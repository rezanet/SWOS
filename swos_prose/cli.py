"""CLI for the Milestone-1 SWOS Prose verifier."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import verify_rewrite


def _read(value: str) -> str:
    path = Path(value)
    return path.read_text(encoding="utf-8") if path.exists() else value


def main() -> int:
    parser = argparse.ArgumentParser(description="SWOS Prose semantic-delta verifier")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="Compare a source with a candidate rewrite")
    verify.add_argument("--source", required=True, help="Source file path or literal text")
    verify.add_argument("--candidate", required=True, help="Candidate file path or literal text")
    verify.add_argument("--assurance", choices=("standard", "strict", "review"), default="standard")
    verify.add_argument("--json", action="store_true", dest="as_json")

    args = parser.parse_args()
    result = verify_rewrite(
        source=_read(args.source),
        candidate=_read(args.candidate),
        assurance=args.assurance,
    )

    if args.as_json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"SWOS Prose verification: {result.status.value}")
        for delta in result.semantic_deltas:
            print(f"- {delta.severity.value.upper()} {delta.delta_type.value}: {delta.explanation}")
        for note in result.notes:
            print(f"  note: {note}")

    return 0 if result.safe_for_automatic_use else 1


if __name__ == "__main__":
    raise SystemExit(main())
