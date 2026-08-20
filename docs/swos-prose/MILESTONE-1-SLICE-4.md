# SWOS Prose — Milestone 1 Slice 4: Proposition Coverage and Granularity

**Status:** implementation candidate  
**Goal:** harden what the verifier chooses to represent as a proposition, not only whether its mapping graph is structurally valid.

## Why this slice exists

Slices 1–3 established deterministic safety gates, a bidirectional proposition contract, and the first real model-assisted semantic-verifier adapter. Slice 4 addresses the next false-PASS/false-REJECT frontier: **coverage and granularity**.

A structurally perfect report can still be semantically poor if the provider:

- extracts the wrong units of meaning;
- ignores a methodological or epistemic distinction;
- promotes rhetorical decoration into a material proposition;
- drops a material evaluative claim as mere style;
- flattens hypothesis, inference, assumption and conclusion into one generic claim;
- mistakes safe lexical negation for a polarity flip.

## New proposition classifications

Each real-provider proposition now carries:

### `claim_type`

Controlled values:

- `empirical`
- `methodological`
- `interpretive`
- `normative`
- `definitional`
- `procedural`
- `evaluative`
- `other`
- `unknown`

### `epistemic_type`

Controlled values:

- `observation`
- `hypothesis`
- `inference`
- `assumption`
- `conclusion`
- `report`
- `method`
- `evaluation`
- `none`
- `unknown`

The core treats a resolved epistemic-type change as a blocker. A claim-type mismatch routes to REVIEW because classification itself can be contestable even when the underlying proposition may be equivalent.

Older static fixtures that do not populate these fields remain compatible; the real OpenAI structured-output schema requires them.

## Materiality boundary

Slice 4 deliberately rejects the rule that **all subjective language is disposable style**.

Example:

> The findings, which were surprising, suggest a new approach.

The parenthetical `surprising` may be merely rhetorical and safely omitted. But in another passage, `surprising` may carry argumentative weight by marking a result as anomalous relative to prior expectations.

Provider guidance therefore says:

- do not automatically promote every evaluative adjective into a standalone proposition;
- do not automatically discard evaluative language either;
- if evaluation is materially asserted, extract it with `claim_type="evaluative"`;
- if materiality is uncertain, use `unresolved` and route to REVIEW.

This preserves editorial freedom without pretending authorial stance is never meaningful.

## Discourse-marker boundary

Pure sequencing/formatting cues such as:

- `First`
- `To begin`

are not propositions by themselves.

However, Slice 4 does **not** declare all discourse markers superficial. Terms such as:

- `therefore`
- `because`
- `however`

can encode inference, causation, or contrast and may be semantically material. The verifier must preserve those relations when they carry argumentative content.

## Methodology vs interpretation

The verifier must distinguish:

> The analysis was performed using a t-test.

from an interpretation about whether a t-test is appropriate.

A lexical rewrite such as:

> The analysis used a t-test.

may preserve both `claim_type="methodological"` and `epistemic_type="method"`.

Changing methodological reporting into interpretive or hypothetical language cannot silently PASS.

## Epistemic status

The provider must not flatten:

- hypothesis;
- observation;
- inference;
- assumption;
- conclusion.

Example:

> We hypothesized that the drug would reduce symptoms.

is not automatically equivalent to:

> The drug was expected to reduce symptoms.

A resolved `hypothesis -> assumption` shift produces `EPISTEMIC_TYPE_CHANGED`.

## Lexical negation

Slice 4 extends deterministic risk detection with a deliberately small, reviewed lexicon of clear lexical negatives, including:

- `ineffective`
- `inefficient`
- `unavailable`
- `unable`
- `unsuccessful`
- `unknown`
- `incompatible`

This allows the deterministic layer to recognize negation presence in:

> The treatment was ineffective.

and:

> The treatment was not effective.

without falsely treating only the second sentence as negated.

The implementation **does not** infer negation from English prefixes generally. `un-`, `in-`, `dis-`, and `non-` are not universally compositional. Broader lexical and scope-sensitive negation remains an open hardening problem.

## Coverage validator

`swos_prose.verify.coverage` validates `claim_type` and `epistemic_type` over the existing many-to-many mapping graph.

Rules:

- one source proposition split into several candidate propositions may remain safe if each mapped fragment preserves compatible classification;
- resolved epistemic-type changes are blockers;
- claim-type mismatches route to REVIEW;
- unresolved/unknown classification cannot silently establish equivalence;
- in strict mode, merging source propositions with heterogeneous claim/epistemic types into one scalar-classified candidate routes to REVIEW.

The coverage validator is additive to the existing structural and semantic report validators.

## Adversarial fixtures

Slice 4 adds tests for:

1. non-material parenthetical evaluation;
2. material evaluative proposition deletion;
3. methodological lexical paraphrase;
4. claim-type mismatch;
5. sequencing cue rewrite (`First` -> `To begin`);
6. lexical negation equivalence (`ineffective` -> `not effective`);
7. lexical negation removal (`ineffective` -> `effective`);
8. hypothesis -> assumption drift;
9. unresolved epistemic classification.

Optional live-provider tests cover the same frontier when an API key is explicitly configured.

## Deliberate corrections to adversarial review

Slice 4 does not implement three overly broad reviewer assumptions:

1. **Subjective modifier = always non-material** — false. Evaluation can carry argumentative stance.
2. **All discourse markers = surface-only** — false. Some encode logical relations.
3. **All negative prefixes = compositional negation** — false. The deterministic layer uses only a narrow reviewed lexical set.

These corrections preserve the core SWOS principle: fail closed where semantic status is genuinely uncertain, but avoid false rejection when a safe equivalence can be established.
