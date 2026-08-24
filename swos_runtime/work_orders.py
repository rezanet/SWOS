"""Persistent SWOS work-order protocol for live host execution.

SWOS owns stage ordering, canonical instructions, contract validation and state
transitions. A host or adapter fulfils one bounded capability at a time. The
host never chooses the next scholarly stage and never owns the release decision.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .capabilities import CAPABILITY_CONTRACT_SET, CAPABILITY_CONTRACTS
from .instructions import INSTRUCTION_SET, instruction_record

PROTOCOL_VERSION = "swos.work-orders.v1"
MAX_REVIEW_ITERATIONS = 3
BASE_STAGE_SEQUENCE = [
    "research_planning",
    "source_retrieval",
    "semantic_rerank",
    "evidence_extraction",
    "citation_support_audit",
    "argument_construction",
    "draft_generation",
    "prose_transformation",
    "semantic_verification",
    "hostile_review",
]
JUDGEMENT_TYPES = {
    "semantic_rerank": "relevance_ranking",
    "citation_support_audit": "citation_support",
    "argument_construction": "argument_proposal",
    "semantic_verification": "semantic_preservation",
    "hostile_review": "scholarly_review",
}


class WorkOrderError(RuntimeError):
    """Raised for invalid work-order transitions or submissions."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_adapter_manifest(path: str | Path) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise WorkOrderError("adapter capability manifest must be a JSON object")
    if payload.get("contract_set") != CAPABILITY_CONTRACT_SET:
        raise WorkOrderError(
            f"adapter manifest must declare contract_set={CAPABILITY_CONTRACT_SET!r}"
        )
    if not isinstance(payload.get("capabilities"), dict):
        raise WorkOrderError("adapter manifest must contain a capabilities object")
    return payload


def _require_capability(adapter: dict[str, Any], capability: str) -> dict[str, Any]:
    declaration = adapter.get("capabilities", {}).get(capability)
    if not isinstance(declaration, dict):
        raise WorkOrderError(
            f"adapter {adapter.get('adapter', '?')!r} does not declare {capability!r}"
        )
    if declaration.get("level") not in {"full", "native"}:
        raise WorkOrderError(
            f"adapter {adapter.get('adapter', '?')!r} declares {capability!r} as "
            f"{declaration.get('level')!r}; autonomous execution requires full/native"
        )
    expected = CAPABILITY_CONTRACTS[capability]
    if declaration.get("contract") != expected:
        raise WorkOrderError(
            f"adapter {adapter.get('adapter', '?')!r} declares wrong contract for "
            f"{capability!r}: expected {expected!r}"
        )
    return declaration


def _validate_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise WorkOrderError("request must be a JSON object")
    topic = payload.get("topic")
    if not isinstance(topic, str) or not topic.strip():
        raise WorkOrderError("request.topic must be non-empty text")
    result = dict(payload)
    result.setdefault("length", 2500)
    result.setdefault("audience", "intelligent general reader")
    result.setdefault("style", "scholarly-natural")
    result.setdefault("depth", "rigorous")
    return result


def _blocking_findings(review: Any) -> list[dict[str, Any]]:
    if not isinstance(review, dict):
        return []
    findings: list[dict[str, Any]] = []
    for panel in review.get("reviews", []):
        if not isinstance(panel, dict):
            continue
        for finding in panel.get("findings", []):
            if isinstance(finding, dict) and finding.get("severity") in {"blocker", "major"}:
                findings.append(finding)
    return findings


def _review_assurance(declaration: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_mode": str(declaration.get("review_mode") or "unspecified"),
        "independence": str(declaration.get("independence") or "unknown"),
        "blind_review_supported": bool(declaration.get("blind_review_supported", False)),
        "independence_limitations": list(declaration.get("independence_limitations") or []),
    }


class WorkOrderRun:
    """A persistent SWOS-controlled live execution run."""

    def __init__(self, run_dir: str | Path) -> None:
        self.run_dir = Path(run_dir)
        self.state_path = self.run_dir / "run-state.json"
        if not self.state_path.is_file():
            raise WorkOrderError(f"not a SWOS work-order run: {self.run_dir}")
        self.state = _read_json(self.state_path)

    @classmethod
    def start(
        cls,
        *,
        request: dict[str, Any],
        adapter_manifest: dict[str, Any],
        root: str | Path,
    ) -> "WorkOrderRun":
        request = _validate_request(request)
        for capability in [*BASE_STAGE_SEQUENCE, "revision"]:
            _require_capability(adapter_manifest, capability)
        run_id = f"host-{uuid.uuid4()}"
        run_dir = Path(root) / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        state = {
            "protocol_version": PROTOCOL_VERSION,
            "instruction_set": INSTRUCTION_SET,
            "run_id": run_id,
            "status": "ACTIVE",
            "request": request,
            "adapter": adapter_manifest,
            "stage": "research_planning",
            "review_iteration": 0,
            "revision_count": 0,
            "submissions": [],
            "history": [],
        }
        _write_json(run_dir / "request.json", request)
        _write_json(run_dir / "adapter-capabilities.json", adapter_manifest)
        _write_json(run_dir / "run-state.json", state)
        run = cls(run_dir)
        run._persist_work_order()
        return run

    @classmethod
    def start_from_files(
        cls,
        *,
        request_path: str | Path,
        adapter_path: str | Path,
        root: str | Path,
    ) -> "WorkOrderRun":
        return cls.start(
            request=_read_json(request_path),
            adapter_manifest=_load_adapter_manifest(adapter_path),
            root=root,
        )

    def _save(self) -> None:
        _write_json(self.state_path, self.state)

    def _latest(self, stage: str) -> Any:
        for item in reversed(self.state.get("submissions", [])):
            if item.get("stage") == stage:
                return _read_json(self.run_dir / item["file"])
        return None

    def _all(self, stage: str) -> list[Any]:
        return [
            _read_json(self.run_dir / item["file"])
            for item in self.state.get("submissions", [])
            if item.get("stage") == stage
        ]

    def _latest_revision_or_draft(self) -> str | None:
        for stage in ("revision", "draft_generation"):
            payload = self._latest(stage)
            if isinstance(payload, dict):
                text = payload.get("article") or payload.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
        return None

    def _work_inputs(self, stage: str) -> dict[str, Any]:
        request = self.state["request"]
        latest = self._latest
        if stage == "research_planning":
            return {"request": request}
        if stage == "source_retrieval":
            plan = latest("research_planning") or {}
            return {
                "topic": request["topic"],
                "queries": plan.get("queries", []),
                "research_plan": plan,
            }
        if stage == "semantic_rerank":
            return {"query": request["topic"], "sources": latest("source_retrieval") or {}}
        if stage == "evidence_extraction":
            return {
                "topic": request["topic"],
                "sources": latest("source_retrieval") or {},
                "rerank": latest("semantic_rerank") or {},
            }
        if stage == "citation_support_audit":
            return {
                "candidates": latest("evidence_extraction") or {},
                "sources": latest("source_retrieval") or {},
            }
        if stage == "argument_construction":
            return {
                "topic": request["topic"],
                "research_plan": latest("research_planning") or {},
                "evidence_candidates": latest("evidence_extraction") or {},
                "citation_audit": latest("citation_support_audit") or {},
            }
        if stage == "draft_generation":
            return {
                "request": request,
                "research_plan": latest("research_planning") or {},
                "evidence_candidates": latest("evidence_extraction") or {},
                "citation_audit": latest("citation_support_audit") or {},
                "argument": latest("argument_construction") or {},
            }
        if stage == "revision":
            return {
                "article": self._latest_revision_or_draft(),
                "review": latest("hostile_review") or {},
                "evidence_candidates": latest("evidence_extraction") or {},
                "citation_audit": latest("citation_support_audit") or {},
                "argument": latest("argument_construction") or {},
            }
        if stage == "prose_transformation":
            return {
                "article": self._latest_revision_or_draft(),
                "mode": "polish",
                "preset": request.get("style", "scholarly-natural"),
            }
        if stage == "semantic_verification":
            transform = latest("prose_transformation") or {}
            return {
                "source": self._latest_revision_or_draft(),
                "candidate": transform.get("candidate") or transform.get("final_text"),
                "assurance": "strict",
            }
        if stage == "hostile_review":
            verification = latest("semantic_verification") or {}
            transform = latest("prose_transformation") or {}
            source = self._latest_revision_or_draft()
            article = transform.get("candidate") if verification.get("status") == "PASS" else source
            return {
                "iteration": self.state.get("review_iteration", 0) + 1,
                "article": article,
                "evidence_candidates": latest("evidence_extraction") or {},
                "citation_audit": latest("citation_support_audit") or {},
                "argument": latest("argument_construction") or {},
                "sources": latest("source_retrieval") or {},
            }
        raise WorkOrderError(f"unsupported work-order stage: {stage}")

    def work_order(self) -> dict[str, Any] | None:
        if self.state.get("status") != "ACTIVE":
            return None
        stage = self.state["stage"]
        declaration = _require_capability(self.state["adapter"], stage)
        instruction = instruction_record(stage)
        return {
            "protocol_version": PROTOCOL_VERSION,
            "run_id": self.state["run_id"],
            "next_stage": stage,
            "capability": stage,
            "contract": CAPABILITY_CONTRACTS[stage],
            "canonical_instruction": instruction,
            "adapter": self.state["adapter"].get("adapter"),
            "execution_mode": self.state["adapter"].get("execution_mode"),
            "assurance_declaration": declaration,
            "inputs": self._work_inputs(stage),
            "submission_contract": {
                "format": "json",
                "must_include": ["provenance"],
                "provenance_must_include": [
                    "adapter",
                    "model_host",
                    "model",
                    "execution_mode",
                ],
                "swos_stamps": [
                    "capability",
                    "contract",
                    "contract_passed",
                    "instruction_id",
                    "instruction_sha256",
                    "judgement_evidence_when_applicable",
                ],
            },
        }

    def _persist_work_order(self) -> None:
        order = self.work_order()
        path = self.run_dir / "next-work.json"
        if order is None:
            if path.exists():
                path.unlink()
            return
        _write_json(path, order)

    def _validate_provenance(self, stage: str, result: dict[str, Any]) -> dict[str, Any]:
        provenance = result.get("provenance")
        if not isinstance(provenance, dict):
            raise WorkOrderError("submission must include provenance object")
        for key in ("adapter", "model_host", "model", "execution_mode"):
            if key not in provenance:
                raise WorkOrderError(f"submission provenance missing {key!r}")
        adapter = self.state["adapter"]
        if provenance.get("adapter") != adapter.get("adapter"):
            raise WorkOrderError("submission adapter does not match run adapter")
        if provenance.get("execution_mode") != adapter.get("execution_mode"):
            raise WorkOrderError("submission execution_mode does not match run adapter")
        instruction = instruction_record(stage)
        normalized = dict(provenance)
        normalized["instruction_set"] = instruction["instruction_set"]
        normalized["instruction_id"] = instruction["instruction_id"]
        normalized["instruction_sha256"] = instruction["sha256"]
        normalized["capability"] = stage
        normalized["contract"] = CAPABILITY_CONTRACTS[stage]
        return normalized

    def _judgement_evidence(
        self,
        stage: str,
        result: dict[str, Any],
        provenance: dict[str, Any],
    ) -> dict[str, Any] | None:
        judgement_type = JUDGEMENT_TYPES.get(stage)
        if not judgement_type:
            return None
        declaration = _require_capability(self.state["adapter"], stage)
        review = _review_assurance(declaration)
        return {
            "judgement_type": judgement_type,
            "capability": stage,
            "contract": CAPABILITY_CONTRACTS[stage],
            "adapter": provenance["adapter"],
            "host": provenance["model_host"],
            "model": provenance["model"],
            "confidence": str(result.get("confidence") or "unreported"),
            "assurance": list(declaration.get("assurance") or []),
            "review_mode": review["review_mode"],
            "independence": review["independence"],
            "blind_review_supported": review["blind_review_supported"],
            "independence_limitations": review["independence_limitations"],
            "instruction_id": provenance["instruction_id"],
            "instruction_sha256": provenance["instruction_sha256"],
            "authority": "advisory_evidence_for_swos_governance",
        }

    def _validate_stage_result(self, stage: str, result: Any) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise WorkOrderError("stage submission must be a JSON object")
        normalized = dict(result)
        provenance = self._validate_provenance(stage, normalized)
        contract = normalized.get("contract")
        if contract not in {None, CAPABILITY_CONTRACTS[stage]}:
            raise WorkOrderError(f"submission contract mismatch for {stage}: {contract!r}")
        normalized["capability"] = stage
        normalized["contract"] = CAPABILITY_CONTRACTS[stage]
        normalized["contract_passed"] = True
        normalized["provenance"] = provenance
        judgement = self._judgement_evidence(stage, normalized, provenance)
        if judgement is not None:
            normalized["judgement_evidence"] = judgement

        if stage == "research_planning":
            required = ("research_question", "scope", "queries", "rival_theses")
            for key in required:
                if key not in normalized:
                    raise WorkOrderError(f"research plan missing {key!r}")
            if not isinstance(normalized.get("queries"), list) or len(normalized["queries"]) < 3:
                raise WorkOrderError("research plan requires at least three queries")
        elif stage == "source_retrieval":
            sources = normalized.get("sources")
            if not isinstance(sources, list) or not sources:
                raise WorkOrderError("source retrieval must return a non-empty sources array")
        elif stage == "semantic_rerank":
            if not isinstance(normalized.get("scores"), list):
                raise WorkOrderError("semantic rerank must return scores array")
        elif stage == "evidence_extraction":
            claims = normalized.get("claims")
            if not isinstance(claims, list) or not claims:
                raise WorkOrderError("evidence extraction must return claims array")
            for claim in claims:
                if (
                    not isinstance(claim, dict)
                    or not claim.get("exact_quote")
                    or not claim.get("source_id")
                ):
                    raise WorkOrderError("every evidence claim requires source_id and exact_quote")
        elif stage == "citation_support_audit":
            if not isinstance(normalized.get("audits"), list):
                raise WorkOrderError("citation support audit must return audits array")
        elif stage == "argument_construction":
            if not isinstance(normalized.get("nodes"), list) or not normalized.get("nodes"):
                raise WorkOrderError("argument construction must return non-empty nodes")
        elif stage in {"draft_generation", "revision"}:
            article = normalized.get("article") or normalized.get("text")
            if not isinstance(article, str) or not article.strip():
                raise WorkOrderError(f"{stage} must return non-empty article text")
        elif stage == "prose_transformation":
            candidate = normalized.get("candidate") or normalized.get("final_text")
            if not isinstance(candidate, str) or not candidate.strip():
                raise WorkOrderError("prose transformation must return candidate text")
        elif stage == "semantic_verification":
            if normalized.get("status") not in {"PASS", "REVIEW", "REJECT"}:
                raise WorkOrderError("semantic verification status must be PASS, REVIEW or REJECT")
        elif stage == "hostile_review" and not isinstance(normalized.get("reviews"), list):
            raise WorkOrderError("hostile review must return reviews array")
        return normalized

    def _advance(self, stage: str, result: dict[str, Any]) -> None:
        if stage == "hostile_review":
            self.state["review_iteration"] = self.state.get("review_iteration", 0) + 1
            blockers = _blocking_findings(result)
            if blockers:
                if self.state["review_iteration"] >= MAX_REVIEW_ITERATIONS:
                    self.state["status"] = "REVIEW_REQUIRED"
                    self.state["blocking_findings"] = blockers
                    self.state["stage"] = None
                    return
                self.state["stage"] = "revision"
                return
            self.state["status"] = "READY_TO_FINALISE"
            self.state["stage"] = None
            return
        if stage == "revision":
            self.state["revision_count"] = self.state.get("revision_count", 0) + 1
            self.state["stage"] = "prose_transformation"
            return
        index = BASE_STAGE_SEQUENCE.index(stage)
        self.state["stage"] = BASE_STAGE_SEQUENCE[index + 1]

    def submit(self, result: dict[str, Any]) -> dict[str, Any]:
        if self.state.get("status") != "ACTIVE":
            raise WorkOrderError(f"run is not ACTIVE: {self.state.get('status')}")
        stage = self.state["stage"]
        validated = self._validate_stage_result(stage, result)
        count = len(self.state.get("submissions", [])) + 1
        filename = f"{count:02d}-{stage}.json"
        relative = f"submissions/{filename}"
        _write_json(self.run_dir / relative, validated)
        self.state.setdefault("submissions", []).append({"stage": stage, "file": relative})
        self.state.setdefault("history", []).append(
            {
                "event": "stage_accepted",
                "stage": stage,
                "capability": stage,
                "contract": CAPABILITY_CONTRACTS[stage],
                "contract_passed": True,
                "instruction_id": validated["provenance"]["instruction_id"],
                "instruction_sha256": validated["provenance"]["instruction_sha256"],
                "submission": relative,
            }
        )
        self._advance(stage, validated)
        self._save()
        self._persist_work_order()
        return self.status()

    def status(self) -> dict[str, Any]:
        return {
            "protocol_version": PROTOCOL_VERSION,
            "instruction_set": self.state.get("instruction_set", INSTRUCTION_SET),
            "run_id": self.state["run_id"],
            "status": self.state["status"],
            "next_stage": self.state.get("stage"),
            "review_iteration": self.state.get("review_iteration", 0),
            "revision_count": self.state.get("revision_count", 0),
            "submissions": len(self.state.get("submissions", [])),
            "run_dir": str(self.run_dir),
        }

    def judgement_evidence(self) -> list[dict[str, Any]]:
        records = []
        for item in self.state.get("submissions", []):
            payload = _read_json(self.run_dir / item["file"])
            judgement = payload.get("judgement_evidence") if isinstance(payload, dict) else None
            if isinstance(judgement, dict):
                records.append(judgement)
        return records

    def export_host_bundle(self, output_path: str | Path | None = None) -> Path:
        """Generate canonical replay/interchange/debug/reproducibility evidence."""
        if self.state.get("status") not in {"READY_TO_FINALISE", "REVIEW_REQUIRED"}:
            raise WorkOrderError("host bundle can be exported only after review completion")
        adapter = self.state["adapter"]
        retrieval = self._latest("source_retrieval") or {}
        verification = self._latest("semantic_verification") or {}
        transform = self._latest("prose_transformation") or {}
        source_text = self._latest_revision_or_draft()
        candidate = transform.get("candidate") or transform.get("final_text")
        safe = verification.get("status") == "PASS"
        final_text = candidate if safe and isinstance(candidate, str) else source_text
        draft = self._latest("draft_generation") or {}
        revisions = [
            payload.get("article") or payload.get("text")
            for payload in self._all("revision")
            if isinstance(payload, dict)
        ]
        review_decl = _require_capability(adapter, "hostile_review")
        review = _review_assurance(review_decl)
        bundle = {
            "bundle_role": "replay_interchange_debug_reproducibility",
            "host": {
                "adapter": adapter.get("adapter"),
                "model_host": adapter.get("model_host"),
                "model": (transform.get("provenance") or {}).get(
                    "model", adapter.get("model_host")
                ),
                "execution_mode": adapter.get("execution_mode"),
                "api_key_used": bool(adapter.get("api_key_used", False)),
                "paid_api_calls": int(adapter.get("paid_api_calls", 0)),
                "review_mode": review["review_mode"],
                "independence": review["independence"],
                "independence_limitations": review["independence_limitations"],
                "blind_review_supported": review["blind_review_supported"],
                "capability_contract_set": CAPABILITY_CONTRACT_SET,
                "instruction_set": INSTRUCTION_SET,
            },
            "sources": retrieval.get("sources", []),
            "stages": {
                "research_plan": self._latest("research_planning") or {},
                "rerank_scores": (self._latest("semantic_rerank") or {}).get("scores", []),
                "evidence_build": self._latest("evidence_extraction") or {},
                "evidence_audit": self._latest("citation_support_audit") or {},
                "argument_build": self._latest("argument_construction") or {},
                "draft": draft.get("article") or draft.get("text"),
                "reviews": self._all("hostile_review"),
                "revisions": [item for item in revisions if isinstance(item, str)],
                "semantic_verification": verification,
            },
            "prose": {
                "adapter_mode": "host_native_swos_prose_contract",
                "safe_for_automatic_use": safe,
                "final_text": final_text,
                "semantic_verification": verification,
            },
            "judgement_evidence": self.judgement_evidence(),
            "work_order_run": {
                "protocol_version": PROTOCOL_VERSION,
                "instruction_set": INSTRUCTION_SET,
                "run_id": self.state["run_id"],
                "review_iteration": self.state.get("review_iteration", 0),
                "revision_count": self.state.get("revision_count", 0),
            },
        }
        path = Path(output_path) if output_path else self.run_dir / "host-bundle.json"
        _write_json(path, bundle)
        return path
