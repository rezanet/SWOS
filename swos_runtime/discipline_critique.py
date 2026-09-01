"""Structured, pack-bound discipline critique.

The critic emits machine proposals.  It never promotes them to human review
and it keeps each discipline's criteria separate during aggregation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .discipline_ontology import DisciplineOntologyRegistry, DisciplineProfile
from .models import canonical_digest, stable_identifier, utc_timestamp


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def _truthy(value: Any) -> bool:
    if isinstance(value, Mapping):
        return bool(value.get("supported", value.get("pass", value.get("valid", False))))
    return bool(value) and str(value).lower() not in {"fail", "false", "blocked", "missing"}


@dataclass(frozen=True)
class CritiqueFinding:
    finding_id: str
    discipline: str
    pack_id: str
    pack_version: str
    ontology_version: str
    ontology_digest: str
    criterion_iri: str
    failure_mode_iri: str
    finding_type: str
    severity: str
    claim_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    observations: tuple[str, ...] = ()
    reasoning: str = ""
    counter_position: str = ""
    limitation: str = ""
    remediation: str = ""
    confidence: float = 0.0
    review_state: str = "machine_proposed"
    reviewer_refs: tuple[str, ...] = ()
    epg_refs: tuple[str, ...] = ()
    sdl_refs: tuple[str, ...] = ()
    created_at: str = field(default_factory=utc_timestamp)

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "discipline": self.discipline,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "ontology_version": self.ontology_version,
            "ontology_digest": self.ontology_digest,
            "criterion_iri": self.criterion_iri,
            "failure_mode_iri": self.failure_mode_iri,
            "finding_type": self.finding_type,
            "severity": self.severity,
            "claim_refs": list(self.claim_refs),
            "evidence_refs": list(self.evidence_refs),
            "observations": list(self.observations),
            "reasoning": self.reasoning,
            "counter_position": self.counter_position,
            "limitation": self.limitation,
            "remediation": self.remediation,
            "confidence": self.confidence,
            "review_state": self.review_state,
            "reviewer_refs": list(self.reviewer_refs),
            "epg_refs": list(self.epg_refs),
            "sdl_refs": list(self.sdl_refs),
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class CriterionResult:
    criterion_iri: str
    label: str
    mandatory: bool
    weight: float
    status: str
    finding_state: str
    claim_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    finding_ids: list[str] = field(default_factory=list)
    proof_standard_iris: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion_iri": self.criterion_iri,
            "label": self.label,
            "mandatory": self.mandatory,
            "weight": self.weight,
            "status": self.status,
            "finding_state": self.finding_state,
            "claim_refs": list(self.claim_refs),
            "evidence_refs": list(self.evidence_refs),
            "finding_ids": list(self.finding_ids),
            "proof_standard_iris": list(self.proof_standard_iris),
        }


@dataclass(frozen=True)
class DisciplineCritiqueReport:
    report_id: str
    discipline: str
    pack_id: str
    pack_version: str
    ontology_version: str
    ontology_digest: str
    subject_digest: str
    evidence_digest: str
    criteria: tuple[CriterionResult, ...]
    findings: tuple[CritiqueFinding, ...]
    mandatory_failures: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    review_state: str = "machine_proposed"
    created_at: str = field(default_factory=utc_timestamp)

    @property
    def blocking(self) -> bool:
        return bool(self.mandatory_failures)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "discipline": self.discipline,
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "ontology_version": self.ontology_version,
            "ontology_digest": self.ontology_digest,
            "subject_digest": self.subject_digest,
            "evidence_digest": self.evidence_digest,
            "criteria": [item.to_dict() for item in self.criteria],
            "findings": [item.to_dict() for item in self.findings],
            "mandatory_failures": list(self.mandatory_failures),
            "limitations": list(self.limitations),
            "review_state": self.review_state,
            "created_at": self.created_at,
            "blocking": self.blocking,
        }


@dataclass(frozen=True)
class AggregatedCritiqueReport:
    report_id: str
    sections: tuple[DisciplineCritiqueReport, ...]
    disagreements: list[dict[str, Any]]
    mandatory_failures: list[dict[str, Any]]
    limitations: tuple[str, ...]
    display_summary: Mapping[str, Any]
    created_at: str = field(default_factory=utc_timestamp)

    @property
    def blocking(self) -> bool:
        return bool(self.mandatory_failures)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "sections": [section.to_dict() for section in self.sections],
            "disagreements": [dict(item) for item in self.disagreements],
            "mandatory_failures": [dict(item) for item in self.mandatory_failures],
            "limitations": list(self.limitations),
            "display_summary": dict(self.display_summary),
            "blocking": self.blocking,
            "created_at": self.created_at,
        }


def _criterion_inputs(
    criterion_iri: str,
    evidence_matrix: Mapping[str, Any],
    research_plan: Mapping[str, Any],
    draft: Mapping[str, Any],
) -> tuple[list[str], list[str], str | None]:
    claims = [str(item.get("claim_id") or item.get("id")) for item in draft.get("claims", []) if isinstance(item, Mapping)]
    evidence: list[str] = []
    status: str | None = None
    for row in evidence_matrix.get("rows", evidence_matrix.get("evidence", [])):
        if not isinstance(row, Mapping) or str(row.get("criterion_iri") or "") != criterion_iri:
            continue
        evidence.extend(str(value) for value in _as_list(row.get("evidence_refs") or row.get("epg_refs")))
        claims.extend(str(value) for value in _as_list(row.get("claim_refs") or row.get("claim_ids")))
        if row.get("status") is not None:
            status = str(row["status"])
    for container in (research_plan, draft):
        criteria = container.get("criteria", {})
        if isinstance(criteria, Mapping) and criterion_iri in criteria:
            value = criteria[criterion_iri]
            if isinstance(value, Mapping):
                evidence.extend(str(item) for item in _as_list(value.get("evidence_refs") or value.get("epg_refs")))
                claims.extend(str(item) for item in _as_list(value.get("claim_refs") or value.get("claim_ids")))
                if value.get("status") is not None:
                    status = str(value["status"])
                if _truthy(value) and not evidence:
                    evidence.append(f"criterion:{criterion_iri}")
            elif _truthy(value):
                evidence.append(f"criterion:{criterion_iri}")
            else:
                status = "fail"
    return list(dict.fromkeys(claims)), list(dict.fromkeys(evidence)), status


class DisciplineCritic:
    """Apply pack criteria while preserving evidence and review boundaries."""

    def __init__(self, registry: DisciplineOntologyRegistry | None = None) -> None:
        self.registry = registry

    def critique(
        self,
        *,
        discipline: DisciplineProfile | str,
        research_plan: Mapping[str, Any],
        evidence_matrix: Mapping[str, Any],
        draft: Mapping[str, Any],
    ) -> DisciplineCritiqueReport:
        if isinstance(discipline, str):
            if self.registry is None:
                raise ValueError("a registry is required to resolve a discipline")
            profile = self.registry.profile(discipline)
        else:
            profile = discipline
        criteria: list[CriterionResult] = []
        findings: list[CritiqueFinding] = []
        mandatory_failures: list[str] = []
        limitations: list[str] = []
        claims_in_draft = tuple(
            str(item.get("claim_id") or item.get("id"))
            for item in draft.get("claims", [])
            if isinstance(item, Mapping)
        ) or ("draft",)
        plan_methods = {str(value).lower() for value in _as_list(research_plan.get("methods"))}
        draft_text = jsonish_text(draft).lower()
        for raw in profile.required_criteria:
            criterion = dict(raw)
            criterion_iri = str(criterion.get("iri") or "")
            label = str(criterion.get("label") or criterion_iri.rsplit("/", 1)[-1])
            claim_refs, evidence_refs, explicit_status = _criterion_inputs(
                criterion_iri, evidence_matrix, research_plan, draft
            )
            if not claim_refs:
                claim_refs = list(claims_in_draft)
            special_failure = False
            reasoning = ""
            limitation = ""
            finding_type = "required_move"
            failure_mode = profile.failure_modes[0]["iri"] if profile.failure_modes else ""
            if criterion.get("requires_design") and str(research_plan.get("claim_type", "")).lower() == "causal":
                design_methods = {"randomized", "randomized_controlled", "quasi_experimental", "experiment", "causal_inference"}
                if not plan_methods.intersection(design_methods):
                    special_failure = True
                    finding_type = "missing_warrant"
                    reasoning = "A causal claim lacks an adequate causal design warrant; a correlational or observational design cannot license causal language."
                    limitation = "Limit the conclusion to association until a design capable of identifying the causal effect is supplied."
                    limitations.append(limitation)
            if explicit_status in {"fail", "blocked", "missing", "false"}:
                special_failure = True
            elif explicit_status in {"pass", "supported", "valid", "true"}:
                supported = True
            else:
                supported = bool(evidence_refs) or bool(re.search(re.escape(label.split()[0]), draft_text))
            failed = special_failure or not supported
            if failed:
                status = "fail"
                if bool(criterion.get("mandatory", True)):
                    mandatory_failures.append(criterion_iri)
                finding_id = stable_identifier(
                    "critique-finding",
                    {"discipline": profile.discipline, "criterion": criterion_iri, "claims": claim_refs},
                )
                finding = CritiqueFinding(
                    finding_id=finding_id,
                    discipline=profile.discipline,
                    pack_id=profile.pack_id,
                    pack_version=profile.pack_version,
                    ontology_version="2.0.0",
                    ontology_digest=profile.ontology_digest,
                    criterion_iri=criterion_iri,
                    failure_mode_iri=failure_mode,
                    finding_type=finding_type,
                    severity="blocking" if criterion.get("mandatory", True) else "major",
                    claim_refs=tuple(claim_refs),
                    evidence_refs=tuple(evidence_refs),
                    observations=(f"Required move missing: {label}.",),
                    reasoning=reasoning or f"The pack requires {label}; no linked evidence or accepted criterion result was supplied.",
                    limitation=limitation,
                    remediation=f"Supply an evidence-linked treatment of the {label} criterion and request human review.",
                    confidence=0.95 if criterion.get("mandatory", True) else 0.75,
                    review_state="machine_proposed",
                    epg_refs=tuple(evidence_refs),
                )
                findings.append(finding)
                finding_ids = (finding_id,)
                state = "blocking" if criterion.get("mandatory", True) else "machine_proposed"
            else:
                status = "pass"
                finding_ids = ()
                state = "machine_proposed"
            criteria.append(
                CriterionResult(
                    criterion_iri=criterion_iri,
                    label=label,
                    mandatory=bool(criterion.get("mandatory", True)),
                    weight=float(criterion.get("weight", 0.0)),
                    status=status,
                    finding_state=state,
                    claim_refs=list(claim_refs),
                    evidence_refs=list(evidence_refs),
                    finding_ids=list(finding_ids),
                    proof_standard_iris=[str(item.get("iri")) for item in profile.proof_standards],
                )
            )
        subject_digest = canonical_digest({"plan": research_plan, "draft": draft})
        evidence_digest = canonical_digest(evidence_matrix)
        report_id = stable_identifier("discipline-critique", {"subject": subject_digest, "evidence": evidence_digest, "discipline": profile.discipline})
        return DisciplineCritiqueReport(
            report_id=report_id,
            discipline=profile.discipline,
            pack_id=profile.pack_id,
            pack_version=profile.pack_version,
            ontology_version="2.0.0",
            ontology_digest=profile.ontology_digest,
            subject_digest=subject_digest,
            evidence_digest=evidence_digest,
            criteria=tuple(criteria),
            findings=tuple(findings),
            mandatory_failures=tuple(dict.fromkeys(mandatory_failures)),
            limitations=tuple(dict.fromkeys(limitations)),
        )


def aggregate_critiques(reports: Iterable[DisciplineCritiqueReport]) -> AggregatedCritiqueReport:
    sections = tuple(reports)
    disagreements: list[dict[str, Any]] = []
    by_criterion: dict[str, list[tuple[str, str]]] = {}
    for section in sections:
        for criterion in section.criteria:
            by_criterion.setdefault(criterion.criterion_iri, []).append((section.discipline, criterion.status))
    for criterion_iri, values in by_criterion.items():
        if len({status for _, status in values}) > 1:
            disagreements.append({"criterion_iri": criterion_iri, "results": [{"discipline": d, "status": s} for d, s in values], "resolution": "unresolved"})
    failures = tuple(
        {"discipline": section.discipline, "criterion_iri": criterion}
        for section in sections
        for criterion in section.mandatory_failures
    )
    summary = {
        section.discipline: {
            "criteria": len(section.criteria),
            "passed": sum(item.status == "pass" for item in section.criteria),
            "failed": sum(item.status == "fail" for item in section.criteria),
            "blocking": section.blocking,
        }
        for section in sections
    }
    report_id = stable_identifier("discipline-critique-aggregate", [section.report_id for section in sections])
    return AggregatedCritiqueReport(
        report_id=report_id,
        sections=sections,
        disagreements=disagreements,
        mandatory_failures=list(failures),
        limitations=tuple(dict.fromkeys(limit for section in sections for limit in section.limitations)),
        display_summary=summary,
    )


def jsonish_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(f"{jsonish_text(key)} {jsonish_text(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return " ".join(jsonish_text(item) for item in value)
    return str(value)
