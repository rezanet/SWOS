"""Command-line entry point for Autonomous SWOS."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .host_bundle import (
    HostBundleRetriever,
    HostBundleStageProvider,
    host_prose_transform,
    load_host_bundle,
)
from .models import ResearchRequest
from .orchestrator import AutonomousSWOS
from .work_orders import WorkOrderError, WorkOrderRun


def _print(payload, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        if isinstance(payload, dict):
            for key, value in payload.items():
                print(f"{key}: {value}")
        else:
            print(payload)


def _request_from_dict(payload: dict) -> ResearchRequest:
    fields = {
        "topic",
        "length",
        "audience",
        "style",
        "depth",
        "jurisdiction",
        "citation_style",
        "date_cutoff",
    }
    return ResearchRequest(**{key: value for key, value in payload.items() if key in fields})


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
        "--host-bundle",
        type=Path,
        default=None,
        help=(
            "Replay a SWOS-generated host-native bundle instead of the default API-backed "
            "reference binding. Users should not hand-assemble host bundles."
        ),
    )
    write.add_argument("--json", action="store_true", dest="as_json")

    start = sub.add_parser(
        "start",
        help="Start a host-native subscription run and issue the first SWOS work order",
    )
    start.add_argument("request", type=Path, help="JSON ResearchRequest")
    start.add_argument("--adapter", type=Path, required=True, help="swos.capabilities.v1 manifest")
    start.add_argument("--run-root", type=Path, default=Path(".swos/runs"))
    start.add_argument("--json", action="store_true", dest="as_json")

    next_work = sub.add_parser("next-work", help="Return the next SWOS-owned work order")
    next_work.add_argument("run_dir", type=Path)
    next_work.add_argument("--json", action="store_true", dest="as_json")

    submit = sub.add_parser("submit", help="Submit one host capability result to SWOS")
    submit.add_argument("run_dir", type=Path)
    submit.add_argument("result", type=Path)
    submit.add_argument("--json", action="store_true", dest="as_json")

    status = sub.add_parser("status", help="Show a host-native SWOS run state")
    status.add_argument("run_dir", type=Path)
    status.add_argument("--json", action="store_true", dest="as_json")

    export = sub.add_parser(
        "export-host-bundle",
        help="Generate the replay/interchange bundle from accepted SWOS work-order submissions",
    )
    export.add_argument("run_dir", type=Path)
    export.add_argument("--output", type=Path, default=None)
    export.add_argument("--json", action="store_true", dest="as_json")

    finalise = sub.add_parser(
        "finalise",
        help="Run final SWOS governance/replay from a completed host-native subscription run",
    )
    finalise.add_argument("run_dir", type=Path)
    finalise.add_argument("--output", type=Path, required=True)
    finalise.add_argument("--json", action="store_true", dest="as_json")

    args = parser.parse_args()

    try:
        if args.command == "start":
            run = WorkOrderRun.start_from_files(
                request_path=args.request,
                adapter_path=args.adapter,
                root=args.run_root,
            )
            payload = {**run.status(), "work_order": run.work_order()}
            _print(payload, args.as_json)
            return 0

        if args.command == "next-work":
            run = WorkOrderRun(args.run_dir)
            order = run.work_order()
            if order is None:
                _print(run.status(), args.as_json)
                return 0
            _print(order, args.as_json)
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
            _print({"host_bundle": str(path), **run.status()}, args.as_json)
            return 0

        if args.command == "finalise":
            run = WorkOrderRun(args.run_dir)
            if run.status()["status"] != "READY_TO_FINALISE":
                raise WorkOrderError(
                    f"run must be READY_TO_FINALISE, got {run.status()['status']}"
                )
            bundle_path = run.export_host_bundle()
            bundle = load_host_bundle(bundle_path)
            runtime = AutonomousSWOS(
                stage_provider=HostBundleStageProvider(bundle),
                retriever=HostBundleRetriever(bundle),
                prose_transform=host_prose_transform(bundle),
            )
            outcome = runtime.run(_request_from_dict(run.state["request"]), args.output)
            (run.run_dir / "final-outcome.json").write_text(
                json.dumps(outcome.to_dict(), indent=2) + "\n", encoding="utf-8"
            )
            run.state["status"] = outcome.status
            run.state["final_output"] = str(args.output)
            run._save()
            run._persist_work_order()
            _print(outcome.to_dict(), args.as_json)
            return 0 if outcome.status == "APPROVED" else 1

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
                bundle = load_host_bundle(args.host_bundle)
                runtime = AutonomousSWOS(
                    stage_provider=HostBundleStageProvider(bundle),
                    retriever=HostBundleRetriever(bundle),
                    prose_transform=host_prose_transform(bundle),
                )
            else:
                runtime = AutonomousSWOS()
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
    except (WorkOrderError, ValueError, json.JSONDecodeError) as exc:
        if getattr(args, "as_json", False):
            print(json.dumps({"error": str(exc)}, indent=2))
        else:
            print(f"ERROR: {exc}")
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
