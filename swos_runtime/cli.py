"""Command-line entry point for Autonomous SWOS."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .adapter_factory import build_openai_api_broker, build_replay_broker
from .finalizer import finalize_work_order_run
from .models import ResearchRequest
from .orchestrator import AutonomousSWOS
from .release_approval import (
    ReleaseApprovalError,
    prepare_approval_pack,
    record_release_decision,
)
from .work_orders import WorkOrderError, WorkOrderRun


def _print(payload, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    elif isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}: {value}")
    else:
        print(payload)


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
    write.add_argument(
        "--adapter",
        choices=["openai-api"],
        default="openai-api",
        help="Concrete direct-execution adapter. SWOS core remains provider-neutral.",
    )
    write.add_argument(
        "--host-bundle",
        type=Path,
        default=None,
        help=(
            "Replay a canonical SWOS host bundle for reproducibility/debugging. "
            "This is not the live subscription execution mechanism."
        ),
    )
    write.add_argument("--json", action="store_true", dest="as_json")

    start = sub.add_parser(
        "start",
        help="Start a live host/subscription run and issue the first SWOS work order",
    )
    start.add_argument("request", type=Path, help="JSON ResearchRequest")
    start.add_argument("--adapter", type=Path, required=True, help="swos.capabilities.v1 manifest")
    start.add_argument("--run-root", type=Path, default=Path(".swos/runs"))
    start.add_argument("--json", action="store_true", dest="as_json")

    next_work = sub.add_parser("next-work", help="Return the next SWOS-owned work order")
    next_work.add_argument("run_dir", type=Path)
    next_work.add_argument("--json", action="store_true", dest="as_json")

    submit = sub.add_parser("submit", help="Submit one bounded host capability result to SWOS")
    submit.add_argument("run_dir", type=Path)
    submit.add_argument("result", type=Path)
    submit.add_argument("--json", action="store_true", dest="as_json")

    status = sub.add_parser("status", help="Show a SWOS work-order run state")
    status.add_argument("run_dir", type=Path)
    status.add_argument("--json", action="store_true", dest="as_json")

    export = sub.add_parser(
        "export-host-bundle",
        help="Generate replay/interchange/debug/reproducibility evidence from accepted work",
    )
    export.add_argument("run_dir", type=Path)
    export.add_argument("--output", type=Path, default=None)
    export.add_argument("--json", action="store_true", dest="as_json")

    finalise = sub.add_parser(
        "finalise",
        help="Run provider-neutral SWOS governance and audit assembly",
    )
    finalise.add_argument("run_dir", type=Path)
    finalise.add_argument("--output", type=Path, required=True)
    finalise.add_argument("--json", action="store_true", dest="as_json")

    prepare = sub.add_parser(
        "prepare-approval", help="Prepare risk-first evidence for a separate human approver"
    )
    prepare.add_argument("--run-dir", type=Path, required=True)
    prepare.add_argument("--evaluation", type=Path, required=True)
    prepare.add_argument("--author", type=Path, required=True)
    prepare.add_argument("--contract-owner", type=Path, required=True)
    prepare.add_argument("--evaluation-owner", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--created-at", default=None)
    prepare.add_argument("--json", action="store_true", dest="as_json")

    approval = sub.add_parser(
        "record-approval", help="Record a human-supplied release approval or rejection"
    )
    approval.add_argument("--release-dir", type=Path, required=True)
    approval.add_argument("--decision", type=Path, required=True)
    approval.add_argument("--json", action="store_true", dest="as_json")

    args = parser.parse_args()

    try:
        if args.command == "start":
            run = WorkOrderRun.start_from_files(
                request_path=args.request,
                adapter_path=args.adapter,
                root=args.run_root,
            )
            _print({**run.status(), "work_order": run.work_order()}, args.as_json)
            return 0

        if args.command == "next-work":
            run = WorkOrderRun(args.run_dir)
            _print(run.work_order() or run.status(), args.as_json)
            return 0

        if args.command == "submit":
            run = WorkOrderRun(args.run_dir)
            result = json.loads(args.result.read_text(encoding="utf-8"))
            payload = run.submit(result)
            payload["work_order"] = run.work_order()
            _print(payload, args.as_json)
            return 0 if payload["status"] != "REVIEW_REQUIRED" else 1

        if args.command == "status":
            _print(WorkOrderRun(args.run_dir).status(), args.as_json)
            return 0

        if args.command == "export-host-bundle":
            run = WorkOrderRun(args.run_dir)
            path = run.export_host_bundle(args.output)
            _print(
                {
                    "host_bundle": str(path),
                    "bundle_role": "replay_interchange_debug_reproducibility",
                    **run.status(),
                },
                args.as_json,
            )
            return 0

        if args.command == "finalise":
            run = WorkOrderRun(args.run_dir)
            outcome = finalize_work_order_run(run, args.output)
            (run.run_dir / "final-outcome.json").write_text(
                json.dumps(outcome.to_dict(), indent=2) + "\n", encoding="utf-8"
            )
            run.state["status"] = outcome.status
            run.state["final_output"] = str(args.output)
            run._save()
            run._persist_work_order()
            _print(outcome.to_dict(), args.as_json)
            return 0 if outcome.status == "APPROVED" else 1

        if args.command == "prepare-approval":
            pack = prepare_approval_pack(
                args.run_dir,
                args.evaluation,
                args.output,
                author=json.loads(args.author.read_text(encoding="utf-8")),
                contract_owner=json.loads(args.contract_owner.read_text(encoding="utf-8")),
                evaluation_owner=json.loads(args.evaluation_owner.read_text(encoding="utf-8")),
                created_at=args.created_at or datetime.now(timezone.utc).isoformat(),
            )
            _print(pack, args.as_json)
            return 0

        if args.command == "record-approval":
            ledger = record_release_decision(
                args.release_dir,
                json.loads(args.decision.read_text(encoding="utf-8")),
            )
            _print(ledger, args.as_json)
            return 0

        if args.command == "research-write":
            request = ResearchRequest(
                topic=args.topic,
                length=args.length,
                audience=args.audience,
                style=args.style,
                depth=args.depth,
                jurisdiction=args.jurisdiction,
            )
            if args.host_bundle is not None:
                broker, manifest = build_replay_broker(args.host_bundle)
            else:
                broker, manifest = build_openai_api_broker()
            runtime = AutonomousSWOS(broker=broker, adapter_manifest=manifest)
            outcome = runtime.run(request, args.output)
            if args.as_json:
                print(json.dumps(outcome.to_dict(), indent=2))
            else:
                print(
                    f"{outcome.status}: {outcome.output_dir} ({outcome.article_word_count} body words)"
                )
                for reason in outcome.blocking_reasons:
                    print(f"- {reason}")
            return 0 if outcome.status == "APPROVED" else 1
    except (WorkOrderError, ReleaseApprovalError, ValueError, json.JSONDecodeError) as exc:
        if getattr(args, "as_json", False):
            print(json.dumps({"error": str(exc)}, indent=2))
        else:
            print(f"ERROR: {exc}")
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
