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

Three modes, for three different questions:

  content  (default)  Concatenate every message, drop role boundaries.
                      "Did the instruction set change at all?"
  roles               Same, but keep `===== SYSTEM =====` markers.
                      "What moved between the system and user prompts?"
  files               List the file inventory on each side, no diff.
                      "Which files went where?"

Usage:
  scripts/prompt_diff.py --list
  scripts/prompt_diff.py vocabulary-complexity
  scripts/prompt_diff.py vocabulary-complexity --mode roles
  scripts/prompt_diff.py --all
  scripts/prompt_diff.py purpose-clarity --base origin/main --head my-branch
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# Where each evaluator's prompts lived before the migration, and which branch
# carries the migrated version. `old_paths` is ordered -- it defines the
# concatenation order for the base side, mirroring the order the config
# declares on the head side.
#
# Once these branches merge, `head_ref` entries can drop to "origin/main" and
# this manifest becomes a historical record of where things used to live.
EVALUATORS: dict[str, dict] = {
    "grade-level-appropriateness": {
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
        "old_name": "Conventionality",
        "pr": 161,
        "head_ref": "origin/worktree-ga-conventionality-fixes",
        "steps": {
            "evaluate_conventionality": {
                "old": [
                    "evals/prompts/conventionality/system.txt",
                    "evals/prompts/conventionality/user.txt",
                ],
            },
        },
    },
    "vocabulary-complexity": {
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
}

NEW_DIR = "evals/student-facing-text/ela-reading"

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
    base_dir = f"{NEW_DIR}/{slug}"
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


def open_in_difftool(base_file: Path, head_file: Path) -> None:
    """Launch a side-by-side view. Honours $PROMPT_DIFF_TOOL, else VS Code."""
    tool = os.environ.get("PROMPT_DIFF_TOOL", "code --diff")
    subprocess.run([*tool.split(), str(base_file), str(head_file)], capture_output=True)


HTML_CSS = """
body { font: 14px -apple-system, BlinkMacSystemFont, sans-serif; margin: 2rem; color: #1f2328; }
h1 { font-size: 1.4rem; } h2 { font-size: 1rem; margin-top: 2.5rem; }
table.diff { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
             font-size: 12px; border-collapse: collapse; width: 100%;
             table-layout: fixed; border: 1px solid #d0d7de; }
table.diff td { padding: 2px 6px; vertical-align: top;
                white-space: pre-wrap; word-break: break-word; }
table.diff td.diff_header { background: #f6f8fa; color: #656d76;
                            text-align: right; width: 3.5rem; user-select: none; }
.diff_next { display: none; }
.diff_add { background: #d1f8d4; } .diff_sub { background: #ffd7d5; }
.diff_chg { background: #fff3c9; }
.idx a { text-decoration: none; } .idx li { margin: .2rem 0; }
.ok { color: #1a7f37; } .chg { color: #9a6700; }
"""


def html_report(entries: list[tuple[str, str, str, bool]], out_path: Path,
                base_ref: str, changed_only: bool) -> Path:
    """One self-contained side-by-side report for every call.

    Self-contained so it can be handed to someone who doesn't have the repo,
    a checkout, or a difftool -- they just open it in a browser.
    """
    import difflib

    differ = difflib.HtmlDiff(wrapcolumn=80)
    index, bodies = [], []

    for name, base_text, head_text, changed in entries:
        if changed_only and not changed:
            continue
        status = "chg" if changed else "ok"
        label = "CHANGED" if changed else "IDENTICAL"
        index.append(f'<li class="idx"><a href="#{name}">{name}</a> '
                     f'<span class="{status}">[{label}]</span></li>')
        bodies.append(f'<h2 id="{name}">{name} <span class="{status}">[{label}]</span></h2>')
        if changed:
            bodies.append(differ.make_table(
                base_text.splitlines(), head_text.splitlines(),
                fromdesc="BEFORE", todesc="AFTER", context=True, numlines=3,
            ))
        else:
            bodies.append("<p>Byte-identical after restructuring.</p>")

    html = (
        f"<!doctype html><meta charset=utf-8><title>Prompt diff</title>"
        f"<style>{HTML_CSS}</style>"
        f"<h1>Prompt diff &mdash; rendered per LLM call</h1>"
        f"<p>base <code>{base_ref}</code>. Each section is one LLM call's full "
        f"rendered prompt, before and after.</p>"
        f"<ul>{''.join(index)}</ul>{''.join(bodies)}"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    return out_path


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

    if args.emit or args.open:
        out_dir = Path(args.emit) if args.emit else Path(tempfile.gettempdir()) / "prompt-diff"
        base_file, head_file = emit_pair(out_dir, label.split()[0], base_text, head_text)
        if args.emit:
            print(f"  wrote {base_file}")
            print(f"  wrote {head_file}")
        tool = os.environ.get("PROMPT_DIFF_TOOL", "code --diff")
        print(f"  {c('visual:', 'cyan')} {tool} {base_file} {head_file}")
        if args.open and changed:
            open_in_difftool(base_file, head_file)

    if not changed:
        print(f"  {c('IDENTICAL', 'green')} -- restructured only, the model sees the same bytes")
    elif args.emit or args.open:
        print(f"  {c('CHANGED', 'yellow')} -- open the pair above in your diff tool")
    else:
        print()
        print(output)
    return changed


def collect_entries(slugs: list[str], args) -> list[tuple[str, str, str, bool]]:
    """Render every LLM call for the given evaluators, for the HTML report."""
    entries: list[tuple[str, str, str, bool]] = []
    for slug in slugs:
        meta = EVALUATORS[slug]
        try:
            base_ref, head_ref = resolve(slug, args)
        except GitError as e:
            print(f"error ({slug}): {e}", file=sys.stderr)
            continue
        for step_id, step_meta in meta["steps"].items():
            try:
                base_msgs = base_messages(base_ref, step_meta["old"])
                head_msgs = head_step_messages(
                    head_ref, slug, step_id, step_meta.get("head_extra", [])
                )
                base_text, head_text, _ = prepare(base_msgs, head_msgs, args)
                _, changed = word_diff(base_text, head_text, "a", "b", color=False)
                entries.append((f"{slug}.{step_id}", base_text, head_text, changed))
            except GitError as e:
                print(f"error ({slug}.{step_id}): {e}", file=sys.stderr)
    return entries


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


def summary(args) -> int:
    """Verdict table across every evaluator, one row per LLM call."""
    # `files` is an inventory view, not a diff -- there's no verdict to report,
    # so hand each evaluator to diff_one rather than producing bogus rows.
    if args.mode == "files":
        for slug in EVALUATORS:
            try:
                diff_one(slug, args)
            except GitError as e:
                print(f"error ({slug}): {e}", file=sys.stderr)
        return 0

    print(f"\n{'EVALUATOR':<30} {'CALL':<38} {'PR':>4}  VERDICT")
    print("=" * 96)

    changed_any = False
    all_notes: set[str] = set()
    for slug, meta in EVALUATORS.items():
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

            verdict = c("CHANGED", "yellow") if changed else c("IDENTICAL", "green")
            changed_any = changed_any or changed
            print(f"{slug:<30} {step_id:<38} {meta['pr']:>4}  {verdict}")

    print("=" * 96)
    print(f"mode={args.mode}" + (", normalized" if args.normalize else ""))
    if all_notes:
        # Never let normalization hide a substitution without naming it.
        print(f"normalized away: {', '.join(sorted(all_notes))}")
    print("IDENTICAL = this LLM call's prompt is byte-identical after restructuring.")
    print("Drill in:  scripts/prompt_diff.py <evaluator>\n")
    return 1 if changed_any else 0


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
        help="write each rendered BEFORE/AFTER pair to DIR instead of printing the "
             "diff inline, and print a `code --diff` command for each -- use this "
             "to review in VS Code, Meld, Beyond Compare, or any visual difftool",
    )
    parser.add_argument(
        "--no-fetch", dest="fetch", action="store_false",
        help="skip the `git fetch origin` this runs first. Fetching is the "
             "default because both sides are read from remote-tracking refs: "
             "without it, a prompt you just pushed is invisible and the tool "
             "reports a confident verdict on stale content",
    )
    parser.add_argument(
        "--open", action="store_true",
        help="launch a side-by-side view for each CHANGED call. Uses "
             "$PROMPT_DIFF_TOOL, defaulting to `code --diff`",
    )
    parser.add_argument(
        "--html", metavar="FILE",
        help="write one self-contained side-by-side HTML report covering every "
             "call, and open it. Needs no repo, checkout, or difftool to read, "
             "so it's the format to hand to a reviewer",
    )
    parser.add_argument(
        "--changed-only", action="store_true",
        help="skip calls whose prompt is unchanged",
    )
    parser.add_argument("--no-color", dest="color", action="store_false", help="disable color")
    args = parser.parse_args()

    global _USE_COLOR
    _USE_COLOR = args.color and sys.stdout.isatty()

    if args.fetch and not args.list:
        fetch()

    if args.list:
        print(f"\n{'SLUG':<30}  {'PR':>5}  WAS")
        print("-" * 70)
        for slug, meta in EVALUATORS.items():
            print(f"{slug:<30}  {meta['pr']:>5}  {meta['old_name']}")
        print()
        return 0

    # --html covers one evaluator or all of them, so handle it before the split.
    if args.html:
        slugs = list(EVALUATORS) if args.all else [args.evaluator]
        if not slugs or slugs == [None]:
            print("--html needs an evaluator or --all", file=sys.stderr)
            return 2
        entries = collect_entries(slugs, args)
        base_ref = resolve(slugs[0], args)[0]
        out = html_report(entries, Path(args.html), base_ref, args.changed_only)
        n_changed = sum(1 for _, _, _, ch in entries if ch)
        print(f"\nwrote {out}  ({n_changed} of {len(entries)} calls changed)")
        subprocess.run(["open", str(out)], capture_output=True)
        return 1 if n_changed else 0

    if args.all:
        # --emit wants files for every pair, not a verdict table.
        if args.emit or args.open:
            args.combined = False
            changed = False
            for slug in EVALUATORS:
                try:
                    changed |= diff_one(slug, args)
                except GitError as e:
                    print(f"error ({slug}): {e}", file=sys.stderr)
                    changed = True
            print(f"\nAll pairs written to {args.emit}/")
            return 1 if changed else 0
        return summary(args)

    if not args.evaluator:
        parser.print_help()
        return 2

    if args.evaluator not in EVALUATORS:
        print(f"unknown evaluator: {args.evaluator!r}", file=sys.stderr)
        print(f"known: {', '.join(EVALUATORS)}", file=sys.stderr)
        return 2

    try:
        diff_one(args.evaluator, args)
    except GitError as e:
        print(f"error: {e}", file=sys.stderr)
        print("hint: run `git fetch origin` if a PR branch is missing", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
