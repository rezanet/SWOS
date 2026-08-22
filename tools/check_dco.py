#!/usr/bin/env python3
"""Verify every selected commit carries a real DCO Signed-off-by trailer."""

import re
import subprocess
import sys

ZERO_SHA = "0" * 40
SIGNOFF_VALUE = re.compile(r"^.+\s<[^<>\s]+@[^<>\s]+>$")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def selected_range(base, head):
    """Return a git revision range and a human-readable label.

    A zero base SHA is GitHub's marker for an initial push. In that case the
    complete reachable history at ``head`` is checked, including the root
    commit. If no base is supplied (for local/manual use), only ``head`` is
    checked by using its first parent as the base when one exists.
    """
    head = head or "HEAD"

    if not base:
        try:
            base = git("rev-parse", f"{head}^")
        except subprocess.CalledProcessError:
            base = ZERO_SHA

    if base == ZERO_SHA or (base and set(base) == {"0"}):
        return head, f"initial history through {head}"

    return f"{base}..{head}", f"{base}..{head}"


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else None
    head = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
    revision, label = selected_range(base, head)

    try:
        out = git(
            "log",
            "--format=%H%x1f%s%x1f%(trailers:key=Signed-off-by,valueonly)%x1e",
            revision,
        )
    except subprocess.CalledProcessError as exc:
        print(f"error: could not read git log for {label}: {exc}")
        return 2

    records = [r.strip() for r in out.split("\x1e") if r.strip()]
    if not records:
        print(f"FAIL  DCO range selected no commits: {label}")
        print("Refusing to pass an empty DCO check.")
        return 2

    missing = []
    malformed = []

    for record in records:
        parts = (record.split("\x1f") + ["", ""])[:3]
        sha, subject, trailer_values = parts
        signoffs = [line.strip() for line in trailer_values.splitlines() if line.strip()]

        if not signoffs:
            missing.append(f"{sha[:8]} {subject}")
        elif not any(SIGNOFF_VALUE.fullmatch(value) for value in signoffs):
            malformed.append(f"{sha[:8]} {subject}")

    print(f"DCO range: {label} ({len(records)} commit(s))")

    if missing or malformed:
        if missing:
            print("FAIL  commits without a Signed-off-by trailer:")
            for item in missing:
                print(f"  - {item}")
        if malformed:
            print("FAIL  commits with malformed Signed-off-by trailers:")
            for item in malformed:
                print(f"  - {item}")
        print("\nFix with: git commit -s   (or git rebase --signoff <base>)")
        return 1

    print("OK    every selected commit carries a valid Signed-off-by trailer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
