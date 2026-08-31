#!/usr/bin/env python3
"""Create one exact-SHA release record from completed public-proof evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.release_record import ReleaseRecordError, create_release_record  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-sha", required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--reproduction", type=Path, required=True)
    parser.add_argument("--approved-by-id", required=True)
    parser.add_argument("--approved-by-name", required=True)
    parser.add_argument("--approved-at", required=True)
    parser.add_argument("--rationale", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        record = create_release_record(
            selected_sha=args.selected_sha,
            proof_dir=args.proof,
            reproduction_path=args.reproduction,
            approved_by_id=args.approved_by_id,
            approved_by_name=args.approved_by_name,
            approved_at=args.approved_at,
            rationale=args.rationale,
            output_path=args.out,
        )
    except ReleaseRecordError as exc:
        print(json.dumps({"decision": "deny", "reasons": [str(exc)]}, indent=2))
        return 1
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
