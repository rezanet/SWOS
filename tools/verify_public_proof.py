"""Independently reproduce and compare a public-source proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from swos_runtime.public_proof import PublicProofError, reproduce_public_proof


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--reproduce-at", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = reproduce_public_proof(args.project, args.primary, args.reproduce_at)
    except PublicProofError as exc:
        report = {"decision": "fail", "reasons": [str(exc)]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report.get("decision") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
