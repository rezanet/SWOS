"""Verify an exact-commit release candidate and its compact release record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from swos_runtime.release_evidence import verify_release_candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = verify_release_candidate(candidate_dir=args.candidate)
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["decision"] == "allow" else 1


if __name__ == "__main__":
    raise SystemExit(main())
