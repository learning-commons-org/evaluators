#!/usr/bin/env python3
"""Repo check harness — the single entrypoint run locally and in CI.

  python scripts/check.py            # check everything (CI mode)
  python scripts/check.py --fix      # auto-fix what's safe, report the rest
  python scripts/check.py --list     # list available checks
  python scripts/check.py NAME ...   # run only the named check(s)

Runs every selected check, never stopping at the first failure, and prints one
consolidated report so you see all issues at once. Exit code is non-zero if any
violation remains. See scripts/README.md.
"""

from __future__ import annotations

import argparse
import sys

from checks import ALL_CHECKS
from checks.base import Result, Violation


def main() -> int:
    by_name = {c.name: c for c in ALL_CHECKS}
    parser = argparse.ArgumentParser(description="Repo check harness")
    parser.add_argument("checks", nargs="*", help="checks to run (default: all)")
    parser.add_argument("--fix", action="store_true", help="auto-fix where possible")
    parser.add_argument("--list", action="store_true", help="list checks and exit")
    args = parser.parse_args()

    if args.list:
        for c in ALL_CHECKS:
            print(f"  {c.name:20} {c.description}")
        return 0

    unknown = [n for n in args.checks if n not in by_name]
    if unknown:
        print(f"unknown check(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"available: {', '.join(by_name)}", file=sys.stderr)
        return 2

    selected = [by_name[n] for n in args.checks] if args.checks else ALL_CHECKS

    results = []
    for c in selected:
        try:
            results.append(c.run(fix=args.fix))
        except Exception as e:  # one check crashing must not abort the rest
            crashed = Result(c.name)
            crashed.violations.append(Violation(c.name, f"check crashed: {e}"))
            results.append(crashed)

    failures = 0
    for r in results:
        for path in r.fixed:
            print(f"[fixed] {r.check}: {path}")
        if r.ok:
            print(f"[pass]  {r.check}")
        else:
            failures += 1
            print(f"[fail]  {r.check} ({len(r.violations)})")
            for v in r.violations:
                print(f"          {v.render()}")

    print()
    if failures:
        print(f"{failures} of {len(results)} checks failed.")
        if not args.fix:
            print("Run `python scripts/check.py --fix` to auto-fix what's possible.")
        return 1
    print(f"All {len(results)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
