"""Assemble exact-commit SWOS release evidence without a private signing key."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from swos_runtime.release_evidence import ReleaseEvidenceError, build_release_candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--selected-sha", required=True)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--reproduction", type=Path, required=True)
    parser.add_argument("--release-approval", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--built-at", required=True)
    args = parser.parse_args()
    try:
        manifest = build_release_candidate(
            repo_root=args.repo,
            selected_sha=args.selected_sha,
            proof_dir=args.proof,
            reproduction_path=args.reproduction,
            release_approval_dir=args.release_approval,
            out_dir=args.out,
            built_at=args.built_at,
        )
    except ReleaseEvidenceError as exc:
        print(json.dumps({"decision": "deny", "reasons": [str(exc)]}, indent=2))
        return 1
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
