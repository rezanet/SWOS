"""Credential-free deterministic subject built through the real SWOS runtime."""

from __future__ import annotations

from pathlib import Path

from swos_runtime.models import ResearchRequest, SourceRecord, swos_id
from swos_runtime.orchestrator import AutonomousSWOS


class DeterministicRetriever:
    def __init__(self, *, bad_quotes: bool = False) -> None:
        self.bad_quotes = bad_quotes

    def retrieve(self, topic, queries):
        del topic, queries
        texts = [
            "Alpha evidence states that governed retrieval improves traceability. It also records a limitation: retrieval cannot prove truth by itself.",
            "Beta evidence states that verified citations reduce unsupported attribution. Counter evidence notes that verification can still miss interpretation errors.",
            "Gamma evidence states that explicit argument graphs expose hidden dependencies. The source cautions that graph structure does not guarantee a sound warrant.",
        ]
        return [
            SourceRecord(
                source_id=swos_id("src"),
                title=f"Source {index + 1}",
                url=f"https://example.invalid/{index + 1}",
                source_type="scholarly",
                provider=provider,
                text=text,
                metadata_verified=True,
                retraction_status="clean",
                retraction_checked_at="2026-08-30T00:00:00+00:00",
                retraction_check_source="deterministic-registry",
                licence="cc-by",
                access_status="open_access",
                redistribution_allowed=True,
                excerpt_limit_chars=2400,
                licence_cleared=True,
                licence_checked_at="2026-08-30T00:00:00+00:00",
                licence_check_source="deterministic-registry",
                retrieval_query="deterministic evaluation",
            )
            for index, (provider, text) in enumerate(
                zip(("alpha", "beta", "gamma"), texts, strict=True)
            )
        ]


class DeterministicProvider:
    model = "deterministic-evaluation-model"

    def __init__(self, *, bad_quotes: bool = False) -> None:
        self.bad_quotes = bad_quotes
        self.draft_called = False

    def plan(self, request, scope_hint):
        del request, scope_hint
        return {
            "research_question": "Does governed retrieval improve scholarly control?",
            "scope": "Credential-free deterministic evaluation scope.",
            "out_of_scope": [],
            "queries": ["alpha", "beta", "gamma"],
            "rival_theses": [
                "It improves control.",
                "It adds process without improving control.",
            ],
            "known_uncertainties": [],
            "reviewer_roles": ["citation_auditor", "argument_examiner"],
        }

    def rerank(self, topic, sources, top_k=10):
        del topic
        for index, source in enumerate(sources):
            source.rerank_score = 100 - index
        return sources[:top_k], {
            "method": "deterministic_cross_encoder",
            "model": self.model,
            "top_k": top_k,
            "scores": [
                {"source_id": source.source_id, "score": source.rerank_score}
                for source in sources[:top_k]
            ],
        }

    def build_evidence(self, topic, sources):
        del topic
        quotes = [
            "Alpha evidence states that governed retrieval improves traceability.",
            "It also records a limitation: retrieval cannot prove truth by itself.",
            "Beta evidence states that verified citations reduce unsupported attribution.",
            "Counter evidence notes that verification can still miss interpretation errors.",
            "Gamma evidence states that explicit argument graphs expose hidden dependencies.",
            "The source cautions that graph structure does not guarantee a sound warrant.",
        ]
        if self.bad_quotes:
            quotes = [f"missing quote {index}" for index in range(len(quotes))]
        source_ids = [
            sources[0].source_id,
            sources[0].source_id,
            sources[1].source_id,
            sources[1].source_id,
            sources[2].source_id,
            sources[2].source_id,
        ]
        return {
            "claims": [
                {
                    "claim": f"Verified deterministic claim {index + 1}",
                    "source_id": source_ids[index],
                    "exact_quote": quote,
                    "locator": f"paragraph {index + 1}",
                    "epistemic_type": "source_backed_claim",
                    "confidence": "high",
                    "stance": "limitation" if index in {1, 3, 5} else "support",
                    "rationale": "Deterministic direct support.",
                }
                for index, quote in enumerate(quotes)
            ]
        }

    def audit_evidence(self, candidates, sources):
        del sources
        return {
            "audits": [
                {
                    "index": index,
                    "support_level": "directly_supports",
                    "reason": "Exact deterministic support.",
                }
                for index, _ in enumerate(candidates)
            ]
        }

    def build_argument(self, topic, evidence_rows, rival_theses):
        del topic, rival_theses
        return {
            "thesis": "Governed retrieval improves control while not proving truth by itself.",
            "nodes": [
                {
                    "local_id": "n1",
                    "node_type": "claim",
                    "statement": "Governed retrieval improves traceability.",
                    "evidence_claim_ids": [evidence_rows[0]["claim_id"]],
                },
                {
                    "local_id": "n2",
                    "node_type": "grounds",
                    "statement": "Citation verification reduces unsupported attribution.",
                    "evidence_claim_ids": [evidence_rows[2]["claim_id"]],
                },
                {
                    "local_id": "n3",
                    "node_type": "objection",
                    "statement": "Verification can miss interpretation errors.",
                    "evidence_claim_ids": [evidence_rows[3]["claim_id"]],
                },
                {
                    "local_id": "n4",
                    "node_type": "qualifier",
                    "statement": "Graph structure is not itself proof.",
                    "evidence_claim_ids": [evidence_rows[5]["claim_id"]],
                },
            ],
            "edges": [
                {"from_local_id": "n2", "to_local_id": "n1", "relation": "supports"},
                {"from_local_id": "n3", "to_local_id": "n1", "relation": "objects_to"},
                {"from_local_id": "n4", "to_local_id": "n1", "relation": "qualifies"},
            ],
        }

    def draft(self, request, plan, evidence_rows, argument, source_labels):
        self.draft_called = True
        del request, plan, evidence_rows, argument
        markers = list(source_labels.values())[:3]
        sentence = (
            f"Governed research keeps evidence and conclusions distinguishable [{markers[0]}], "
            f"citation checks constrain unsupported attribution [{markers[1]}], and explicit "
            f"argument structure exposes limitations [{markers[2]}]. "
        )
        body = (sentence * 55).strip()
        return f"# Governed research\n\n{body}\n\n## Conclusion\n\n{sentence * 8}"

    def review(self, article, evidence_rows, argument, sources, iteration):
        del article, evidence_rows, argument, sources, iteration
        roles = [
            "citation_auditor",
            "argument_examiner",
            "discipline_expert",
            "hostile_reviewer",
            "editor",
            "governance_reviewer",
        ]
        return {
            "reviews": [
                {
                    "role": role,
                    "verdict": "pass",
                    "attack_summary": f"{role} found no unresolved blocker.",
                    "findings": [],
                }
                for role in roles
            ]
        }

    def revise(self, article, findings, evidence_rows, argument, source_labels):
        del findings, evidence_rows, argument, source_labels
        return article


def deterministic_prose(article, request):
    del request
    return article, {
        "invoked": True,
        "chunks": [{"safe_for_automatic_use": True}],
        "all_changed_text_safe": True,
    }


def build_deterministic_subject(root: str | Path):
    """Build one complete provider-free run through AutonomousSWOS."""
    runtime = AutonomousSWOS(
        stage_provider=DeterministicProvider(),
        retriever=DeterministicRetriever(),
        prose_transform=deterministic_prose,
    )
    return runtime.run(
        ResearchRequest(topic="Does governed retrieval improve scholarly control?", length=1500),
        root,
    )
