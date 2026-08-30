"""Immutable approval packs and human-authority release verification."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .evaluation import (
    PLANES,
    EvaluationError,
    EvaluationSubject,
    canonical_digest,
    validate_evaluation_result,
)
from .models import swos_id

RELEASE_POLICY = "swos.release-gate"
SECTION_ORDER = (
    "unsupported_claims",
    "counter_evidence",
    "open_review_findings",
    "evaluation",
    "provenance_and_review_assurance",
    "manuscript",
)


class ReleaseApprovalError(RuntimeError):
    """Raised when release evidence is incomplete, mismatched, or unauthorised."""


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseApprovalError(f"cannot load {path.name}: {exc}") from exc


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _actor_id(actor: Any, role: str, *, human: bool = False) -> str:
    if not isinstance(actor, dict) or not str(actor.get("actor_id") or "").strip():
        raise ReleaseApprovalError(f"{role} requires a stable actor_id")
    if human and actor.get("actor_type") != "human":
        raise ReleaseApprovalError(f"{role} must be a human actor")
    return str(actor["actor_id"])


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _evaluation_bindings(subject: EvaluationSubject, evaluation: dict[str, Any]) -> None:
    errors = validate_evaluation_result(evaluation)
    if errors:
        raise ReleaseApprovalError("evaluation schema failed: " + "; ".join(errors))
    planes = evaluation.get("planes", [])
    names = [item.get("plane") for item in planes if isinstance(item, dict)]
    if len(names) != len(set(names)) or set(names) != set(PLANES):
        raise ReleaseApprovalError("evaluation must contain each required plane exactly once")
    if any(item.get("gate_result") != "pass" for item in planes):
        raise ReleaseApprovalError("every evaluation plane must pass")
    if evaluation.get("release_decision", {}).get("decision") != "release":
        raise ReleaseApprovalError("evaluation does not recommend release")
    versions = evaluation.get("subject_versions", {})
    expected = subject.subject_versions()
    for key in ("subject_run_id", "manifest_sha256", "integrity_chain_head"):
        if versions.get(key) != expected.get(key):
            raise ReleaseApprovalError(f"evaluation subject binding mismatch: {key}")
    if evaluation.get("work_id") != subject.work_id:
        raise ReleaseApprovalError("evaluation work_id does not match the runtime subject")


def _open_findings(subject: EvaluationSubject) -> list[dict[str, Any]]:
    return [
        finding
        for review in subject.reviews
        for finding in review.get("findings", [])
        if finding.get("severity") in {"blocker", "major"} and finding.get("status") != "resolved"
    ]


def _pack_section(section_id: str, payload: Any) -> dict[str, Any]:
    return {
        "section_id": section_id,
        "content_sha256": canonical_digest(payload),
        "item_count": len(payload) if isinstance(payload, (list, dict)) else 1,
        "content": payload,
    }


def prepare_approval_pack(
    run_dir: str | Path,
    evaluation_path: str | Path,
    out_dir: str | Path,
    *,
    author: dict[str, Any],
    contract_owner: dict[str, Any],
    evaluation_owner: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    """Prepare risk-first evidence without creating a release approval."""
    if not _valid_timestamp(created_at):
        raise ReleaseApprovalError("approval pack created_at must be an ISO 8601 timestamp")
    subject = EvaluationSubject.load(run_dir)
    evaluation = _load(Path(evaluation_path))
    if not isinstance(evaluation, dict):
        raise ReleaseApprovalError("evaluation result must be an object")
    _evaluation_bindings(subject, evaluation)

    author_id = _actor_id(author, "author")
    contract_owner_id = _actor_id(contract_owner, "contract owner")
    evaluation_owner_id = _actor_id(evaluation_owner, "evaluation owner")
    if contract_owner_id == evaluation_owner_id:
        raise ReleaseApprovalError("contract owner and evaluation owner must differ")
    separation_errors = subject.reviewer_separation_errors()
    if separation_errors:
        raise ReleaseApprovalError("; ".join(separation_errors))
    findings = _open_findings(subject)
    if findings:
        raise ReleaseApprovalError("open blocker or major review findings remain")

    evidence_rejections_path = subject.root / "evidence-rejections.json"
    unsupported = _load(evidence_rejections_path) if evidence_rejections_path.is_file() else []
    counter_evidence = [
        {
            "claim_id": row.get("claim_id"),
            "claim_text": row.get("claim_text"),
            "counter_evidence": row.get("counter_evidence"),
        }
        for row in subject.evidence.get("rows", [])
        if row.get("counter_evidence")
    ]
    manuscript = (subject.root / "article.md").read_text(encoding="utf-8")
    sections = [
        _pack_section("unsupported_claims", unsupported),
        _pack_section("counter_evidence", counter_evidence),
        _pack_section("open_review_findings", findings),
        _pack_section(
            "evaluation",
            {
                "run_id": evaluation.get("run_id"),
                "planes": evaluation.get("planes"),
                "release_decision": evaluation.get("release_decision"),
            },
        ),
        _pack_section(
            "provenance_and_review_assurance",
            {
                "provenance_sha256": canonical_digest(subject.provenance),
                "review_assurance": subject.review_assurance,
                "governed_store_heads": subject.control.get("governed_store_heads"),
            },
        ),
        _pack_section("manuscript", manuscript),
    ]
    bindings = {
        "subject_run_id": subject.run_id,
        "work_id": subject.work_id,
        "run_manifest_sha256": subject.manifest_sha256,
        "integrity_chain_head": subject.integrity_chain_head,
        "evaluation_run_id": evaluation.get("run_id"),
        "evaluation_sha256": canonical_digest(evaluation),
    }
    pack = {
        "pack_version": "swos.approval-pack.v1",
        "pack_id": swos_id("apr"),
        "created_at": created_at,
        "release_status": "awaiting_human_decision",
        "bindings": bindings,
        "roles": {
            "author": author,
            "contract_owner": contract_owner,
            "evaluation_owner": evaluation_owner,
        },
        "section_order": list(SECTION_ORDER),
        "sections": sections,
    }
    if author_id in {contract_owner_id, evaluation_owner_id}:
        pack["role_limitations"] = [
            "Author also occupies an owner role; release approval still requires a distinct human."
        ]
    output = Path(out_dir)
    if any((output / name).exists() for name in ("evaluation-result.json", "approval-pack.json")):
        raise ReleaseApprovalError("approval evidence already exists; use a new release directory")
    output.mkdir(parents=True, exist_ok=True)
    _write(output / "evaluation-result.json", evaluation)
    _write(output / "approval-pack.json", pack)
    return pack


def verify_approval_pack(run_dir: str | Path, release_dir: str | Path) -> list[str]:
    errors: list[str] = []
    try:
        subject = EvaluationSubject.load(run_dir)
        release = Path(release_dir)
        evaluation = _load(release / "evaluation-result.json")
        pack = _load(release / "approval-pack.json")
        _evaluation_bindings(subject, evaluation)
    except (EvaluationError, ReleaseApprovalError) as exc:
        return [str(exc)]
    if pack.get("section_order") != list(SECTION_ORDER):
        errors.append("approval-pack section order is invalid")
    sections = pack.get("sections", [])
    if [section.get("section_id") for section in sections] != list(SECTION_ORDER):
        errors.append("approval-pack sections do not match the required order")
    for section in sections:
        if section.get("content_sha256") != canonical_digest(section.get("content")):
            errors.append(f"approval-pack section digest mismatch: {section.get('section_id')}")
    expected = {
        "subject_run_id": subject.run_id,
        "work_id": subject.work_id,
        "run_manifest_sha256": subject.manifest_sha256,
        "integrity_chain_head": subject.integrity_chain_head,
        "evaluation_run_id": evaluation.get("run_id"),
        "evaluation_sha256": canonical_digest(evaluation),
    }
    if pack.get("bindings") != expected:
        errors.append("approval-pack exact evidence bindings do not verify")
    roles = pack.get("roles", {})
    try:
        _actor_id(roles.get("author"), "author")
        contract_id = _actor_id(roles.get("contract_owner"), "contract owner")
        evaluation_id = _actor_id(roles.get("evaluation_owner"), "evaluation owner")
        if contract_id == evaluation_id:
            errors.append("contract owner and evaluation owner are not separated")
    except ReleaseApprovalError as exc:
        errors.append(str(exc))
    errors.extend(subject.reviewer_separation_errors())
    if _open_findings(subject):
        errors.append("open blocker or major review findings remain")
    return errors


def _validate_sdl(document: dict[str, Any]) -> list[str]:
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema unavailable; release decision cannot be validated"]
    root = Path(__file__).resolve().parents[1] / "schemas"
    schema = _load(root / "decision-ledger" / "sdl.schema.json")
    common = _load(root / "common" / "common.schema.json")
    store = {schema["$id"]: schema, common["$id"]: common}
    resolver = jsonschema.RefResolver(base_uri=schema["$id"], referrer=schema, store=store)
    validator = jsonschema.Draft202012Validator(schema, resolver=resolver)
    return [
        f"{'/'.join(str(part) for part in error.path)}: {error.message}"
        for error in validator.iter_errors(document)
    ]


def record_release_decision(release_dir: str | Path, decision: dict[str, Any]) -> dict[str, Any]:
    """Record a human-supplied decision; never synthesize approval authority."""
    release = Path(release_dir)
    if any(
        (release / name).exists()
        for name in ("release-decision-ledger.json", "release-decision-bindings.json")
    ):
        raise ReleaseApprovalError("release decision already exists and is immutable")
    pack = _load(release / "approval-pack.json")
    evaluation = _load(release / "evaluation-result.json")
    choice = decision.get("decision")
    if choice not in {"approve", "reject"}:
        raise ReleaseApprovalError("decision must be approve or reject")
    approver = decision.get("approver")
    approver_id = _actor_id(approver, "approver", human=True)
    author_id = _actor_id(pack.get("roles", {}).get("author"), "author")
    if approver_id == author_id:
        raise ReleaseApprovalError("author and release approver must differ")
    if not str(decision.get("rationale") or "").strip():
        raise ReleaseApprovalError("release decision requires a rationale")
    if decision.get("policy_basis") != RELEASE_POLICY:
        raise ReleaseApprovalError(f"release decision policy_basis must be {RELEASE_POLICY}")
    if not _valid_timestamp(decision.get("timestamp")):
        raise ReleaseApprovalError("release decision requires an ISO 8601 timestamp")
    alternatives = list(decision.get("alternatives_considered") or [])
    if not {"approve", "reject"}.issubset(set(alternatives)):
        raise ReleaseApprovalError("release decision must consider approve and reject")
    expected_reviewed = {
        **pack.get("bindings", {}),
        "approval_pack_sha256": canonical_digest(pack),
    }
    if decision.get("reviewed_evidence") != expected_reviewed:
        raise ReleaseApprovalError(
            "human decision evidence bindings do not match the approval pack"
        )

    selected = "APPROVE RELEASE" if choice == "approve" else "REJECT RELEASE"
    rejected = "REJECT RELEASE" if choice == "approve" else "APPROVE RELEASE"
    entry = {
        "decision_id": swos_id("dec"),
        "decision_type": "release",
        "question": "Should this exact evaluated SWOS run be released?",
        "options_considered": [
            {"option": selected, "supporting_evidence_refs": [evaluation["run_id"]]},
            {
                "option": rejected,
                "why_rejected": str(decision.get("rationale")),
                "supporting_evidence_refs": [pack["pack_id"]],
            },
        ],
        "selected_option": selected,
        "rationale": str(decision["rationale"]),
        "criteria_applied": [RELEASE_POLICY, "SWOS human approval threshold matrix"],
        "evidence_refs": [evaluation["run_id"], pack["pack_id"]],
        "counter_evidence_refs": [],
        "argument_refs": [],
        "confidence": "high" if choice == "approve" else "medium",
        "uncertainty": [],
        "review_status": "passed" if choice == "approve" else "rejected",
        "responsible_agent": approver,
        "human_approver": approver,
        "policy_basis": RELEASE_POLICY,
        "timestamp": decision["timestamp"],
        "lifecycle_status": "approved" if choice == "approve" else "evaluated",
        "reversibility": "reversible",
    }
    ledger = {
        "schema_version": "1.0.0",
        "work_id": pack["bindings"]["work_id"],
        "append_only": True,
        "entries": [entry],
    }
    errors = _validate_sdl(ledger)
    if errors:
        raise ReleaseApprovalError("release SDL failed: " + "; ".join(errors))
    bindings = {
        "decision": choice,
        "decision_id": entry["decision_id"],
        "approver_id": approver_id,
        "author_id": author_id,
        "reviewed_evidence": expected_reviewed,
        "release_decision_sha256": canonical_digest(ledger),
    }
    _write(release / "release-decision-ledger.json", ledger)
    _write(release / "release-decision-bindings.json", bindings)
    return ledger


def verify_release(run_dir: str | Path, release_dir: str | Path) -> dict[str, Any]:
    """Return a fail-closed release gate decision without modifying evidence."""
    release = Path(release_dir)
    reasons = verify_approval_pack(run_dir, release)
    try:
        pack = _load(release / "approval-pack.json")
        ledger = _load(release / "release-decision-ledger.json")
        bindings = _load(release / "release-decision-bindings.json")
    except ReleaseApprovalError as exc:
        reasons.append(str(exc))
        return {"gate_version": "swos.release-verifier.v1", "decision": "deny", "reasons": reasons}
    reasons.extend(_validate_sdl(ledger))
    entries = ledger.get("entries", [])
    entry = entries[0] if len(entries) == 1 else {}
    if len(entries) != 1:
        reasons.append("release decision ledger must contain exactly one decision")
    if entry.get("selected_option") != "APPROVE RELEASE":
        reasons.append("human decision does not approve release")
    if entry.get("policy_basis") != RELEASE_POLICY:
        reasons.append("release decision policy basis is invalid")
    if not str(entry.get("rationale") or "").strip():
        reasons.append("release decision rationale is missing")
    approver = entry.get("human_approver")
    try:
        approver_id = _actor_id(approver, "approver", human=True)
        author_id = _actor_id(pack.get("roles", {}).get("author"), "author")
        if approver_id == author_id:
            reasons.append("author and release approver are not separated")
    except ReleaseApprovalError as exc:
        reasons.append(str(exc))
    expected_reviewed = {
        **pack.get("bindings", {}),
        "approval_pack_sha256": canonical_digest(pack),
    }
    if bindings.get("reviewed_evidence") != expected_reviewed:
        reasons.append("release decision exact evidence bindings do not verify")
    if bindings.get("release_decision_sha256") != canonical_digest(ledger):
        reasons.append("release decision digest does not verify")
    if bindings.get("decision_id") != entry.get("decision_id"):
        reasons.append("release decision identity binding does not verify")
    if bindings.get("approver_id") != (approver or {}).get("actor_id"):
        reasons.append("release approver identity binding does not verify")
    if bindings.get("author_id") != pack.get("roles", {}).get("author", {}).get("actor_id"):
        reasons.append("release author identity binding does not verify")
    expected_choice = "approve" if entry.get("selected_option") == "APPROVE RELEASE" else "reject"
    if bindings.get("decision") != expected_choice:
        reasons.append("release decision choice binding does not verify")
    return {
        "gate_version": "swos.release-verifier.v1",
        "decision": "deny" if reasons else "allow",
        "subject_run_id": pack.get("bindings", {}).get("subject_run_id"),
        "reasons": reasons,
    }
