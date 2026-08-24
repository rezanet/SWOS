"""Persistent host-native work-order protocol for subscription execution.

SWOS owns stage ordering and validation. A host such as Codex or Claude fulfils
one bounded capability work order at a time and submits the result. The host
never chooses the next scholarly stage.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .capabilities import CAPABILITY_CONTRACTS, CAPABILITY_CONTRACT_SET

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


class WorkOrderError(RuntimeError):
    """Raised for invalid host-native work-order transitions or submissions."""


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


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
            if (
                isinstance(finding, dict)
                and finding.get("severity") in {"blocker", "major"}
            ):
                findings.append(finding)
    return findings


class WorkOrderRun:
    """A persistent SWOS-controlled host-native run."""

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
            return {
                "query": request["topic"],
                "sources": latest("source_retrieval") or {},
            }
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
                "instruction": (
                    "Judge support only; uncertainty must not become directly_supports."
                ),
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
                "instruction": "Change language only; preserve meaning and source markers.",
            }
        if stage == "semantic_verification":
            transform = latest("prose_transformation") or {}
            return {
                "source": self._latest_revision_or_draft(),
                "candidate": transform.get("candidate") or transform.get("final_text"),
                "assurance": "strict",
                "instruction": (
                    "Return PASS only when the candidate preserves meaning and protected facts."
                ),
            }
        if stage == "hostile_review":
            verification = latest("semantic_verification") or {}
            transform = latest("prose_transformation") or {}
            source = self._latest_revision_or_draft()
            article = (
                transform.get("candidate")
                if verification.get("status") == "PASS"
                else source
            )
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
        return {
            "protocol_version": PROTOCOL_VERSION,
            "run_id": self.state["run_id"],
            "next_stage": stage,
            "capability": stage,
            "contract": CAPABILITY_CONTRACTS[stage],
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

    def _validate_provenance(self, result: dict[str, Any]) -> None:
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

    def _validate_stage_result(self, stage: str, result: Any) -> dict[str, Any]:
        if not isinstance(result, dict):
            raise WorkOrderError("stage submission must be a JSON object")
        self._validate_provenance(result)
        contract = result.get("contract")
        if contract not in {None, CAPABILITY_CONTRACTS[stage]}:
            raise WorkOrderError(f"submission contract mismatch for {stage}: {contract!r}")

        if stage == "research_planning":
            required = ("research_question", "scope", "queries", "rival_theses")
            for key in required:
                if key not in result:
                    raise WorkOrderError(f"research plan missing {key!r}")
            if not isinstance(result.get("queries"), list) or len(result["queries"]) < 3:
                raise WorkOrderError("research plan requires at least three queries")
        elif stage == "source_retrieval":
            sources = result.get("sources")
            if not isinstance(sources, list) or not sources:
                raise WorkOrderError("source retrieval must return a non-empty sources array")
        elif stage == "semantic_rerank":
            if not isinstance(result.get("scores"), list):
                raise WorkOrderError("semantic rerank must return scores array")
            if result.get("capability") not in {None, "semantic_rerank"}:
                raise WorkOrderError("semantic rerank capability identity mismatch")
        elif stage == "evidence_extraction":
            claims = result.get("claims")
            if not isinstance(claims, list) or not claims:
                raise WorkOrderError("evidence extraction must return claims array")
            for claim in claims:
                if (
                    not isinstance(claim, dict)
                    or not claim.get("exact_quote")
                    or not claim.get("source_id")
                ):
                    raise WorkOrderError(
                        "every evidence claim requires source_id and exact_quote"
                    )
        elif stage == "citation_support_audit":
            if not isinstance(result.get("audits"), list):
                raise WorkOrderError("citation support audit must return audits array")
        elif stage == "argument_construction":
            if not isinstance(result.get("nodes"), list) or not result.get("nodes"):
                raise WorkOrderError("argument construction must return non-empty nodes")
        elif stage in {"draft_generation", "revision"}:
            article = result.get("article") or result.get("text")
            if not isinstance(article, str) or not article.strip():
                raise WorkOrderError(f"{stage} must return non-empty article text")
        elif stage == "prose_transformation":
            candidate = result.get("candidate") or result.get("final_text")
            if not isinstance(candidate, str) or not candidate.strip():
                raise WorkOrderError("prose transformation must return candidate text")
        elif stage == "semantic_verification":
            if result.get("status") not in {"PASS", "REVIEW", "REJECT"}:
                raise WorkOrderError(
                    "semantic verification status must be PASS, REVIEW or REJECT"
                )
        elif stage == "hostile_review":
            if not isinstance(result.get("reviews"), list):
                raise WorkOrderError("hostile review must return reviews array")
        return result

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
        self.state.setdefault("submissions", []).append(
            {"stage": stage, "file": relative}
        )
        self.state.setdefault("history", []).append(
            {
                "event": "stage_accepted",
                "stage": stage,
                "contract": CAPABILITY_CONTRACTS[stage],
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
            "run_id": self.state["run_id"],
            "status": self.state["status"],
            "next_stage": self.state.get("stage"),
            "review_iteration": self.state.get("review_iteration", 0),
            "revision_count": self.state.get("revision_count", 0),
            "submissions": len(self.state.get("submissions", [])),
            "run_dir": str(self.run_dir),
        }

    def export_host_bundle(self, output_path: str | Path | None = None) -> Path:
        """Generate the replay/interchange bundle from accepted host work."""

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

        bundle = {
            "host": {
                "adapter": adapter.get("adapter"),
                "model_host": adapter.get("model_host"),
                "model": (transform.get("provenance") or {}).get(
                    "model", adapter.get("model_host")
                ),
                "execution_mode": adapter.get("execution_mode"),
                "api_key_used": bool(adapter.get("api_key_used", False)),
                "paid_api_calls": int(adapter.get("paid_api_calls", 0)),
                "blind_review_supported": False,
                "capability_contract_set": CAPABILITY_CONTRACT_SET,
            },
            "sources": retrieval.get("sources", []),
            "stages": {
                "research_plan": self._latest("research_planning") or {},
                "rerank_scores": (self._latest("semantic_rerank") or {}).get(
                    "scores", []
                ),
                "evidence_build": self._latest("evidence_extraction") or {},
                "evidence_audit": self._latest("citation_support_audit") or {},
                "argument_build": self._latest("argument_construction") or {},
                "draft": draft.get("article") or draft.get("text"),
                "reviews": self._all("hostile_review"),
                "revisions": [item for item in revisions if isinstance(item, str)],
            },
            "prose": {
                "adapter_mode": "host_native_swos_prose_contract",
                "safe_for_automatic_use": safe,
                "final_text": final_text,
                "semantic_verification": verification,
            },
            "work_order_run": {
                "protocol_version": PROTOCOL_VERSION,
                "run_id": self.state["run_id"],
                "review_iteration": self.state.get("review_iteration", 0),
                "revision_count": self.state.get("revision_count", 0),
            },
        }
        path = Path(output_path) if output_path else self.run_dir / "host-bundle.json"
        _write_json(path, bundle)
        return path
