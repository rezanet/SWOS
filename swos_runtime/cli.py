"""Command-line entry point for Autonomous SWOS."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import ResearchRequest
from .orchestrator import AutonomousSWOS


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="swos", description="Autonomous governed SWOS research-writing runtime"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser(
        "research-write",
        help="Run research -> evidence -> argument -> draft -> verify -> review -> audit",
    )
    write.add_argument("--topic", required=True)
    write.add_argument("--length", type=int, default=2500)
    write.add_argument("--audience", default="intelligent general reader")
    write.add_argument("--style", default="scholarly-natural")
    write.add_argument("--depth", default="rigorous")
    write.add_argument("--jurisdiction", default=None)
    write.add_argument("--output", type=Path, required=True)
    write.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    if args.command == "research-write":
        request = ResearchRequest(
            topic=args.topic,
            length=args.length,
            audience=args.audience,
            style=args.style,
            depth=args.depth,
            jurisdiction=args.jurisdiction,
        )
        outcome = AutonomousSWOS().run(request, args.output)
        if args.as_json:
            print(json.dumps(outcome.to_dict(), indent=2))
        else:
            print(
                f"{outcome.status}: {outcome.output_dir} ({outcome.article_word_count} body words)"
            )
            for reason in outcome.blocking_reasons:
                print(f"- {reason}")
        return 0 if outcome.status == "APPROVED" else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
