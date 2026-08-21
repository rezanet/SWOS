"""CLI for SWOS Prose verification and local dogfooding."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .pipeline import verify_rewrite


def _read(value: str) -> str:
    path = Path(value)
    return path.read_text(encoding="utf-8") if path.exists() else value


def _run_verify(args: argparse.Namespace) -> int:
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


def _run_dogfood(args: argparse.Namespace) -> int:
    from .dogfood import collect_dogfood, load_simple_env_file
    from .providers.openai_responses import OpenAIResponsesSemanticVerifierProvider
    from .providers.openai_rewrite import OpenAIResponsesRewriteProvider

    if args.env_file:
        try:
            loaded = load_simple_env_file(args.env_file)
        except (FileNotFoundError, ValueError) as exc:
            print(f"SWOS Prose dogfood setup error: {exc}")
            return 2
        if loaded:
            print(f"Loaded local environment keys: {', '.join(loaded)}")

    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "SWOS Prose dogfood requires OPENAI_API_KEY in the process environment "
            "or in the explicitly supplied --env-file."
        )
        return 2

    try:
        rewriter = OpenAIResponsesRewriteProvider(model=args.rewriter_model)
        verifier = OpenAIResponsesSemanticVerifierProvider(model=args.verifier_model)
        records = collect_dogfood(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            rewrite_provider=rewriter,
            verifier_provider=verifier,
            assurance=args.assurance,
            run_diagnostics=not args.skip_diagnostics,
        )
    except (RuntimeError, TypeError, ValueError) as exc:
        print(f"SWOS Prose dogfood failed safely: {exc}")
        return 2

    counts: dict[str, int] = {}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    rendered = ", ".join(f"{key}={counts[key]}" for key in sorted(counts))
    print(f"SWOS Prose dogfood complete: {len(records)} sample(s); {rendered}")
    print(f"Results: {Path(args.output_dir) / 'summary.json'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SWOS Prose semantic-safe editing tools")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="Compare a source with a candidate rewrite")
    verify.add_argument("--source", required=True, help="Source file path or literal text")
    verify.add_argument("--candidate", required=True, help="Candidate file path or literal text")
    verify.add_argument("--assurance", choices=("standard", "strict", "review"), default="standard")
    verify.add_argument("--json", action="store_true", dest="as_json")

    dogfood = sub.add_parser("dogfood", help="Run local polish dogfood samples and save JSON results")
    dogfood.add_argument("--input-dir", required=True, help="Directory containing local .md/.txt samples")
    dogfood.add_argument("--output-dir", required=True, help="Directory for local JSON results")
    dogfood.add_argument("--assurance", choices=("standard", "strict", "review"), default="strict")
    dogfood.add_argument(
        "--env-file",
        default=None,
        help="Optional simple KEY=VALUE file to load explicitly; existing environment variables win",
    )
    dogfood.add_argument("--rewriter-model", default=None, help="Optional rewrite-provider model override")
    dogfood.add_argument("--verifier-model", default=None, help="Optional verifier-provider model override")
    dogfood.add_argument(
        "--skip-diagnostics",
        action="store_true",
        help=(
            "Disable pre-generation abstention. Intended for semantic-calibration campaigns "
            "that must exercise the rewrite/verifier path even on already-good prose."
        ),
    )

    args = parser.parse_args()
    if args.command == "verify":
        return _run_verify(args)
    if args.command == "dogfood":
        return _run_dogfood(args)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
