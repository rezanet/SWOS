#!/usr/bin/env python3
"""Dry-run-first operator CLI for the scoped Research Programme Memory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from swos_runtime.models import SWOSRuntimeError, canonical_digest  # noqa: E402
from swos_runtime.programme_store import ProgrammeStore, StoreIntegrityError  # noqa: E402
from swos_runtime.research_memory import (  # noqa: E402
    HumanApproval,
    ResearchMemoryService,
    ResearchScope,
    RPMOperation,
)
from swos_runtime.rpm_exchange import (  # noqa: E402
    BundleLimits,
    ExportSelection,
    ImportInspection,
    RPMExchange,
)


def _read(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path: str | Path, value: Any) -> None:
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _scope(path: str | Path) -> ResearchScope:
    data = _read(path)
    return ResearchScope(
        repository_namespace_id=str(data["repository_namespace_id"]),
        programme_id=str(data["programme_id"]),
        project_id=str(data["project_id"]),
    )


def _service(repository: str | Path) -> ResearchMemoryService:
    return ResearchMemoryService(ProgrammeStore(repository))


def _approval_data(path: str | Path) -> dict[str, Any]:
    data = _read(path)
    if not isinstance(data, dict):
        raise ValueError("approval file must contain an object")
    return data


def _approval_for_assessment(path: str | Path, assessment: Any) -> HumanApproval:
    data = _approval_data(path)
    required = {
        "approval_id",
        "approver",
        "role",
        "approved_at",
        "assessment_digest",
        "candidate_digest",
        "sdl_decision_id",
        "disposition",
        "rationale",
    }
    if required <= set(data):
        return HumanApproval(**data)
    return HumanApproval.for_assessment(
        assessment,
        approver=str(data.get("approver", "operator")),
        role=str(data.get("role", "memory_owner")),
    )


def _approval_for_exchange(path: str | Path) -> HumanApproval:
    data = _approval_data(path)
    required = {
        "approval_id",
        "approver",
        "role",
        "approved_at",
        "assessment_digest",
        "candidate_digest",
        "sdl_decision_id",
        "disposition",
        "rationale",
    }
    if not required <= set(data):
        raise ValueError("exchange approval must include complete approval evidence")
    return HumanApproval(**data)


def _serialize(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--repository", required=True)
    init.add_argument("--namespace", required=True)

    register = subparsers.add_parser("register-project")
    register.add_argument("--repository", required=True)
    register.add_argument("--scope-file", required=True)
    register.add_argument("--approval", required=True)
    register.add_argument("--label", default=None)
    register.add_argument("--manifest-digest", default=None)

    assess = subparsers.add_parser("assess-operation")
    assess.add_argument("--repository", required=True)
    assess.add_argument("--scope-file", required=True)
    assess.add_argument("--operation", required=True)
    assess.add_argument("--out", required=True)

    commit = subparsers.add_parser("commit-operation")
    commit.add_argument("--repository", required=True)
    commit.add_argument("--scope-file", required=True)
    commit.add_argument("--assessment", required=True)
    commit.add_argument("--approval", required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--repository", required=True)
    verify.add_argument("--scope-file", required=True)
    verify.add_argument("--json-out", default=None)

    expire = subparsers.add_parser("expire")
    expire.add_argument("--repository", required=True)
    expire.add_argument("--scope-file", required=True)
    expire.add_argument("--as-of", required=True)
    expire.add_argument("--commit", action="store_true")
    expire.add_argument("--approval", default=None)

    export = subparsers.add_parser("export")
    export.add_argument("--repository", required=True)
    export.add_argument("--scope-file", required=True)
    export.add_argument("--selection", required=True)
    export.add_argument("--approval", required=True)
    export.add_argument("--out", required=True)

    inspect = subparsers.add_parser("inspect-import")
    inspect.add_argument("--repository", required=True)
    inspect.add_argument("--bundle", required=True)
    inspect.add_argument("--destination", required=True)
    inspect.add_argument("--out", required=True)

    commit_import = subparsers.add_parser("commit-import")
    commit_import.add_argument("--repository", required=True)
    commit_import.add_argument("--inspection", required=True)
    commit_import.add_argument("--approval", required=True)

    rebuild = subparsers.add_parser("rebuild-projection")
    rebuild.add_argument("--repository", required=True)
    rebuild.add_argument("--scope-file", required=True)
    rebuild.add_argument("--verify-only", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            store = ProgrammeStore(args.repository)
            store.initialize()
            result = {
                "status": "initialized",
                "repository": str(args.repository),
                "namespace": args.namespace,
                "schema_version": "2.0.0",
            }
        elif args.command == "register-project":
            service = _service(args.repository)
            scope = _scope(args.scope_file)
            operation = RPMOperation.register_project(
                scope,
                label=args.label or _approval_data(args.approval).get("label", scope.project_id),
                manifest_digest=args.manifest_digest
                or _approval_data(args.approval).get(
                    "manifest_digest", canonical_digest(scope.to_dict())
                ),
            )
            assessment = service.assess_operation(scope, operation)
            approval = _approval_for_assessment(args.approval, assessment)
            result = service.commit_operation(
                scope, assessment_id=assessment.assessment_id, approval=approval
            ).to_dict()
        elif args.command == "assess-operation":
            service = _service(args.repository)
            scope = _scope(args.scope_file)
            result = service.assess_operation(scope, _read(args.operation)).to_dict()
            _write(args.out, result)
        elif args.command == "commit-operation":
            service = _service(args.repository)
            scope = _scope(args.scope_file)
            assessment_data = _read(args.assessment)
            assessment_id = str(assessment_data["assessment_id"])
            stored = service.store.get_assessment(assessment_id)
            if stored is None:
                raise ValueError("assessment is not present in the repository")
            assessment = service._assessment_from_dict(stored)
            approval = _approval_for_assessment(args.approval, assessment)
            result = service.commit_operation(
                scope, assessment_id=assessment_id, approval=approval
            ).to_dict()
        elif args.command == "verify":
            store = ProgrammeStore(args.repository)
            scope = _scope(args.scope_file)
            errors = store.verify_chain(scope)
            result = {
                "status": "fail" if errors else "pass",
                "scope": scope.to_dict(),
                "errors": errors,
                "head": store.chain_head(scope),
            }
            if errors:
                raise StoreIntegrityError("; ".join(errors))
            if args.json_out:
                _write(args.json_out, result)
        elif args.command == "expire":
            service = _service(args.repository)
            scope = _scope(args.scope_file)
            report = service.propose_expiry(scope, as_of=args.as_of)
            result = report.to_dict()
            if args.commit:
                if not args.approval:
                    raise ValueError("--approval is required with --commit")
                committed = []
                for candidate in report.candidates:
                    assessment = service.assess_operation(
                        scope, RPMOperation.expire(scope, candidate["item_id"]), as_of=args.as_of
                    )
                    approval = _approval_for_assessment(args.approval, assessment)
                    committed.append(
                        service.commit_operation(
                            scope,
                            assessment_id=assessment.assessment_id,
                            approval=approval,
                            as_of=args.as_of,
                        ).to_dict()
                    )
                result["committed"] = committed
        elif args.command == "export":
            service = _service(args.repository)
            scope = _scope(args.scope_file)
            selection = ExportSelection(**_read(args.selection))
            approval = _approval_for_exchange(args.approval)
            result = RPMExchange(service).export_bundle(
                scope, selection, approval, BundleLimits(), args.out
            )
            result = _serialize(result)
        elif args.command == "inspect-import":
            service = _service(args.repository)
            scope = _scope(args.destination)
            inspection = RPMExchange(service).inspect_import(
                args.bundle, destination=scope, limits=BundleLimits()
            )
            result = _serialize(inspection)
            _write(args.out, result)
        elif args.command == "commit-import":
            service = _service(args.repository)
            data = _read(args.inspection)
            origin = ResearchScope(**data["origin_scope"])
            destination = ResearchScope(**data["destination_scope"])
            inspection = ImportInspection(
                inspection_id=data["inspection_id"],
                inspection_digest=data["inspection_digest"],
                source_bundle_digest=data["source_bundle_digest"],
                origin_scope=origin,
                destination_scope=destination,
                commit_eligible=bool(data["commit_eligible"]),
                diff=dict(data["diff"]),
                checks=dict(data["checks"]),
                events=tuple(data.get("events", [])),
                warnings=tuple(data.get("warnings", [])),
            )
            exchange = RPMExchange(service)
            exchange._inspections[inspection.inspection_id] = inspection
            result = _serialize(
                exchange.commit_import(
                    inspection.inspection_id,
                    inspection.inspection_digest,
                    _approval_for_exchange(args.approval),
                )
            )
        else:
            store = ProgrammeStore(args.repository)
            scope = _scope(args.scope_file)
            result = {"status": "pass", "scope": scope.to_dict()}
            if not args.verify_only:
                result["projection"] = store.rebuild_projection(scope)
        print(json.dumps(_serialize(result), sort_keys=True, ensure_ascii=False))
        return 0
    except (ValueError, OSError, SWOSRuntimeError, StoreIntegrityError) as exc:
        print(json.dumps({"status": "denied", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
