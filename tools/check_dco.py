#!/usr/bin/env python3
"""Verify every commit in the range carries a DCO Signed-off-by trailer."""
import subprocess
import sys


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    try:
        out = subprocess.run(
            ["git", "log", "--format=%H%x1f%s%x1f%b%x1e", f"{base}..HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        print(f"error: could not read git log: {exc}")
        return 2

    missing = []
    for record in filter(None, (r.strip() for r in out.split("\x1e"))):
        sha, subject, body = (record.split("\x1f") + ["", ""])[:3]
        if "Signed-off-by:" not in body:
            missing.append(f"{sha[:8]} {subject}")

    if missing:
        print("FAIL  commits without a DCO sign-off:")
        for m in missing:
            print(f"  - {m}")
        print("\nFix with:  git commit -s   (or  git rebase --signoff <base>)")
        return 1

    print("OK    all commits carry a DCO sign-off.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
