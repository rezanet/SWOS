# T079 Source-Diversity Packet Construction Specification

Status: RESEARCH/PREPARATION ONLY  
Baseline authority: `1f5135969f04a104d4a99764f921d1743d22710f`  
Frozen task: T079  

This specification turns the existing T079 planning note into a concrete packet/data shape that can be generated automatically and then handed to independent human reviewers. It is not human review and does not complete T079.

## Frozen task boundary

T079 requires separate tuning packets plus at least ten locked human-reviewed packets per each of the nine supported disciplines, spanning the frozen stress categories `balanced`, `concentrated`, `sparse`, `narrow`, `multilingual`, `historical`, `method_monoculture`, `duplicate`, `fake_diversity`, and `missing_strata`.

The current production diversity engine defines eleven measured dimensions: `work_family`, `publisher`, `venue`, `author_cluster`, `geography`, `language`, `period`, `methodology`, `source_type`, `access_mode`, and `stance`. It also distinguishes source-count from claim-exposure distributions, metadata states (`observed`, `externally_verified`, `inferred`, `unknown`), pre-retrieval requirements, family-count status, required strata, counter-position requirements, and the v2 geometric composite.

## Candidate cohort

Prepare 12 candidates per discipline (108 total). The first two are tuning candidates and must never enter the locked evaluation set. The other ten are locked candidates once independent review is complete.

Per-discipline allocation:

1. balanced — tuning
2. balanced — tuning
3. concentrated — locked candidate
4. concentrated — locked candidate
5. sparse — locked candidate
6. narrow — locked candidate
7. multilingual — locked candidate
8. historical — locked candidate
9. method_monoculture — locked candidate
10. duplicate — locked candidate
11. fake_diversity — locked candidate
12. missing_strata — locked candidate

The category is a construction/stress intent, not the human truth label.

## Packet object

Every generated packet should use this logical shape:

```json
{
  "schema_version": "2.0.0-candidate",
  "packet_id": "DIV-ART-HISTORY-03",
  "discipline": "art_history",
  "partition": "locked_candidate",
  "stress_category": "concentrated",
  "status": "candidate_unreviewed",
  "research_question": "...",
  "construction": {
    "generator_version": "...",
    "generator_digest": "sha256",
    "generated_at": "ISO-8601",
    "source_metadata_snapshot_digest": "sha256",
    "construction_intent": "concentrated",
    "construction_notes": []
  },
  "pre_retrieval_requirement": {
    "requirement_id": "...",
    "dimensions": ["publisher", "venue", "geography", "language", "period", "methodology", "source_type", "access_mode", "stance"],
    "required_strata": {},
    "min_family_count": 5,
    "max_hhi": 0.40,
    "max_share": 0.60,
    "min_composite": 0.50,
    "max_unknown_rate": 0.10,
    "counter_position_required": false,
    "declared_before_retrieval": true,
    "claim_exposure_required": true,
    "ontology_digest": "sha256"
  },
  "source_records": [],
  "canonical_families": [],
  "claim_exposure_edges": [],
  "machine_result": null,
  "review": null,
  "packet_digest": "sha256"
}
```

## Source record

A source record is retrieval provenance, not a diversity family. Preserve at least:

```json
{
  "source_id": "SRC-...",
  "provider": "openalex",
  "retrieved_uri": "...",
  "canonical_work_id": "https://doi.org/...",
  "doi": "...",
  "isbn": null,
  "title": "...",
  "publisher": {"value": "...", "status": "externally_verified", "evidence_uri": "..."},
  "venue": {"value": "...", "status": "externally_verified", "evidence_uri": "..."},
  "author_cluster": {"value": "...", "status": "externally_verified", "evidence_uri": "..."},
  "geography": {"value": "...", "status": "observed", "evidence_uri": "..."},
  "language": {"value": "en", "status": "observed", "evidence_uri": "..."},
  "period": {"value": "2020s", "status": "externally_verified", "evidence_uri": "..."},
  "methodology": {"value": "...", "status": "inferred", "evidence_uri": "..."},
  "source_type": {"value": "journal_article", "status": "externally_verified", "evidence_uri": "..."},
  "access_mode": {"value": "open_access", "status": "externally_verified", "evidence_uri": "..."},
  "stance": {"value": "support", "status": "observed", "evidence_uri": "..."}
}
```

Provider identity is provenance only and must never create diversity.

## Canonical family object

Canonicalize duplicate provider records, mirrors, editions, accepted manuscripts, repository copies, and preprint/final relationships before scoring.

```json
{
  "family_id": "FAM-...",
  "canonical_key": "doi:10....",
  "source_ids": ["SRC-...", "SRC-..."],
  "provider_ids": ["openalex", "crossref"],
  "identifiers": {"doi": "10...."},
  "titles": ["..."],
  "metadata": {
    "work_family": {"value": "FAM-...", "status": "externally_verified"},
    "publisher": {"value": "...", "status": "externally_verified"},
    "venue": {"value": "...", "status": "externally_verified"},
    "author_cluster": {"value": "...", "status": "externally_verified"},
    "geography": {"value": "...", "status": "observed"},
    "language": {"value": "...", "status": "observed"},
    "period": {"value": "...", "status": "externally_verified"},
    "methodology": {"value": "...", "status": "inferred"},
    "source_type": {"value": "...", "status": "externally_verified"},
    "access_mode": {"value": "...", "status": "externally_verified"},
    "stance": {"value": "...", "status": "observed"}
  }
}
```

Only `observed` and `externally_verified` values count as known for the Research Grade metric. `inferred` and `unknown` must never improve a score.

## Claim-exposure edge

Each unique `(claim_id, family_id)` pair contributes one exposure. Multiple URLs/editions/providers from the same family cannot multiply exposure.

```json
{
  "claim_id": "CLM-001",
  "family_id": "FAM-001",
  "source_ids": ["SRC-001", "SRC-019"],
  "relationship": "supports",
  "edge_digest": "sha256"
}
```

## Machine result

Before human review, run the production `source_diversity` path and preserve its raw output rather than reproducing formulas in the packet generator. The result must include:

- family count and provider count;
- per-dimension source-count distribution;
- per-dimension claim-exposure distribution;
- HHI, max share, effective categories and normalized balance for both;
- the worse governed dimension balance;
- required-strata coverage;
- metadata completeness and unknown rate;
- research-grade composite;
- raw status, exception state, limitations and corrective queries;
- family and requirement digests.

The machine result is diagnostic. It is not the locked expected answer.

## Independent review object

Leave this object absent/null until a real reviewer acts. The final review shape should be:

```json
{
  "status": "reviewed",
  "reviewer_id": "external-human-id",
  "reviewed_at": "ISO-8601",
  "packet_digest_reviewed": "sha256",
  "family_canonicalization_correct": true,
  "metadata_evidence_states_correct": true,
  "material_gaps": ["..."],
  "narrow_corpus_exception_justified": false,
  "expected_outcome": "fail",
  "expected_failure_dimensions": ["publisher", "methodology"],
  "rationale": "...",
  "disposition": "lock"
}
```

A reviewer may reject/repair a candidate rather than lock it. The generator must not create reviewer IDs, expected outcomes, rationales, or approvals.

## Construction rules by stress category

- `balanced`: >=5 canonical families, deliberately broad across declared applicable dimensions, no seeded material gap.
- `concentrated`: one or more predeclared dimensions intentionally dominated by a single known category, while enough families exist to avoid the trivial <3-family rule.
- `sparse`: 1–4 families, testing fail/review family-count handling.
- `narrow`: a legitimately narrow evidence domain where raw diversity may fail but any exception must remain explicit, expiring, limitation-bearing, and human-governed.
- `multilingual`: at least two languages in the source families, with a predeclared language requirement; do not infer language from title text if metadata exists.
- `historical`: deliberate period concentration or period-gap against a predeclared historical requirement.
- `method_monoculture`: multiple independent families but the same methodology/method-family, proving family count alone does not imply epistemic diversity.
- `duplicate`: several provider/source records collapse into fewer canonical work families; scoring must use the collapsed family set.
- `fake_diversity`: the same work/family appears through multiple providers or mirrors; provider count must not improve the gate.
- `missing_strata`: a predeclared required stratum is absent or metadata is insufficient; unknown/inferred metadata must not manufacture coverage.

## Tuning/locked separation

The two tuning candidates per discipline may be used to debug packet construction and benchmark plumbing. They must be excluded from T080 locked metric denominators. Once a locked candidate receives genuine review and is frozen, its packet digest must prevent later editing without an explicit new version.

## Generator invariants

A production-side packet builder should fail closed if:

- `declared_before_retrieval` is false;
- source families are not canonicalized;
- provider names appear in family identity logic;
- an `inferred`/`unknown` metadata value is treated as known;
- duplicate `(claim_id, family_id)` edges are counted more than once;
- packet review fields are populated by automation;
- a locked packet is mutated after review without a version change;
- tuning packets enter locked denominators.

## Durable next action

Generate the 108 candidate IDs from `T079-CANDIDATE-PACKET-SET.json`, populate source-family and pre-retrieval requirement data through the verified metadata substrate, run the production diversity path, then stop at `READY_FOR_HUMAN_REVIEW` for each candidate lacking a genuine reviewer record.