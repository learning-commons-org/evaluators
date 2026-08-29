#!/usr/bin/env python3
"""Diff an evaluator's prompts between two git refs.

Prompt review is hard with a plain `git diff` for two reasons:

  1. The files moved. `evals/prompts/vocabulary/` became
     `evals/student-facing-text/ela-reading/vocabulary-complexity/`, so a
     path-based diff shows every file as deleted-and-added.

  2. Content moved *between* files. Rubric text that used to sit in a user
     prompt now sits in a system prompt. A per-file diff reports that as a
     large deletion plus a large addition, when nothing the model sees
     actually changed.

This tool answers the question that matters -- "did the bytes we send to the
model change?" -- by rendering each side into one normalized blob, in the
order the config declares, and diffing that. A pure restructure produces an
empty diff. Only real wording changes show up.

Diffs are per LLM call (one `steps[]` entry) by default -- the unit that maps
to an actual API request. `git fetch origin` runs first, so a prompt you just
pushed to a PR is never reviewed from a stale ref.

Three modes, for three different questions:

  content  (default)  Concatenate every message, drop role boundaries.
                      "Did the instruction set change at all?"
  roles               Same, but keep `===== SYSTEM =====` markers.
                      "What moved between the system and user prompts?"
  files               List the file inventory on each side, no diff.
                      "Which files went where?"

Usage:
  scripts/prompt_diff.py --list                      # evaluators + calls, by family
  scripts/prompt_diff.py --all                       # verdict per LLM call
  scripts/prompt_diff.py --all --family feedback     # scope to one family
  scripts/prompt_diff.py --all --changed-only        # only what moved
  scripts/prompt_diff.py vocabulary-complexity       # drill into one evaluator
  scripts/prompt_diff.py sentence-structure --mode roles
  scripts/prompt_diff.py --all --normalize           # hide already-agreed renames

Reviewing visually:
  scripts/prompt_diff.py <evaluator> --difftool      # via your configured diff.tool
  scripts/prompt_diff.py --all --emit /tmp/pd        # write pairs + print commands

Any two refs:
  scripts/prompt_diff.py purpose-clarity --base origin/main --head my-branch
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# Destination root per family. Each evaluator names its family rather than
# repeating the path.
FAMILIES = {
    "student-facing-text": "evals/student-facing-text/ela-reading",
    "feedback": "evals/feedback/ela-writing",
}

# Where each evaluator's prompts lived before the migration, and which branch
# carries the migrated version. Each step's `old` list is ordered -- it defines
# the concatenation order for the base side, mirroring the order the config
# declares on the head side.
#
# Once these branches merge, `head_ref` entries can drop to "origin/main" and
# this manifest becomes a historical record of where things used to live.
EVALUATORS: dict[str, dict] = {
    "grade-level-appropriateness": {
        "family": "student-facing-text",
        "old_name": "Grade Level Appropriateness",
        "pr": 159,
        "head_ref": "origin/worktree-ga-gla-prompt-fixes",
        "steps": {
            "evaluate_grade_level_appropriateness": {
                "old": [
                    "evals/prompts/grade-level-appropriateness/system.txt",
                    "evals/prompts/grade-level-appropriateness/user.txt",
                ],
            },
        },
    },
    "meaning-directness": {
        "family": "student-facing-text",
        "old_name": "Conventionality",
        "pr": 161,
        "head_ref": "origin/worktree-ga-conventionality-fixes",
        "steps": {
            "evaluate_meaning_directness": {
                "old": [
                    "evals/prompts/conventionality/system.txt",
                    "evals/prompts/conventionality/user.txt",
                ],
            },
        },
    },
    "vocabulary-complexity": {
        "family": "student-facing-text",
        "old_name": "Vocabulary",
        "pr": 163,
        "head_ref": "origin/worktree-ga-vocabulary-fixes",
        "steps": {
            "background_knowledge": {
                "old": ["evals/prompts/vocabulary/background-knowledge.txt"],
            },
            "vocab_complexity_grades_3_4": {
                "old": [
                    "evals/prompts/vocabulary/grades-3-4-system.txt",
                    "evals/prompts/vocabulary/grades-3-4-user.txt",
                ],
            },
            "vocab_complexity_other_grades": {
                "old": [
                    "evals/prompts/vocabulary/other-grades-system.txt",
                    "evals/prompts/vocabulary/other-grades-user.txt",
                ],
            },
        },
    },
    "background-knowledge-demands": {
        "family": "student-facing-text",
        "old_name": "Subject Matter Knowledge",
        "pr": 173,
        "head_ref": "origin/worktree-background-knowledge-demands",
        "steps": {
            "evaluate_background_knowledge_demands": {
                "old": [
                    "evals/prompts/subject-matter-knowledge/system.txt",
                    "evals/prompts/subject-matter-knowledge/user.txt",
                ],
            },
        },
    },
    "sentence-structure": {
        "family": "student-facing-text",
        "old_name": "Sentence Structure",
        "pr": 174,
        "head_ref": "origin/worktree-sentence-structure",
        "steps": {
            "sentence_analysis": {
                "old": [
                    "evals/prompts/sentence-structure/analysis-system.txt",
                    "evals/prompts/sentence-structure/analysis-user.txt",
                ],
            },
            "classify_complexity": {
                "old": [
                    "evals/prompts/sentence-structure/complexity-system.txt",
                    "evals/prompts/sentence-structure/complexity-user.txt",
                    "evals/prompts/sentence-structure/rubric-grade-3.txt",
                    "evals/prompts/sentence-structure/rubric-grade-4.txt",
                    "evals/prompts/sentence-structure/rubric-grades-5-12.txt",
                ],
                # Interpolated into this step's {rubric}. They're `preprocessing`
                # entries, and the schema has no source_path for those, so the
                # config can't tell us they belong to this call -- hence listing
                # them here. See the note in head_step_messages().
                "head_extra": [
                    "rubric-grade-3.txt",
                    "rubric-grade-4.txt",
                    "rubric-grades-5-12.txt",
                ],
            },
        },
    },
    "purpose-clarity": {
        "family": "student-facing-text",
        "old_name": "Purpose",
        "pr": 175,
        "head_ref": "origin/worktree-purpose-clarity",
        "steps": {
            "evaluate_purpose_clarity": {
                "old": [
                    "evals/prompts/purpose/system.txt",
                    "evals/prompts/purpose/user.txt",
                ],
            },
        },
    },
    "organizational-structure": {
        "family": "student-facing-text",
        "old_name": "Organizational Structure",
        "pr": 176,
        "head_ref": "origin/worktree-organizational-structure",
        "steps": {
            "evaluate_organizational_structure": {
                "old": [
                    "evals/literacy/qualitative-text-complexity/organizational-structure/system.txt",
                    "evals/literacy/qualitative-text-complexity/organizational-structure/user.txt",
                ],
            },
        },
    },
    "reference-knowledge-demands": {
        "family": "student-facing-text",
        "old_name": "Intertextuality",
        "pr": 177,
        "head_ref": "origin/worktree-reference-knowledge-demands",
        "steps": {
            "evaluate_intertextuality": {
                "old": [
                    "evals/literacy/qualitative-text-complexity/intertextuality/system.txt",
                    "evals/literacy/qualitative-text-complexity/intertextuality/user.txt",
                ],
            },
        },
    },

    # --- feedback family -------------------------------------------------
    # All seven moved from evals/feedback/productive-coaching-writing-feedback/
    # to evals/feedback/ela-writing/. Single LLM step each, system + user.
    "strength-acknowledgment": {
        "family": "feedback",
        "old_name": "Acknowledges Strength",
        "pr": 185,
        "head_ref": "origin/feedback-strength-acknowledgement",
        "steps": {
            "evaluate_strength_acknowledgment": {
                "old": [
                    "evals/feedback/productive-coaching-writing-feedback/acknowledges-strength/system.txt",
                    "evals/feedback/productive-coaching-writing-feedback/acknowledges-strength/user.txt",
                ],
            },
        },
    },
    "revision-actionability": {
        "family": "feedback",
        "old_name": "Actionable Revision",
        "pr": 180,
        "head_ref": "origin/feedback-revision-actionability",
        "steps": {
            "evaluate_revision_actionability": {
                "old": [
                    "evals/feedback/productive-coaching-writing-feedback/actionable-revision/system.txt",
                    "evals/feedback/productive-coaching-writing-feedback/actionable-revision/user.txt",
                ],
            },
        },
    },
    "student-response-specificity": {
        "family": "feedback",
        "old_name": "Anchored In Student Response",
        "pr": 181,
        "head_ref": "origin/feedback-student-response-specificity",
        "steps": {
            "evaluate_student_response_specificity": {
                "old": [
                    "evals/feedback/productive-coaching-writing-feedback/anchored-in-student-response/system.txt",
                    "evals/feedback/productive-coaching-writing-feedback/anchored-in-student-response/user.txt",
                ],
            },
        },
    },
    "revision-accuracy": {
        "family": "feedback",
        "old_name": "Appropriate Feedback",
        "pr": 182,
        "head_ref": "origin/feedback-revision-accuracy",
        "steps": {
            "evaluate_revision_accuracy": {
                "old": [
                    "evals/feedback/productive-coaching-writing-feedback/appropriate-feedback/system.txt",
                    "evals/feedback/productive-coaching-writing-feedback/appropriate-feedback/user.txt",
                ],
            },
        },
    },
    "revision-manageability": {
        "family": "feedback",
        "old_name": "Manageable",
        "pr": 179,
        "head_ref": "origin/feedback-revision-manageability",
        "steps": {
            "evaluate_revision_manageability": {
                "old": [
                    "evals/feedback/productive-coaching-writing-feedback/manageable/system.txt",
                    "evals/feedback/productive-coaching-writing-feedback/manageable/user.txt",
                ],
            },
        },
    },
    "tone-appropriateness": {
        "family": "feedback",
        "old_name": "Tone Appropriateness",
        "pr": 183,
        "head_ref": "origin/feedback-tone-appropriateness",
        "steps": {
            "evaluate_tone_appropriateness": {
                "old": [
                    "evals/feedback/productive-coaching-writing-feedback/tone-appropriateness/system.txt",
                    "evals/feedback/productive-coaching-writing-feedback/tone-appropriateness/user.txt",
                ],
            },
        },
    },
    "withholding-answers": {
        "family": "feedback",
        "old_name": "Withholding Answers",
        "pr": 184,
        "head_ref": "origin/feedback-withholding-answers",
        "steps": {
            "evaluate_withholding_answers": {
                "old": [
                    "evals/feedback/productive-coaching-writing-feedback/withholding-answers/system.txt",
                    "evals/feedback/productive-coaching-writing-feedback/withholding-answers/user.txt",
                ],
            },
        },
    },
}

def new_dir(slug: str) -> str:
    """Destination directory for an evaluator, from its family."""
    return f"{FAMILIES[EVALUATORS[slug]['family']]}/{slug}"

# Substitutions applied under --normalize, to answer "ignoring the renames we
# already know about, is anything else different?" Reported when applied, so a
# clean diff never silently hides one of these.
KNOWN_RENAMES = [("{grade}", "{grade_level}")]

# Dropped under --normalize: structured output made these obsolete, and their
# removal is a decision already made, not something to re-review per evaluator.
KNOWN_DROPS = ["{format_instructions}"]


class GitError(RuntimeError):
    pass


# Set once from --no-color, so every styled string honours it -- not just the
# diff body.
_USE_COLOR = True

_STYLES = {"bold": "1", "red": "31", "green": "32", "yellow": "33", "cyan": "36"}


def c(text: str, style: str) -> str:
    """Style text, or return it untouched when colour is off."""
    if not _USE_COLOR:
        return text
    return f"\033[{_STYLES[style]}m{text}\033[0m"


def git_show(ref: str, path: str) -> str:
    """Read one file at one ref. Raises GitError if it isn't there."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GitError(f"{ref}:{path} -- {result.stderr.strip()}")
    return result.stdout


def path_exists(ref: str, path: str) -> bool:
    return subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{path}"], capture_output=True
    ).returncode == 0


def ref_with_path(ref: str, path: str) -> str:
    """Return a ref where `path` exists, starting from `ref`.

    Once a migration PR merges, the base-side files are gone from the default
    branch -- they were `git mv`d away. Reading them at `origin/main` then
    fails, which would make the whole post-merge fallback useless. So when the
    path is missing we walk back to the commit that removed it and read from
    its first parent, i.e. the last state where the file still existed.
    """
    if path_exists(ref, path):
        return ref

    result = subprocess.run(
        ["git", "rev-list", "-1", ref, "--", path], capture_output=True, text=True
    )
    sha = result.stdout.strip()
    if not sha:
        raise GitError(f"{path} never existed in the history of {ref}")
    return f"{sha}^"


# Where PR refs get cached locally. GitHub publishes every PR head at
# refs/pull/<N>/head, which beats a branch name on all three counts that
# matter here: it exists on any clone without the contributor having set up
# branches, it survives the branch being deleted after merge, and it can't be
# invalidated by a rename.
PR_REF_NS = "refs/prompt-diff"


def pr_ref(pr: int) -> str:
    return f"{PR_REF_NS}/pr-{pr}"


def fetch(remote: str = "origin") -> None:
    """Refresh remote-tracking refs and cache every PR head locally.

    Both sides are read from refs, not the working tree, so a stale ref means
    a confident verdict on old content -- worse than an error, because it
    looks like a real answer. Fetching the PR heads in the same round trip is
    what lets this work on a clone that has never seen the PR branches.
    """
    subprocess.run(["git", "fetch", remote, "--quiet"], capture_output=True)

    refspecs = [
        f"+refs/pull/{meta['pr']}/head:{pr_ref(meta['pr'])}"
        for meta in EVALUATORS.values()
    ]
    subprocess.run(
        ["git", "fetch", remote, "--quiet", *refspecs], capture_output=True
    )


def role_from_filename(path: str) -> str:
    """Infer a message's role from its filename.

    Only used for the base side, which predates config.json declaring roles
    explicitly. The naming convention was consistent enough to rely on:
    *-system.txt / system.txt are system prompts, everything else is a user
    prompt (rubric-*.txt are fragments interpolated into a user prompt).
    """
    stem = Path(path).stem
    return "system" if stem == "system" or stem.endswith("-system") else "user"


def ls_tree(ref: str, directory: str) -> list[str]:
    """List filenames directly under a directory at a ref."""
    result = subprocess.run(
        ["git", "ls-tree", "--name-only", ref, f"{directory}/"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return []
    return [Path(line).name for line in result.stdout.splitlines() if line.strip()]


def head_step_messages(ref: str, slug: str, step_id: str,
                       extra: list[str]) -> list[tuple[str, str, str]]:
    """Read one LLM call's prompt files from the head side.

    The declared messages come from config.json, so the tool stays correct as
    steps are reordered. `extra` covers files the config depends on but cannot
    name: Sentence Structure's grade-band rubrics are `preprocessing` entries
    interpolated into `{rubric}`, and config.schema.json has no `source_path`
    field for preprocessing. Without them the rubrics would read as deletions
    -- exactly the false alarm this tool exists to prevent.
    """
    base_dir = new_dir(slug)
    config = json.loads(git_show(ref, f"{base_dir}/config.json"))

    step = next((s for s in config.get("steps", []) if s.get("id") == step_id), None)
    if step is None:
        known = ", ".join(s.get("id", "?") for s in config.get("steps", []))
        raise GitError(f"step {step_id!r} not in {ref}:{base_dir}/config.json (has: {known})")

    messages = [
        (msg.get("role", "user"), msg["source_path"],
         git_show(ref, f"{base_dir}/{msg['source_path']}"))
        for msg in step.get("prompt", {}).get("messages", [])
    ]
    messages += [
        ("interpolated", name, git_show(ref, f"{base_dir}/{name}")) for name in extra
    ]
    return messages


def head_messages(ref: str, slug: str) -> list[tuple[str, str, str]]:
    """Every prompt file on the head side, all steps concatenated in order."""
    out: list[tuple[str, str, str]] = []
    for step_id, step_meta in EVALUATORS[slug]["steps"].items():
        out += head_step_messages(ref, slug, step_id, step_meta.get("head_extra", []))
    return out


def old_paths_for(slug: str) -> list[str]:
    """Every base-side path for an evaluator, all steps in order."""
    return [p for s in EVALUATORS[slug]["steps"].values() for p in s["old"]]


def base_messages(ref: str, old_paths: list[str]) -> list[tuple[str, str, str]]:
    """Read the base side's messages from the manifest's ordered path list.

    Each path is resolved independently via ref_with_path, so this keeps
    working after the migration PRs merge and delete the originals.
    """
    return [
        (role_from_filename(path), Path(path).name,
         git_show(ref_with_path(ref, path), path))
        for path in old_paths
    ]


def normalize(text: str) -> str:
    """Strip differences that are formatting, not meaning.

    Trailing whitespace and blank-line runs vary between hand-edited files and
    tell you nothing about what the model receives.
    """
    lines = [line.rstrip() for line in text.split("\n")]
    out: list[str] = []
    for line in lines:
        if not line and out and not out[-1]:
            continue
        out.append(line)
    return "\n".join(out).strip() + "\n"


def apply_known_renames(text: str) -> tuple[str, list[str]]:
    """Canonicalize the placeholder renames, reporting which ones fired."""
    applied = []
    for old, new in KNOWN_RENAMES:
        if old in text:
            text = text.replace(old, new)
            applied.append(f"{old} -> {new}")
    for token in KNOWN_DROPS:
        if token in text:
            text = text.replace(token, "")
            applied.append(f"dropped {token}")
    return text, applied


def render(messages: list[tuple[str, str, str]], mode: str) -> str:
    """Flatten messages into the blob that gets diffed."""
    if mode == "roles":
        parts = [
            f"===== {role.upper()} ({source}) =====\n{text}"
            for role, source, text in messages
        ]
    else:  # content -- role and file boundaries deliberately erased
        parts = [text for _, _, text in messages]
    return normalize("\n".join(parts))


def strip_file_header(diff: str) -> str:
    """Drop git's file-header lines -- they'd show temp paths, not real ones.

    The `@@` hunk headers are kept: they carry the surrounding prose, which is
    the useful part for locating a change in a long prompt.
    """
    skip = ("diff --git ", "index ", "--- ", "+++ ")
    lines = [ln for ln in diff.split("\n") if not _ANSI.sub("", ln).startswith(skip)]
    return "\n".join(lines).strip("\n")


def word_diff(base_text: str, head_text: str, base_label: str, head_label: str,
              color: bool) -> tuple[str, bool]:
    """Word-level diff via git. Returns (output, changed).

    Word granularity matters for prose: a reflowed paragraph is a whole-line
    change to a line differ, but a no-op to a word differ.
    """
    with tempfile.TemporaryDirectory() as tmp:
        base_file = Path(tmp) / "base"
        head_file = Path(tmp) / "head"
        base_file.write_text(base_text)
        head_file.write_text(head_text)

        cmd = [
            "git", "diff", "--no-index", "--patience",
            f"--word-diff={'color' if color else 'plain'}",
            f"--color={'always' if color else 'never'}",
            str(base_file), str(head_file),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        # git diff exits 1 when files differ -- that's data, not failure.
        return strip_file_header(result.stdout), result.returncode != 0


def ref_exists(ref: str) -> bool:
    return subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        capture_output=True,
    ).returncode == 0


def resolve(slug: str, args) -> tuple[str, str]:
    """Resolve the base and head refs for one evaluator.

    Head is tried in descending order of robustness: the cached PR ref (works
    on any clone, outlives the branch), then the branch itself (covers a
    local-only branch that was never pushed, and the offline case), then the
    default branch once the work has merged.
    """
    if args.head:
        return args.base, args.head

    meta = EVALUATORS[slug]
    for candidate in (pr_ref(meta["pr"]), meta["head_ref"], args.fallback_head):
        if ref_exists(candidate):
            return args.base, candidate

    raise GitError(
        f"no usable head ref for {slug}: tried {pr_ref(meta['pr'])}, "
        f"{meta['head_ref']}, {args.fallback_head}. "
        f"Run with network access so PR #{meta['pr']} can be fetched."
    )


def prepare(base_msgs, head_msgs, args) -> tuple[str, str, list[str]]:
    """Render both sides and apply optional normalization.

    Substitutions from *both* sides are reported. Collecting only the base
    side's would silently hide a head-only substitution, breaking the
    guarantee that normalization never conceals a change without saying so.
    """
    base_text = render(base_msgs, args.mode)
    head_text = render(head_msgs, args.mode)
    notes: list[str] = []
    if args.normalize:
        base_text, base_applied = apply_known_renames(base_text)
        head_text, head_applied = apply_known_renames(head_text)
        seen: set[str] = set()
        for note in base_applied + head_applied:
            if note not in seen:
                seen.add(note)
                notes.append(note)
        base_text, head_text = normalize(base_text), normalize(head_text)
    return base_text, head_text, notes


def emit_pair(out_dir: Path, name: str, base_text: str, head_text: str) -> tuple[Path, Path]:
    """Write a rendered pair to disk for use with any external diff tool."""
    out_dir.mkdir(parents=True, exist_ok=True)
    base_file = out_dir / f"{name}.BEFORE.txt"
    head_file = out_dir / f"{name}.AFTER.txt"
    base_file.write_text(base_text)
    head_file.write_text(head_text)
    return base_file, head_file


def print_review_commands(out_dir: Path) -> None:
    """Print ready-to-run commands for the pairs just written.

    The per-call `visual:` lines are already above, but they're scattered
    through the output. One loop over the directory beats hunting for them or
    retyping paths, and the naming convention makes it a one-liner.
    """
    pairs = sorted(out_dir.glob("*.BEFORE.txt"))
    if not pairs:
        return

    print(f"\n{c('Review all ' + str(len(pairs)) + ' in one go:', 'bold')}")
    print(f'  for f in {out_dir}/*.BEFORE.txt; do '
          f'git diff --no-index "$f" "${{f%.BEFORE.txt}}.AFTER.txt"; done')
    print(f"\n{c('Or one at a time:', 'bold')}")
    for base_file in pairs:
        head_file = base_file.with_name(base_file.name.replace(".BEFORE.", ".AFTER."))
        print(f"  git diff --no-index {base_file} {head_file}")


def open_in_difftool(base_file: Path, head_file: Path, tool: str | None) -> None:
    """Hand the pair to `git difftool`.

    Deliberately not a bespoke launcher: git already knows how to drive 25+
    diff tools and honours whatever the user configured in `diff.tool`, so
    reinventing that would just be a worse version with its own config.
    """
    cmd = ["git", "difftool", "--no-index", "--no-prompt"]
    if tool:
        cmd.append(f"--tool={tool}")
    subprocess.run([*cmd, str(base_file), str(head_file)])


def report(label: str, subtitle: str, base_text: str, head_text: str,
           notes: list[str], args) -> bool:
    """Diff one rendered pair and print the result. Returns True if changed."""
    output, changed = word_diff(base_text, head_text, "before", "after", color=args.color)

    # "Show me what changed" usually means only what changed.
    if args.changed_only and not changed:
        return False

    print(f"\n{c(label, 'bold')}")
    print(f"  {subtitle}")
    if notes:
        print(f"  normalized: {', '.join(notes)}")

    if args.emit or args.difftool:
        out_dir = Path(args.emit) if args.emit else Path(tempfile.gettempdir()) / "prompt-diff"
        base_file, head_file = emit_pair(out_dir, label.split()[0], base_text, head_text)
        if args.emit:
            print(f"  wrote {base_file}")
            print(f"  wrote {head_file}")
        # `git diff` rather than `git difftool`: it works everywhere, and picks
        # up delta (or any configured pager) automatically. --difftool covers
        # the GUI case.
        print(f"  {c('visual:', 'cyan')} git diff --no-index {base_file} {head_file}")
        if args.difftool and changed:
            tool = None if args.difftool == "auto" else args.difftool
            open_in_difftool(base_file, head_file, tool)

    if not changed:
        print(f"  {c('IDENTICAL', 'green')} -- restructured only, the model sees the same bytes")
    elif args.emit or args.difftool:
        print(f"  {c('CHANGED', 'yellow')} -- open the pair above in your diff tool")
    else:
        print()
        print(output)
    return changed


def diff_one(slug: str, args) -> bool:
    """Diff one evaluator. Returns True if anything changed."""
    meta = EVALUATORS[slug]
    base_ref, head_ref = resolve(slug, args)
    refs = f"{base_ref}  ->  {head_ref}"

    if args.mode == "files":
        title = f"{meta['old_name']} -> {slug}"
        print(f"\n{c(title, 'bold')}  (PR #{meta['pr']})")
        for step_id, step_meta in meta["steps"].items():
            print(f"\n  {c(f'call: {step_id}', 'bold')}")
            print(f"    base  {base_ref}")
            for role, source, text in base_messages(base_ref, step_meta["old"]):
                print(f"      {role:>13}  {source:<28} {len(text):>6} chars")
            print(f"    head  {head_ref}")
            for role, source, text in head_step_messages(
                head_ref, slug, step_id, step_meta.get("head_extra", [])
            ):
                print(f"      {role:>13}  {source:<28} {len(text):>6} chars")
        return False

    # Per-LLM-call: one diff per step, the unit that maps to an actual API call.
    if not args.combined:
        changed_any = False
        for step_id, step_meta in meta["steps"].items():
            base_msgs = base_messages(base_ref, step_meta["old"])
            head_msgs = head_step_messages(
                head_ref, slug, step_id, step_meta.get("head_extra", [])
            )
            base_text, head_text, notes = prepare(base_msgs, head_msgs, args)
            changed_any |= report(
                f"{slug}.{step_id}",
                f"{meta['old_name']} -> {slug}  (PR #{meta['pr']}, call {step_id}, mode={args.mode})\n  {refs}",
                base_text, head_text, notes, args,
            )
        return changed_any

    base_text, head_text, notes = prepare(
        base_messages(base_ref, old_paths_for(slug)), head_messages(head_ref, slug), args
    )
    return report(
        slug,
        f"{meta['old_name']} -> {slug}  (PR #{meta['pr']}, all calls, mode={args.mode})\n  {refs}",
        base_text, head_text, notes, args,
    )


def selected(args) -> list[str]:
    """Evaluator slugs in scope, honouring --family."""
    return [s for s, m in EVALUATORS.items()
            if not args.family or m["family"] == args.family]


def exit_code(changed: bool, args) -> int:
    """Finding changes is the expected outcome here, not a failure.

    Exiting non-zero for it would make every normal run look like an error --
    shells paint it red, `&&` chains break. Follows `git diff`, which is 0 by
    default and only reports differences through the exit status when you ask
    with --exit-code.
    """
    return 1 if (changed and args.exit_code) else 0


def summary(args) -> int:
    """Verdict table across every evaluator, one row per LLM call."""
    # `files` is an inventory view, not a diff -- there's no verdict to report,
    # so hand each evaluator to diff_one rather than producing bogus rows.
    if args.mode == "files":
        for slug in selected(args):
            try:
                diff_one(slug, args)
            except GitError as e:
                print(f"error ({slug}): {e}", file=sys.stderr)
        return 0

    print(f"\n{'EVALUATOR':<30} {'CALL':<38} {'PR':>4}  VERDICT")
    print("=" * 96)

    changed_any = False
    all_notes: set[str] = set()
    for slug in selected(args):
        meta = EVALUATORS[slug]
        try:
            base_ref, head_ref = resolve(slug, args)
        except GitError as e:
            print(f"{slug:<30} {'-':<38} {meta['pr']:>4}  {c('ERROR', 'red')}  {e}")
            changed_any = True
            continue
        for step_id, step_meta in meta["steps"].items():
            try:
                base_msgs = base_messages(base_ref, step_meta["old"])
                head_msgs = head_step_messages(
                    head_ref, slug, step_id, step_meta.get("head_extra", [])
                )
                base_text, head_text, notes = prepare(base_msgs, head_msgs, args)
                all_notes.update(notes)
                _, changed = word_diff(base_text, head_text, "a", "b", color=False)
            except GitError as e:
                print(f"{slug:<30} {step_id:<38} {meta['pr']:>4}  {c('ERROR', 'red')}  {e}")
                changed_any = True
                continue

            changed_any = changed_any or changed
            if args.changed_only and not changed:
                continue
            verdict = c("CHANGED", "yellow") if changed else c("IDENTICAL", "green")
            print(f"{slug:<30} {step_id:<38} {meta['pr']:>4}  {verdict}")

    print("=" * 96)
    print(f"mode={args.mode}" + (", normalized" if args.normalize else ""))
    if all_notes:
        # Never let normalization hide a substitution without naming it.
        print(f"normalized away: {', '.join(sorted(all_notes))}")
    print("IDENTICAL = this LLM call's prompt is byte-identical after restructuring.")
    print("Drill in:  scripts/prompt_diff.py <evaluator>\n")
    return exit_code(changed_any, args)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Diff an evaluator's prompts between two git refs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage:")[1] if "Usage:" in __doc__ else None,
    )
    parser.add_argument("evaluator", nargs="?", help="evaluator slug (see --list)")
    parser.add_argument("--list", action="store_true", help="list known evaluators")
    parser.add_argument("--all", action="store_true", help="verdict table for every evaluator")
    parser.add_argument(
        "--family", choices=sorted(FAMILIES), metavar="NAME",
        help=f"restrict --all to one family ({', '.join(sorted(FAMILIES))})",
    )
    parser.add_argument(
        "--mode", choices=["content", "roles", "files"], default="content",
        help="content: ignore role/file boundaries (default). "
             "roles: keep role markers. files: inventory only, no diff",
    )
    parser.add_argument("--base", default="origin/main", help="base ref (default: origin/main)")
    parser.add_argument("--head", help="head ref (default: the evaluator's PR branch)")
    parser.add_argument(
        "--fallback-head", default="origin/main",
        help="ref to use when an evaluator's PR branch no longer exists, e.g. "
             "after it merges (default: origin/main)",
    )
    parser.add_argument(
        "--normalize", action="store_true",
        help="canonicalize known placeholder renames ({grade}->{grade_level}, "
             "drop {format_instructions}) so only unexpected changes surface",
    )
    parser.add_argument(
        "--combined", action="store_true",
        help="concatenate all of an evaluator's LLM calls into one diff. Off by "
             "default: condition-gated branches (Vocabulary Complexity's grade "
             "bands, for instance) can cancel out when flattened, so a real "
             "change to one branch could read as IDENTICAL",
    )
    parser.add_argument(
        "--emit", metavar="DIR",
        help="write each rendered BEFORE/AFTER pair to DIR instead of printing "
             "the diff inline, then print ready-to-run `git diff --no-index` "
             "commands for them -- one loop covering every pair, and one per "
             "call. Use with --difftool, or drive the comparison yourself",
    )
    parser.add_argument(
        "--no-fetch", dest="fetch", action="store_false",
        help="skip the `git fetch origin` this runs first. Fetching is the "
             "default because both sides are read from remote-tracking refs: "
             "without it, a prompt you just pushed is invisible and the tool "
             "reports a confident verdict on stale content",
    )
    parser.add_argument(
        "--difftool", nargs="?", const="auto", metavar="TOOL",
        help="open each CHANGED call in `git difftool --no-index`. Uses your "
             "configured diff.tool by default; pass a name (opendiff, vimdiff, "
             "meld, bc, kdiff3, ...) to override. `git difftool --tool-help` "
             "lists what's available",
    )
    parser.add_argument(
        "--changed-only", action="store_true",
        help="skip calls whose prompt is unchanged",
    )
    parser.add_argument(
        "--exit-code", action="store_true",
        help="exit 1 when any prompt changed, like `git diff --exit-code`. Off "
             "by default: finding changes is the point, not a failure, and a "
             "non-zero exit makes every normal run look like an error",
    )
    parser.add_argument("--no-color", dest="color", action="store_false", help="disable color")
    args = parser.parse_args()

    global _USE_COLOR
    _USE_COLOR = args.color and sys.stdout.isatty()

    if args.fetch and not args.list:
        fetch()

    if args.list:
        for family, root in FAMILIES.items():
            print(f"\n{c(family, 'bold')}  ({root}/)")
            print(f"  {'SLUG':<30}  {'PR':>5}  {'CALLS':>5}  WAS")
            print("  " + "-" * 74)
            for slug, meta in EVALUATORS.items():
                if meta["family"] != family:
                    continue
                print(f"  {slug:<30}  {meta['pr']:>5}  {len(meta['steps']):>5}  {meta['old_name']}")
        print()
        return 0

    if args.all:
        # --emit / --difftool want a pair per call, not a verdict table.
        if args.emit or args.difftool:
            args.combined = False
            changed = failed = False
            for slug in selected(args):
                try:
                    changed |= diff_one(slug, args)
                except GitError as e:
                    print(f"error ({slug}): {e}", file=sys.stderr)
                    failed = True
            if args.emit:
                print(f"\nAll pairs written to {args.emit}/")
                print_review_commands(Path(args.emit))
            # A failure is a real error; a change is just the answer.
            return 1 if failed else exit_code(changed, args)
        return summary(args)

    if not args.evaluator:
        parser.print_help()
        return 2

    if args.evaluator not in EVALUATORS:
        print(f"unknown evaluator: {args.evaluator!r}", file=sys.stderr)
        print(f"known: {', '.join(EVALUATORS)}", file=sys.stderr)
        return 2

    try:
        changed = diff_one(args.evaluator, args)
    except GitError as e:
        print(f"error: {e}", file=sys.stderr)
        print("hint: run `git fetch origin` if a PR branch is missing", file=sys.stderr)
        return 1
    return exit_code(changed, args)


if __name__ == "__main__":
    sys.exit(main())
