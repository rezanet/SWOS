---
contract: swos-memory-governance-contract
version: 1.0.0
status: frozen
---

# SWOS Memory Governance Contract

Split from the tool contract deliberately. Memory is not a tool; it is a
persistence surface with its own risk profile. **Memory is governed, not merely
long.**

The failure mode this contract exists to prevent has a name: **memory
contamination** - weak or unsupported reflections becoming durable "facts" that
future runs read as evidence. Reflection-style patterns are genuinely useful, but
in SWOS a reflection becomes memory only after support, review and expiry
metadata are attached.

## Memory tiers

| Tier | Scope | Persistence | Governance |
|---|---|---|---|
| **Working** | Single reasoning step | Ephemeral | None; never persisted |
| **Episodic** | One work item | Work lifetime | Retained in the audit pack; not read across works |
| **Semantic** | Concepts, definitions, relationships | Programme lifetime | Write requires source grounding |
| **Reflective** | Past mistakes, failed arguments, weak evidence | Programme lifetime | Write requires reviewer finding as basis |
| **User** | Style preferences, journals, terminology | User lifetime | Isolated; **never readable as evidence** |
| **Research Program Memory (RPM)** | Cross-project scholarly continuity | Indefinite with expiry | Full write approval path |

Only RPM and user memory persist across works. The isolation of user memory is
structural: a preference for a theorist is a stylistic fact about the user, and
must never be readable as a scholarly fact about the theorist.

## The six memory verbs

Every memory policy must define all six. A tier with an undefined verb is
non-conformant.

### READ

* Any agent may read RPM entries whose `data_classification` is at or below the
  work's classification.
* Reads are logged as EPG activities. Memory that influenced an output must be
  traceable from the output.
* Expired and `contradicted` items are not returned to agents by default; they
  are returned to the Governance Officer and the Adversarial Reviewer.

### WRITE

A durable write requires **all** of:

1. `provenance.epg_node_ids` - at least one supporting provenance node;
2. `provenance.sdl_decision_id` - an SDL entry of type `memory_write`;
3. `owner` - an accountable actor;
4. `confidence` - high, medium or low;
5. `expiry` - a date. Memory without expiry becomes silent dogma;
6. passing `governance/policies/memory-write.policy.json`.

**Never write:** raw sensitive content, restricted data, prompts, responses,
secrets, customer content, or unsupported reflections. Store *source-grounded
lessons*, not the material the lesson came from. The principle is metadata-first:
audit what happened, not the payload it happened to.

### UPDATE

Items are updated in place only for `last_confirmed_at` and `status`. A change of
substance is a **correction**, not an update, and creates a new item linked by
`correction_of`.

### EXPIRY

* Default retention is defined per category in the memory policy.
* On expiry an item moves to `expired` and stops being returned to agents. It is
  not deleted - expiry is a visibility change, deletion is a rights operation.
* Expired items remain in the audit trail.

### CORRECTION

* Any agent or human may raise a correction. Corrections require an SDL entry.
* The corrected item moves to `corrected` and retains a pointer to its successor.
* Original rationale is never overwritten. This mirrors SDL supersession.

### DELETION

* Deletion is a **rights and privacy operation**, not a tidiness operation.
* Triggered by: data subject request, licence revocation, classification error,
  or retention expiry under the retention policy.
* Deletion writes deletion evidence to the audit trail. The item's existence and
  removal remain provable; its content does not.

## Contradiction handling

When a new candidate write conflicts with an existing item, the system does not
overwrite and does not silently coexist. It creates a contradiction record with
one of six states:

| State | Meaning |
|---|---|
| `open_contradiction` | Plausible unresolved conflict |
| `under_review` | Evidence gathering or expert review active |
| `resolved_by_evidence` | One position is now better supported |
| `resolved_by_scope` | Both are valid under different assumptions |
| `parked` | Insufficient evidence to resolve |
| `retired` | No longer relevant or superseded |

`resolved_by_scope` is a legitimate and common scholarly outcome. A system that
cannot represent "both, under different assumptions" will manufacture false
resolutions.

## What RPM stores

* Research agendas - enduring programmes, target publications, long-term questions
* Open questions - unresolved problems, missing sources, untested hypotheses
* Concept lineage - definitions, genealogies, rival concepts, ontology mappings
* Claim lifecycle - proposed, supported, weakened, rejected, superseded
* Evidence history - validated sources, excluded sources, counter-evidence, retractions
* Contradictions - evidence conflicts, unresolved interpretations, theory clashes
* Accepted and rejected positions - what the programme has committed to
* Reviewer lessons - recurring objections, accepted corrections, known weak moves
* Method lessons - what methods are valid in which discipline
* Future work - planned searches, experiments, interviews, archival checks
* Publications - what this programme has released
* Memory policies - the governing rules themselves

## Memory contamination test

`evals/fixtures/memory/` seeds RPM with a plausible but false prior item and
asserts that it does **not** become an accepted fact in the next run. The test
passes only if the system either flags the contradiction or requires re-grounding.
This test runs on every release. See `contracts/evaluation-contract/`.
