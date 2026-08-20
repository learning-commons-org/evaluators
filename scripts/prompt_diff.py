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
        "old_paths": [
            "evals/prompts/grade-level-appropriateness/system.txt",
            "evals/prompts/grade-level-appropriateness/user.txt",
        ],
    },
    "meaning-directness": {
        "old_name": "Conventionality",
        "pr": 161,
        "head_ref": "origin/worktree-ga-conventionality-fixes",
        "old_paths": [
            "evals/prompts/conventionality/system.txt",
            "evals/prompts/conventionality/user.txt",
        ],
    },
    "vocabulary-complexity": {
        "old_name": "Vocabulary",
        "pr": 163,
        "head_ref": "origin/worktree-ga-vocabulary-fixes",
        "old_paths": [
            "evals/prompts/vocabulary/background-knowledge.txt",
            "evals/prompts/vocabulary/grades-3-4-system.txt",
            "evals/prompts/vocabulary/grades-3-4-user.txt",
            "evals/prompts/vocabulary/other-grades-system.txt",
            "evals/prompts/vocabulary/other-grades-user.txt",
        ],
    },
    "background-knowledge-demands": {
        "old_name": "Subject Matter Knowledge",
        "pr": 173,
        "head_ref": "origin/worktree-background-knowledge-demands",
        "old_paths": [
            "evals/prompts/subject-matter-knowledge/system.txt",
            "evals/prompts/subject-matter-knowledge/user.txt",
        ],
    },
    "sentence-structure": {
        "old_name": "Sentence Structure",
        "pr": 174,
        "head_ref": "origin/worktree-sentence-structure",
        "old_paths": [
            "evals/prompts/sentence-structure/analysis-system.txt",
            "evals/prompts/sentence-structure/analysis-user.txt",
            "evals/prompts/sentence-structure/complexity-system.txt",
            "evals/prompts/sentence-structure/complexity-user.txt",
            "evals/prompts/sentence-structure/rubric-grade-3.txt",
            "evals/prompts/sentence-structure/rubric-grade-4.txt",
            "evals/prompts/sentence-structure/rubric-grades-5-12.txt",
        ],
    },
    "purpose-clarity": {
        "old_name": "Purpose",
        "pr": 175,
        "head_ref": "origin/worktree-purpose-clarity",
        "old_paths": [
            "evals/prompts/purpose/system.txt",
            "evals/prompts/purpose/user.txt",
        ],
    },
    "organizational-structure": {
        "old_name": "Organizational Structure",
        "pr": 176,
        "head_ref": "origin/worktree-organizational-structure",
        "old_paths": [
            "evals/literacy/qualitative-text-complexity/organizational-structure/system.txt",
            "evals/literacy/qualitative-text-complexity/organizational-structure/user.txt",
        ],
    },
    "reference-knowledge-demands": {
        "old_name": "Intertextuality",
        "pr": 177,
        "head_ref": "origin/worktree-reference-knowledge-demands",
        "old_paths": [
            "evals/literacy/qualitative-text-complexity/intertextuality/system.txt",
            "evals/literacy/qualitative-text-complexity/intertextuality/user.txt",
        ],
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


def head_messages(ref: str, slug: str) -> list[tuple[str, str, str]]:
    """Read the head side's prompt files: config-declared messages first, then
    any remaining .txt files in the directory.

    Driving the ordered part off config.json keeps the tool correct as steps
    are added or reordered. The trailing sweep exists because not every prompt
    file is declared as a `messages` entry -- Sentence Structure's grade-band
    rubrics are `preprocessing` entries interpolated into `{rubric}`, and the
    schema has no `source_path` for those. Without the sweep they'd read as
    deletions, which is exactly the false alarm this tool exists to prevent.
    """
    base_dir = f"{NEW_DIR}/{slug}"
    config = json.loads(git_show(ref, f"{base_dir}/config.json"))

    messages: list[tuple[str, str, str]] = []
    declared: set[str] = set()
    for step in config.get("steps", []):
        for msg in step.get("prompt", {}).get("messages", []):
            source = msg["source_path"]
            declared.add(source)
            messages.append(
                (msg.get("role", "user"), source, git_show(ref, f"{base_dir}/{source}"))
            )

    for name in sorted(ls_tree(ref, base_dir)):
        if name.endswith(".txt") and name not in declared:
            messages.append(("undeclared", name, git_show(ref, f"{base_dir}/{name}")))

    return messages


def base_messages(ref: str, old_paths: list[str]) -> list[tuple[str, str, str]]:
    """Read the base side's messages from the manifest's ordered path list."""
    return [
        (role_from_filename(path), Path(path).name, git_show(ref, path))
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

    Falls back to the default branch once a PR branch is gone, so this keeps
    working unchanged after the migration PRs merge and their branches are
    deleted.
    """
    if args.head:
        return args.base, args.head

    head = EVALUATORS[slug]["head_ref"]
    if not ref_exists(head):
        head = args.fallback_head
    return args.base, head


def diff_one(slug: str, args) -> bool:
    """Diff one evaluator. Returns True if the rendered prompt changed."""
    meta = EVALUATORS[slug]
    base_ref, head_ref = resolve(slug, args)

    base_msgs = base_messages(base_ref, meta["old_paths"])
    head_msgs = head_messages(head_ref, slug)

    if args.mode == "files":
        print(f"\n\033[1m{meta['old_name']} -> {slug}\033[0m  (PR #{meta['pr']})")
        print(f"  base  {base_ref}")
        for role, source, text in base_msgs:
            print(f"    {role:>6}  {source:<28} {len(text):>6} chars")
        print(f"  head  {head_ref}")
        for role, source, text in head_msgs:
            print(f"    {role:>6}  {source:<28} {len(text):>6} chars")
        return False

    base_text = render(base_msgs, args.mode)
    head_text = render(head_msgs, args.mode)

    notes: list[str] = []
    if args.normalize:
        base_text, applied = apply_known_renames(base_text)
        notes = applied
        head_text, _ = apply_known_renames(head_text)
        base_text, head_text = normalize(base_text), normalize(head_text)

    output, changed = word_diff(
        base_text, head_text, meta["old_name"].replace(" ", "-"), slug,
        color=args.color,
    )

    header = f"\n\033[1m{meta['old_name']} -> {slug}\033[0m  (PR #{meta['pr']}, mode={args.mode})"
    print(header)
    print(f"  {base_ref}  ->  {head_ref}")
    if notes:
        print(f"  normalized: {', '.join(notes)}")

    if not changed:
        print("  \033[32mIDENTICAL\033[0m -- restructured only, the model sees the same bytes")
    else:
        print()
        print(output)
    return changed


def summary(args) -> int:
    """Verdict table across every evaluator."""
    print(f"\n{'EVALUATOR':<30}  {'PR':>5}  {'VERDICT':<12}  BASE -> HEAD")
    print("=" * 100)

    changed_any = False
    for slug, meta in EVALUATORS.items():
        base_ref, head_ref = resolve(slug, args)
        try:
            base_text = render(base_messages(base_ref, meta["old_paths"]), args.mode)
            head_text = render(head_messages(head_ref, slug), args.mode)
            if args.normalize:
                base_text, _ = apply_known_renames(base_text)
                head_text, _ = apply_known_renames(head_text)
                base_text, head_text = normalize(base_text), normalize(head_text)
            _, changed = word_diff(base_text, head_text, "a", "b", color=False)
        except GitError as e:
            print(f"{slug:<30}  {meta['pr']:>5}  \033[31mERROR\033[0m         {e}")
            changed_any = True
            continue

        verdict = "\033[33mCHANGED\033[0m     " if changed else "\033[32mIDENTICAL\033[0m   "
        changed_any = changed_any or changed
        print(f"{slug:<30}  {meta['pr']:>5}  {verdict}  {base_ref} -> {head_ref.replace('origin/', '')}")

    print("=" * 100)
    print(f"mode={args.mode}" + (", normalized" if args.normalize else ""))
    print("IDENTICAL = prompt text is byte-identical after restructuring; only file layout changed.")
    print("Run without --all on a CHANGED evaluator to see the word-level diff.\n")
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
    parser.add_argument("--no-color", dest="color", action="store_false", help="disable color")
    args = parser.parse_args()

    if args.list:
        print(f"\n{'SLUG':<30}  {'PR':>5}  WAS")
        print("-" * 70)
        for slug, meta in EVALUATORS.items():
            print(f"{slug:<30}  {meta['pr']:>5}  {meta['old_name']}")
        print()
        return 0

    if args.all:
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
