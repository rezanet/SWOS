"""Rewrite orchestration for SWOS Prose.

All public writer modes share one safety pipeline. A generated candidate is
released automatically only after semantic PASS. Bounded local-span repair is
still limited to high-confidence, machine-actionable lexical deltas, at most
twice, with every mutation mechanically span-confined and fully re-verified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, cast

from .anchors import extract_anchors
from .context import ContextSafety, inspect_context
from .diagnostics import PolishDiagnostics, diagnose_polish
from .models import RepairAttempt, VerificationResult, VerificationStatus
from .modes import writer_policy
from .pipeline import verify_rewrite_with_repair
from .providers.base import SemanticVerifierProvider
from .providers.rewrite_base import RewriteCandidate, RewriteProvider
from .repair import RepairProvider

ASSURANCE_LEVELS = {"standard", "strict", "review"}
_DEGREE_MARKERS = (
    "somewhat",
    "slightly",
    "marginally",
    "moderately",
    "considerably",
    "substantially",
    "significantly",
    "highly",
    "strongly",
    "partly",
    "partially",
    "largely",
    "mostly",
    "nearly",
    "almost",
    "barely",
    "hardly",
)
_MODAL_MARKERS = ("may", "might", "can", "could", "should", "would", "must")


def _present_markers(source: str, markers: tuple[str, ...]) -> list[str]:
    return [m for m in markers if re.search(rf"\b{re.escape(m)}\b", source, re.IGNORECASE)]


def _semantic_force_profile(source: str) -> dict[str, list[str]]:
    return {
        "degree_markers": _present_markers(source, _DEGREE_MARKERS),
        "modal_markers": _present_markers(source, _MODAL_MARKERS),
    }


@dataclass
class PolishResult:
    source: str
    candidate: str
    final_text: str
    assurance: str
    verification: VerificationResult | None
    used_source_fallback: bool
    diagnostics_before: PolishDiagnostics | None = None
    repair_attempts: list[RepairAttempt] = field(default_factory=list)
    repair_success: bool = False
    repair_failure_reason: str | None = None
    notes: list[str] = field(default_factory=list)
    rewrite_call_count: int = 0
    rewrite_token_usage: dict[str, int] | None = None
    rewrite_cost_estimate: float | None = None
    verifier_call_count: int = 0
    verifier_token_usage: dict[str, int] | None = None
    verifier_cost_estimate: float | None = None
    mode: str = "polish"
    preset: str | None = None
    context_safety: dict[str, Any] | None = None

    @property
    def safe_for_automatic_use(self) -> bool:
        if (
            not self.source.strip()
            and self.candidate == self.source
            and self.final_text == self.source
            and self.verification is None
            and not self.used_source_fallback
        ):
            return True
        if self.diagnostics_before is not None and self.diagnostics_before.no_change_recommended:
            return True
        return self.verification is not None and self.verification.status is VerificationStatus.PASS

    @property
    def verification_status(self) -> str | None:
        return self.verification.status.value if self.verification is not None else None

    @property
    def context_rejected(self) -> bool:
        return bool(self.context_safety and not self.context_safety.get("accepted", True))

    @property
    def generation_skipped_by_diagnostics(self) -> bool:
        return (
            self.diagnostics_before is not None
            and self.diagnostics_before.no_change_recommended
            and self.candidate == self.source
            and self.rewrite_token_usage is None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "preset": self.preset,
            "assurance": self.assurance,
            "source": self.source,
            "candidate": self.candidate,
            "final_text": self.final_text,
            "used_source_fallback": self.used_source_fallback,
            "safe_for_automatic_use": self.safe_for_automatic_use,
            "context_rejected": self.context_rejected,
            "verification_status": self.verification_status,
            "verification": self.verification.to_dict() if self.verification is not None else None,
            "diagnostics_before": self.diagnostics_before.to_dict()
            if self.diagnostics_before is not None
            else None,
            "generation_skipped_by_diagnostics": self.generation_skipped_by_diagnostics,
            "repair_attempts": [attempt.to_dict() for attempt in self.repair_attempts],
            "repair_success": self.repair_success,
            "repair_failure_reason": self.repair_failure_reason,
            "notes": self.notes,
            "rewrite_call_count": self.rewrite_call_count,
            "rewrite_token_usage": self.rewrite_token_usage,
            "rewrite_cost_estimate": self.rewrite_cost_estimate,
            "verifier_call_count": self.verifier_call_count,
            "verifier_token_usage": self.verifier_token_usage,
            "verifier_cost_estimate": self.verifier_cost_estimate,
            "context_safety": self.context_safety,
        }


def _polish_plan(source: str) -> dict[str, Any]:
    return _writer_plan(source, "polish", None)


def _writer_plan(source: str, mode: str, preset: str | None) -> dict[str, Any]:
    plan = writer_policy(mode, preset)
    plan["semantic_force_profile"] = _semantic_force_profile(source)
    return plan


def _implicit_repair_provider(rewrite_provider: RewriteProvider) -> RepairProvider | None:
    return (
        cast(RepairProvider, rewrite_provider)
        if callable(getattr(rewrite_provider, "repair", None))
        else None
    )


def edit_text(
    *,
    source: str,
    rewrite_provider: RewriteProvider,
    verifier_provider: SemanticVerifierProvider | None,
    assurance: str = "strict",
    native_swos_context: dict | None = None,
    context_before: str | None = None,
    context_after: str | None = None,
    run_diagnostics: bool = True,
    repair_provider: RepairProvider | None = None,
    mode: str = "polish",
    preset: str | None = None,
) -> PolishResult:
    """Edit prose in one explicit mode, then verify, repair locally, or fail safe."""
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if assurance not in ASSURANCE_LEVELS:
        raise ValueError(f"Unknown assurance level: {assurance}")
    if not isinstance(run_diagnostics, bool):
        raise TypeError("run_diagnostics must be a boolean")
    if native_swos_context is not None and not isinstance(native_swos_context, dict):
        raise TypeError("native_swos_context must be a dictionary or None")
    plan = _writer_plan(source, mode, preset)
    context_info: ContextSafety = inspect_context(context_before, context_after)
    if not source.strip():
        return PolishResult(
            source=source,
            candidate=source,
            final_text=source,
            assurance=assurance,
            verification=None,
            used_source_fallback=False,
            mode=mode,
            preset=preset,
            context_safety=context_info.to_dict(),
            notes=["No source prose supplied; no change recommended."],
        )

    if not context_info.accepted:
        return PolishResult(
            source=source,
            candidate=source,
            final_text=source,
            assurance=assurance,
            verification=None,
            used_source_fallback=True,
            mode=mode,
            preset=preset,
            context_safety=context_info.to_dict(),
            notes=["Read-only context failed its safety bounds; source preserved."],
        )

    diagnostics_before = (
        diagnose_polish(
            source,
            context_before=context_before,
            context_after=context_after,
            mode=mode,
            preset=preset,
        )
        if run_diagnostics
        else None
    )
    if diagnostics_before is not None and diagnostics_before.no_change_recommended:
        return PolishResult(
            source=source,
            candidate=source,
            final_text=source,
            assurance=assurance,
            verification=None,
            used_source_fallback=False,
            mode=mode,
            preset=preset,
            context_safety=context_info.to_dict(),
            diagnostics_before=diagnostics_before,
            notes=[
                "Pre-generation diagnostics found positive evidence for a narrow already-good prose shape; generation and semantic verification were skipped."
            ],
        )

    protected_anchors = [a.to_dict() for a in extract_anchors(source) if a.protected]
    rewrite_call_count = 1
    try:
        proposal = rewrite_provider.rewrite(
            source=source,
            mode=mode,
            protected_anchors=protected_anchors,
            rewrite_plan=plan,
            context_before=context_before,
            context_after=context_after,
        )
    except (TypeError, ValueError, RuntimeError) as exc:
        return PolishResult(
            source=source,
            candidate=source,
            final_text=source,
            assurance=assurance,
            verification=None,
            used_source_fallback=True,
            mode=mode,
            preset=preset,
            context_safety=context_info.to_dict(),
            diagnostics_before=diagnostics_before,
            rewrite_call_count=rewrite_call_count,
            notes=[f"Rewrite provider failed; source preserved: {exc}"],
        )
    if not isinstance(proposal, RewriteCandidate):
        return PolishResult(
            source=source,
            candidate=source,
            final_text=source,
            assurance=assurance,
            verification=None,
            used_source_fallback=True,
            mode=mode,
            preset=preset,
            context_safety=context_info.to_dict(),
            diagnostics_before=diagnostics_before,
            rewrite_call_count=rewrite_call_count,
            notes=["Rewrite provider returned a malformed result object; source preserved."],
        )
    candidate = proposal.candidate_text
    if not isinstance(candidate, str):
        return PolishResult(
            source=source,
            candidate=source,
            final_text=source,
            assurance=assurance,
            verification=None,
            used_source_fallback=True,
            mode=mode,
            preset=preset,
            context_safety=context_info.to_dict(),
            diagnostics_before=diagnostics_before,
            rewrite_call_count=rewrite_call_count,
            notes=["Rewrite provider returned a non-string candidate; source preserved."],
        )

    execution = verify_rewrite_with_repair(
        source=source,
        candidate=candidate,
        assurance=assurance,
        verifier_provider=verifier_provider,
        repair_provider=repair_provider or _implicit_repair_provider(rewrite_provider),
        native_swos_context=native_swos_context,
        context_before=context_before,
        context_after=context_after,
        context_safety=context_info.to_dict(),
    )
    verification, verified_candidate = execution.verification, execution.candidate
    if verification.verifier_skip_reason == "terminal_newline_only":
        final_text, used_source_fallback = source, False
        decision_note = "Candidate differed only by terminal line-ending whitespace; the original source representation was preserved."
    elif verification.status is VerificationStatus.PASS:
        final_text, used_source_fallback = verified_candidate, False
        decision_note = (
            "Bounded repair succeeded and the repaired candidate passed semantic re-verification."
            if execution.success
            else "Candidate passed semantic verification and is safe for automatic use."
        )
    else:
        final_text, used_source_fallback = source, True
        suffix = f" Repair detail: {execution.failure_reason}" if execution.failure_reason else ""
        decision_note = f"Candidate verification returned {verification.status.value}; the original source was preserved.{suffix}"

    repair_provider_notes = [
        note for attempt in execution.attempts for note in attempt.provider_notes
    ]
    return PolishResult(
        source=source,
        candidate=verified_candidate,
        final_text=final_text,
        assurance=assurance,
        verification=verification,
        used_source_fallback=used_source_fallback,
        diagnostics_before=diagnostics_before,
        repair_attempts=execution.attempts,
        repair_success=execution.success,
        repair_failure_reason=execution.failure_reason,
        notes=[*proposal.notes, *repair_provider_notes, decision_note],
        rewrite_call_count=rewrite_call_count,
        rewrite_token_usage=proposal.token_usage,
        rewrite_cost_estimate=proposal.cost_estimate,
        verifier_call_count=execution.verifier_call_count,
        verifier_token_usage=execution.verifier_token_usage,
        verifier_cost_estimate=execution.verifier_cost_estimate,
        mode=mode,
        preset=preset,
        context_safety=context_info.to_dict(),
    )


def polish_text(
    *,
    source: str,
    rewrite_provider: RewriteProvider,
    verifier_provider: SemanticVerifierProvider | None,
    assurance: str = "strict",
    native_swos_context: dict | None = None,
    context_before: str | None = None,
    context_after: str | None = None,
    run_diagnostics: bool = True,
    repair_provider: RepairProvider | None = None,
    mode: str = "polish",
    preset: str | None = None,
) -> PolishResult:
    """Backward-compatible entry point for the common edit pipeline."""

    return edit_text(
        source=source,
        rewrite_provider=rewrite_provider,
        verifier_provider=verifier_provider,
        assurance=assurance,
        native_swos_context=native_swos_context,
        context_before=context_before,
        context_after=context_after,
        run_diagnostics=run_diagnostics,
        repair_provider=repair_provider,
        mode=mode,
        preset=preset,
    )
