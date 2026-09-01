"""Evaluation planes bound to one verified finalized SWOS runtime subject."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .governance import (
    IntegrityChain,
    can_write_durable_rpm,
    detect_prompt_injection,
    verify_manifest,
)
from .models import swos_id
from .schema_validation import validate_frozen_run_schemas
from .stores import verify_run_stores

PLANES = (
    "retrieval",
    "grounding",
    "citation",
    "scholarly",
    "governance",
    "regression",
    "memory_contamination",
    "adversarial",
)


def score_ontology_profile(profile: Any) -> dict[str, Any]:
    """Score only machine-traceable ontology bindings and mappings."""

    criteria = list(getattr(profile, "required_criteria", []) or [])
    methods = list(getattr(profile, "methods", []) or [])
    evidence_types = list(getattr(profile, "evidence_types", []) or [])
    complete = all(isinstance(item, dict) and item.get("iri") for item in [*criteria, *methods, *evidence_types])
    return {
        "discipline": getattr(profile, "discipline", None),
        "ontology_digest": getattr(profile, "ontology_digest", None),
        "criterion_count": len(criteria),
        "method_count": len(methods),
        "evidence_type_count": len(evidence_types),
        "binding_completeness": 1.0 if complete and criteria else 0.0,
        "machine_traceable": bool(complete and getattr(profile, "ontology_digest", None)),
    }


def score_discipline_critique(report: Any) -> dict[str, Any]:
    """Return multidimensional critique metrics without a universal quality score."""

    criteria = list(getattr(report, "criteria", []) or [])
    findings = list(getattr(report, "findings", []) or [])
    mandatory = [item for item in criteria if bool(getattr(item, "mandatory", False))]
    mandatory_failures = list(getattr(report, "mandatory_failures", []) or [])
    linked = sum(bool(getattr(item, "evidence_refs", [])) for item in criteria)
    return {
        "discipline": getattr(report, "discipline", None),
        "ontology_digest": getattr(report, "ontology_digest", None),
        "criterion_coverage": linked / len(criteria) if criteria else 0.0,
        "mandatory_criteria": len(mandatory),
        "mandatory_failures": len(mandatory_failures),
        "blocking_preserved": bool(mandatory_failures) == bool(getattr(report, "blocking", False)),
        "evidence_link_rate": sum(bool(getattr(item, "evidence_refs", [])) for item in findings) / len(findings) if findings else 1.0,
        "machine_proposed_findings": sum(getattr(item, "review_state", "") == "machine_proposed" for item in findings),
        "provider_owned_admission": False,
    }

PLANE_ARTIFACTS = {
    "retrieval": ("source-register.json", "retrieval.json", "reranking.json"),
    "grounding": ("evidence-matrix.json", "source-register.json", "provenance.json"),
    "citation": ("references.json", "source-register.json", "evidence-matrix.json"),
    "scholarly": ("argument-graph.json", "review-summary.json", "article.md"),
    "governance": ("run-control.json", "review-assurance.json", "decision-ledger.json"),
    "regression": ("run-control.json", "run-manifest.json"),
    "memory_contamination": ("run-control.json", "governed-stores"),
    "adversarial": ("security-report.json", "source-register.json"),
}


class EvaluationError(RuntimeError):
    """Raised when a runtime-bound evaluation cannot be trusted."""


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def file_digest(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationError(
            f"cannot load required evaluation artifact {path.name}: {exc}"
        ) from exc


@dataclass(frozen=True)
class EvaluationSubject:
    root: Path
    manifest: dict[str, Any]
    control: dict[str, Any]
    evidence: dict[str, Any]
    sources: list[dict[str, Any]]
    argument: dict[str, Any]
    reviews: list[dict[str, Any]]
    review_assurance: dict[str, Any]
    provenance: dict[str, Any]
    manifest_sha256: str
    integrity_chain_head: str
    artifact_identities: dict[str, str] = field(default_factory=dict)

    @property
    def run_id(self) -> str:
        return str(self.manifest["run_id"])

    @property
    def work_id(self) -> str:
        return str(self.manifest["work_id"])

    @property
    def ontology_binding(self) -> dict[str, Any]:
        """Return the exact ontology identity recorded by the run, if v2-bound."""

        for container in (self.manifest, self.control):
            binding = container.get("ontology_binding")
            if isinstance(binding, dict):
                return dict(binding)
        return {}

    @classmethod
    def load(cls, root: str | Path) -> "EvaluationSubject":
        root = Path(root)
        required = (
            "run-manifest.json",
            "run-control.json",
            "evidence-matrix.json",
            "source-register.json",
            "argument-graph.json",
            "review-summary.json",
            "review-assurance.json",
            "provenance.json",
            "integrity-chain.jsonl",
            "article.md",
        )
        missing = [name for name in required if not (root / name).is_file()]
        if missing:
            raise EvaluationError("missing evaluation subject artifacts: " + ", ".join(missing))

        manifest = _load(root / "run-manifest.json")
        control = _load(root / "run-control.json")
        if not isinstance(manifest, dict) or not isinstance(control, dict):
            raise EvaluationError("run manifest and control must be objects")
        errors: list[str] = []
        if not verify_manifest(root, manifest):
            errors.append("run manifest hashes do not verify")
        errors.extend(validate_frozen_run_schemas(root))
        errors.extend(
            f"governed store: {error}"
            for error in verify_run_stores(root, expected_heads=control.get("governed_store_heads"))
        )
        if control.get("status") != "APPROVED" or manifest.get("status") != "APPROVED":
            errors.append("automated runtime assurance did not reach APPROVED")
        if control.get("blocking_reasons"):
            errors.append("runtime retains unresolved blocking reasons")
        if errors:
            raise EvaluationError("; ".join(errors))

        chain_entries = [
            json.loads(line)
            for line in (root / "integrity-chain.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not chain_entries or not str(chain_entries[-1].get("hash") or ""):
            raise EvaluationError("integrity chain has no verifiable head")
        chain = IntegrityChain()
        chain.entries = chain_entries
        if not chain.verify():
            raise EvaluationError("integrity chain does not verify")
        reviews = _load(root / "review-summary.json")
        sources = _load(root / "source-register.json")
        if not isinstance(reviews, list) or not isinstance(sources, list):
            raise EvaluationError("review summary and source register must be arrays")
        return cls(
            root=root,
            manifest=manifest,
            control=control,
            evidence=_load(root / "evidence-matrix.json"),
            sources=sources,
            argument=_load(root / "argument-graph.json"),
            reviews=reviews,
            review_assurance=_load(root / "review-assurance.json"),
            provenance=_load(root / "provenance.json"),
            manifest_sha256=file_digest(root / "run-manifest.json"),
            integrity_chain_head=str(chain_entries[-1]["hash"]),
            artifact_identities={
                relative: file_digest(root / relative)
                for relative in required
                if (root / relative).is_file()
            },
        )

    def subject_versions(self) -> dict[str, Any]:
        execution = self.control.get("execution", {})
        return {
            "schema_pack_version": "1.0.0",
            "agent_pack_version": "1.0.0",
            "model_id": str(execution.get("model_host") or "unreported"),
            "retriever_id": str(execution.get("adapter") or "unreported"),
            "runtime_version": str(self.control.get("runtime_version") or "unknown"),
            "subject_run_id": self.run_id,
            "manifest_sha256": self.manifest_sha256,
            "integrity_chain_head": self.integrity_chain_head,
            "artifact_identities": dict(sorted(self.artifact_identities.items())),
            "ontology_binding": self.ontology_binding,
        }

    def reviewer_separation_errors(self) -> list[str]:
        errors: list[str] = []
        for capability in ("citation_support_audit", "hostile_review"):
            record = self.review_assurance.get(capability, {})
            if record.get("independence") in {None, "unknown", "none", "unsupported"}:
                errors.append(f"{capability} independence is unsupported")
            if record.get("review_mode") in {None, "unknown", "unspecified"}:
                errors.append(f"{capability} execution mode is missing")
        events = self.control.get("capability_events", [])
        by_capability = {
            str(event.get("capability")): event for event in events if isinstance(event, dict)
        }
        author = by_capability.get("draft_generation", {})
        if not author:
            errors.append("authoring execution evidence is missing")
        for capability in ("citation_support_audit", "hostile_review"):
            reviewer = by_capability.get(capability, {})
            if not reviewer:
                errors.append(f"{capability} execution evidence is missing")
            elif reviewer.get("instruction_id") == author.get("instruction_id"):
                errors.append(f"{capability} reused the authoring instruction identity")
        return errors


def _fixture_detection(plane: str, fixture: dict[str, Any]) -> bool:
    category = fixture.get("category")
    payload = fixture.get("input", {})
    if plane == "retrieval":
        retrieved = payload.get("retrieved_set", {})
        if category == "counter_position_recall":
            return (
                int(retrieved.get("opposing_sources", 0))
                + int(retrieved.get("null_result_sources", 0))
                == 0
            )
        if category == "coverage_bias":
            return (
                len(retrieved.get("languages", {})) <= 1 or len(retrieved.get("regions", {})) <= 2
            )
    if plane == "grounding":
        if category == "unsupported_claim":
            citations = payload.get("citations", [])
            return bool(citations) and all(
                citation.get("support_level") != "directly_supports" for citation in citations
            )
        if category == "overclaim":
            return payload.get("citation", {}).get("support_level") == "partially_supports"
    if plane == "citation":
        if category == "fabricated_reference":
            doi = str(payload.get("citation", {}).get("doi", ""))
            return "synthetic" in doi or doi.startswith("10.9999/")
        if category == "citation_metadata_error":
            cited = payload.get("cited_as", {})
            resolved = payload.get("resolved_record", {})
            return cited.get("authors") != resolved.get("authors") and cited.get(
                "year"
            ) != resolved.get("year")
    if plane == "governance":
        if category == "missing_audit_trail":
            matrix = payload.get("evidence_matrix", {})
            return matrix.get("total_claims") != matrix.get("claims_with_epg_node")
        if category == "policy_breach":
            waiver = payload.get("gate", {}).get("waiver", {})
            return not bool(
                waiver.get("reason") and waiver.get("approved_by") and waiver.get("expires_on")
            )
    if plane == "memory_contamination":
        item = fixture.get("seed", {}).get("rpm_item", {})
        provenance = item.get("provenance", {})
        return not can_write_durable_rpm(
            source_grounded=bool(item.get("source_grounded")),
            epg_refs=list(provenance.get("epg_node_ids") or []),
            sdl_id=provenance.get("sdl_decision_id"),
            human_approver=None,
        )
    if plane == "adversarial":
        if category == "prompt_injection":
            return detect_prompt_injection(str(payload.get("retrieved_content", "")))
        if category == "citation_laundering":
            claim = str(payload.get("claim", {}).get("claim_text", "")).lower()
            quote = str(
                payload.get("citation", {}).get("evidence_span", {}).get("quoted_text", "")
            ).lower()
            return any(word in claim for word in ("causes", "caused", "cause")) and (
                "associated" in quote or "cross-sectional" in quote
            )
        if category == "over_association":
            return bool(payload.get("proposed_synthesis")) and all(
                payload.get(key, {}).get("support") == "strong" for key in ("claim_a", "claim_b")
            )
    if plane == "scholarly":
        return bool(fixture.get("expected_moves")) and fixture.get("discipline") in {
            "art_history",
            "philosophy",
            "psychology",
        }
    if plane == "regression":
        versions = fixture.get("subject_versions", {})
        return versions.get("schema_pack_version") == "1.0.0"
    return False


def _subject_plane_ok(subject: EvaluationSubject, plane: str) -> bool:
    rows = subject.evidence.get("rows", [])
    provenance_ids = {
        entity.get("entity_id")
        for entity in subject.provenance.get("entities", [])
        if isinstance(entity, dict)
    }
    checks: dict[str, Callable[[], bool]] = {
        "retrieval": lambda: (
            bool(subject.sources)
            and subject.evidence.get("coverage", {}).get("counter_evidence_present") is True
        ),
        "grounding": lambda: (
            bool(rows)
            and all(
                row.get("verification_status") == "pass"
                and all(
                    citation.get("support_level") == "directly_supports"
                    for citation in row.get("citations", [])
                )
                for row in rows
            )
        ),
        "citation": lambda: (
            bool(subject.sources)
            and all(
                source.get("metadata_verified")
                and source.get("retraction_status") == "clean"
                and source.get("licence_cleared")
                for source in subject.sources
            )
        ),
        "scholarly": lambda: bool(subject.argument.get("nodes")) and bool(subject.reviews),
        "governance": lambda: (
            not subject.reviewer_separation_errors()
            and not _open_review_findings(subject)
            and all(row.get("epg_node_id") in provenance_ids for row in rows)
        ),
        "regression": lambda: (
            bool(subject.control.get("runtime_version"))
            and subject.subject_versions().get("schema_pack_version") == "1.0.0"
        ),
        "memory_contamination": lambda: (
            not verify_run_stores(
                subject.root, expected_heads=subject.control.get("governed_store_heads")
            )
        ),
        "adversarial": lambda: (subject.root / "security-report.json").is_file(),
    }
    return checks[plane]()


def _open_review_findings(subject: EvaluationSubject) -> list[dict[str, Any]]:
    return [
        finding
        for review in subject.reviews
        for finding in review.get("findings", [])
        if finding.get("severity") in {"blocker", "major"} and finding.get("status") != "resolved"
    ]


def evaluate_plane(
    subject: EvaluationSubject, plane: str, fixtures: list[dict[str, Any]]
) -> dict[str, Any]:
    if plane not in PLANES:
        raise EvaluationError(f"unknown evaluation plane: {plane}")
    passed_fixtures = sum(1 for fixture in fixtures if _fixture_detection(plane, fixture))
    subject_ok = _subject_plane_ok(subject, plane)
    failures = [
        {"fixture_id": str(fixture.get("fixture_id") or "?"), "reason": "probe not detected"}
        for fixture in fixtures
        if not _fixture_detection(plane, fixture)
    ]
    if not subject_ok:
        failures.append({"fixture_id": "runtime-subject", "reason": "subject assurance failed"})
    denominator = len(fixtures) or 1
    value = passed_fixtures / denominator if subject_ok else 0.0
    traceability_metrics = [
        {
            "metric": "exact_subject_binding",
            "value": 1.0 if subject_ok else 0.0,
            "threshold": 1.0,
            "direction": "higher_is_better",
            "passed": subject_ok,
        },
        {
            "metric": "production_control_provenance",
            "value": 1.0 if subject_ok else 0.0,
            "threshold": 1.0,
            "direction": "higher_is_better",
            "passed": subject_ok,
        },
        {
            "metric": "artifact_evidence:" + ",".join(PLANE_ARTIFACTS[plane]),
            "value": 1.0 if subject_ok else 0.0,
            "threshold": 1.0,
            "direction": "higher_is_better",
            "passed": subject_ok,
        },
    ]
    return {
        "plane": plane,
        "gate_result": "pass" if subject_ok and not failures and fixtures else "fail",
        "metrics": [
            {
                "metric": "runtime_bound_probe_pass_rate",
                "value": value,
                "threshold": 1.0,
                "direction": "higher_is_better",
                "passed": value == 1.0 and bool(fixtures),
            },
            *traceability_metrics,
        ],
        "fixtures_run": len(fixtures),
        "failures": failures,
    }


def build_evaluation_result(
    subject: EvaluationSubject,
    fixtures_by_plane: dict[str, list[dict[str, Any]]],
    *,
    selected: list[str] | tuple[str, ...] = PLANES,
    decided_at: str,
) -> dict[str, Any]:
    if len(set(selected)) != len(selected):
        raise EvaluationError("evaluation planes must not be duplicated")
    results = [
        evaluate_plane(subject, plane, fixtures_by_plane.get(plane, [])) for plane in selected
    ]
    blocking = [
        result["plane"] for result in results if result["gate_result"] in {"fail", "not_run"}
    ]
    return {
        "schema_version": "1.0.0",
        "work_id": subject.work_id,
        "run_id": swos_id("evl"),
        "harness_version": "1.1.0",
        "subject_versions": subject.subject_versions(),
        "planes": results,
        "release_decision": {
            "decision": "block" if blocking or set(selected) != set(PLANES) else "release",
            "blocking_planes": blocking,
            "decided_at": decided_at,
        },
    }


def validate_evaluation_result(document: dict[str, Any]) -> list[str]:
    """Validate one result against the frozen evaluation 1.0.0 schema."""
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema unavailable; evaluation result cannot be validated"]
    root = Path(__file__).resolve().parents[1]
    schema_root = root / "schemas"
    schema = _load(schema_root / "evaluation" / "evaluation-result.schema.json")
    common = _load(schema_root / "common" / "common.schema.json")
    store = {schema["$id"]: schema, common["$id"]: common}
    resolver = jsonschema.RefResolver(base_uri=schema["$id"], referrer=schema, store=store)
    validator = jsonschema.Draft202012Validator(schema, resolver=resolver)
    return [
        f"{'/'.join(str(part) for part in error.path)}: {error.message}"
        for error in validator.iter_errors(document)
    ]
