"""Execute the canonical provider-free public-source proof."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from swos_runtime.public_proof import PublicProofError, run_public_proof


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_public_proof(args.project, args.out)
    except PublicProofError as exc:
        print(json.dumps({"decision": "fail", "reasons": [str(exc)]}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
