"""Provider-neutral SWOS capability contracts and adapter declarations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

CAPABILITY_CONTRACT_SET = "swos.capabilities.v1"

CAPABILITY_CONTRACTS: dict[str, str] = {
    "research_planning": "swos.research-planning.v1",
    "source_retrieval": "swos.source-retrieval.v1",
    "semantic_rerank": "swos.semantic-rerank.v1",
    "evidence_extraction": "swos.evidence-extraction.v1",
    "citation_support_audit": "swos.citation-support-audit.v1",
    "argument_construction": "swos.argument-construction.v1",
    "draft_generation": "swos.draft-generation.v1",
    "semantic_verification": "swos.semantic-verification.v1",
    "hostile_review": "swos.hostile-review.v1",
    "revision": "swos.revision.v1",
    "prose_transformation": "swos.prose-transformation.v1",
}


class CapabilityError(RuntimeError):
    """Raised when an adapter cannot satisfy a required SWOS capability."""


@dataclass(frozen=True)
class CapabilityDeclaration:
    """One adapter's declaration for one SWOS capability."""

    name: str
    level: str = "full"
    contract: str | None = None
    assurance: tuple[str, ...] = ()
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level,
            "contract": self.contract or CAPABILITY_CONTRACTS.get(self.name),
            "assurance": list(self.assurance),
            "notes": self.notes,
        }


@dataclass
class AdapterCapabilities:
    """Provider-neutral adapter identity and capability matrix."""

    adapter: str
    model_host: str
    execution_mode: str
    declarations: dict[str, CapabilityDeclaration] = field(default_factory=dict)
    api_key_used: bool = False
    paid_api_calls: int = 0

    def supports(
        self, capability: str, *, accepted_levels: Iterable[str] = ("full", "native")
    ) -> bool:
        declaration = self.declarations.get(capability)
        return bool(declaration and declaration.level in set(accepted_levels))

    def require(
        self, capability: str, *, accepted_levels: Iterable[str] = ("full", "native")
    ) -> CapabilityDeclaration:
        declaration = self.declarations.get(capability)
        if declaration is None:
            raise CapabilityError(
                f"adapter {self.adapter!r} does not declare required capability {capability!r}"
            )
        levels = set(accepted_levels)
        if declaration.level not in levels:
            raise CapabilityError(
                f"adapter {self.adapter!r} declares {capability!r} as {declaration.level!r}; "
                f"required one of {sorted(levels)}"
            )
        expected = CAPABILITY_CONTRACTS.get(capability)
        actual = declaration.contract or expected
        if expected is not None and actual != expected:
            raise CapabilityError(
                f"adapter {self.adapter!r} declares {capability!r} contract {actual!r}; "
                f"SWOS requires {expected!r}"
            )
        return declaration

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_set": CAPABILITY_CONTRACT_SET,
            "adapter": self.adapter,
            "model_host": self.model_host,
            "execution_mode": self.execution_mode,
            "api_key_used": self.api_key_used,
            "paid_api_calls": self.paid_api_calls,
            "capabilities": {
                name: declaration.to_dict()
                for name, declaration in sorted(self.declarations.items())
            },
        }


def capability_evidence(
    *,
    capability: str,
    adapter: AdapterCapabilities,
    executed: bool,
    model: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical capability evidence attached to a stage result."""

    declaration = adapter.require(capability)
    evidence: dict[str, Any] = {
        "capability": capability,
        "contract": declaration.contract or CAPABILITY_CONTRACTS[capability],
        "contract_set": CAPABILITY_CONTRACT_SET,
        "executed": executed,
        "adapter": adapter.adapter,
        "model_host": adapter.model_host,
        "execution_mode": adapter.execution_mode,
        "model": model,
        "assurance": list(declaration.assurance),
    }
    if extra:
        evidence.update(extra)
    return evidence


def capability_satisfied(
    record: dict[str, Any],
    capability: str,
    *,
    contract: str | None = None,
) -> bool:
    """Return whether a runtime record proves the required SWOS capability."""

    expected_contract = contract or CAPABILITY_CONTRACTS[capability]
    return bool(
        record.get("executed") is True
        and record.get("capability") == capability
        and record.get("contract") == expected_contract
    )
