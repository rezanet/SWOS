---
artefact: knowledge-and-reasoning-specification
version: 1.0.0
status: frozen
---

# Knowledge & Reasoning Specification

**This is the core intellectual property of SWOS.** It is a standalone artefact,
not a prompt appendix.

It defines what the system is permitted to *mean* by "evidence", "argument",
"method", "interpretation", "support", "uncertainty" and "quality". Without it,
those words drift per run, per model and per discipline, and the platform's
guarantees become unenforceable.

---

## 1. Epistemic typology

Every claim carries exactly one type. Different disciplines apply different truth
standards, and a system that cannot represent the difference will apply a
psychology proof standard to an art-criticism claim - or, worse, the reverse.

| Type | Definition | Citation burden | Permitted grammar |
|---|---|---|---|
| `observed_fact` | Directly observed or measured; not contested in the field | At least one primary source with a passage span | Declarative |
| `source_backed_claim` | Asserted by an identified source and adopted here | At least one source with `directly_supports` | Declarative with attribution |
| `inference` | Derived by reasoning from other claims | Cite the premises, not a source for the conclusion | "It follows that", "this implies" |
| `interpretation` | A reading of evidence among possible readings | Evidence base **plus** rival readings | "On this reading", "this suggests" |
| `hypothesis` | A proposition offered for testing | May be uncited if labelled | "We hypothesise", "if X then" |
| `speculation` | Beyond current evidence, offered as such | May be uncited if labelled | "Speculatively", "one might conjecture" |
| `critical_assessment` | An evaluative judgement of a work, method or position | The features assessed must be evidenced | "This is weak because" |
| `normative_judgement` | A claim about what ought to be | Grounds stated; never presented as descriptive | "Should", "ought", with stated grounds |
| `unverified_claim` | Asserted but not yet verified | **Must be visibly marked in the output** | Marked as unverified |

**The cardinal rule: never present an inference in the grammar of an observed
fact.** This single substitution is how a chain of reasonable steps becomes an
unfounded assertion that no reviewer can locate.

### Type transitions

A claim may be promoted or demoted; the transition is an SDL `claim_acceptance`
decision, never a silent edit.

```
unverified_claim --[citation verified, directly_supports]--> source_backed_claim
source_backed_claim --[source retracted]--> unverified_claim
hypothesis --[evidence gathered, supports]--> source_backed_claim
interpretation --[rival reading better supported]--> demoted; rival promoted
inference --[premise withdrawn]--> withdrawn, not weakened
```

---

## 2. Citation-support taxonomy

Citation existence is necessary and insufficient. Classify the **relationship**
between the cited passage and the specific claim.

| Status | Meaning | Effect |
|---|---|---|
| `directly_supports` | The cited passage supports the exact claim as stated | Claim supported |
| `partially_supports` | The source supports part of the claim | Written rationale required naming which part; the remainder needs separate support |
| `context_only` | Relevant background; does not establish the sentence | **Claim is unsupported** |
| `contradicts` | The source undermines the claim it is cited for | Blocker; claim must be revised or withdrawn |
| `citation_laundering_risk` | Real source, wrong claim | Blocker; release prevented until resolved |
| `invalid_citation` | Does not exist, or metadata fails verification | Blocker; never "corrected" into a different source |

A claim whose only citations are `context_only` is unsupported. This is stated
explicitly because it is the most common way a supported-looking claim is in fact
unsupported.

### Support is passage-level, never document-level

Document-level support assertions are forbidden. "Smith (2019) supports this" is
not a classification; "Smith (2019), p. 412, second paragraph, supports this"
is. Citation laundering survives every check except this one.

---

## 3. Evidence hierarchy

Evidence strength is **discipline-relative**. There is no universal ranking, and
imposing one is a named anti-pattern.

### General frame

| Tier | Empirical disciplines | Interpretive disciplines |
|---|---|---|
| Strongest | Systematic review, meta-analysis, pre-registered replication | Primary source, original artwork or object, archival document |
| Strong | Well-powered primary study, validated dataset | Specialist monograph, catalogue raisonné, critical edition |
| Moderate | Single study, technical report, standards document | Peer-reviewed article, exhibition catalogue |
| Weak | Conference abstract, preprint, vendor white paper | General survey, tertiary commentary |
| Weakest | Opinion piece, blog post, undocumented claim | Uncredited reproduction, secondary paraphrase |

Discipline packs override this table. A materials science claim about a
processing route needs a characterised experiment, not a review. An art-history
claim about a brushstroke needs the object or a technical study of the object,
not a monograph paraphrasing someone who saw it.

### Evidence theory dimensions

Every source is appraised on: source type, method quality, recency, retraction
status, representativeness, independence, counter-evidence position, and
field-specific support burden.

**Independence matters more than count.** Five sources tracing to one primary
study are one piece of evidence with four echoes. The citation-graph walk exists
to detect this.

---

## 4. Argument model

Toulmin, extended.

| Component | Role | SWOS requirement |
|---|---|---|
| **Claim** | The proposition argued for | Must exist in the Evidence Matrix |
| **Grounds** | The evidence offered | Must reference matrix claim ids; grounds without evidence is assertion |
| **Warrant** | The principle licensing grounds → claim | **Must be explicit.** Hidden warrants are the commonest defect |
| **Backing** | Support for the warrant itself | Required where the warrant is discipline-specific or contested |
| **Qualifier** | The strength and scope of the claim | Must survive editing; removing a qualifier changes the claim |
| **Objection** | A challenge to claim, grounds or warrant | Raised by review; unresolved objections surface in the uncertainty statement |
| **Rebuttal** | Response to an objection | Concession is a legitimate rebuttal outcome |
| **Implication** | What follows if the claim holds | Enables the scope of a contribution to be checked |
| **Rival reading** | An alternative interpretation of the same evidence | **Mandatory** in interpretive disciplines |

### Why `rival_reading` is a first-class node

Interpretive flattening - collapsing genuine ambiguity into a single safe reading
- is a named failure mode of generated humanities writing. Making rival readings a
graph node type rather than a prose gesture means their absence is
machine-detectable.

### Relation confidence

Every edge carries a confidence. This is the structural control against
**over-association**: linking unrelated facts into a neat but false synthesis.
Empirical analysis of long-form generated articles identifies this - shaky links
and irrelevant content, not classic factual hallucination - as the dominant
residual error. Low-confidence edges are routed to the Adversarial Reviewer.

---

## 5. Uncertainty taxonomy

Uncertainty is typed, because different types demand different responses.

| Type | Meaning | Required response |
|---|---|---|
| `missing_evidence` | No evidence located | Mark unsupported; declare as a gap |
| `weak_support` | Evidence exists but is thin or low-tier | Qualify the claim; do not upgrade the language |
| `conflicting_evidence` | Credible sources disagree | Present both; record the contradiction; do not adjudicate for tidiness |
| `method_uncertainty` | The method cannot bear the claim's weight | Methodologist qualification; bound the claim |
| `construct_limitation` | The measure does not capture the concept | State the construct gap explicitly |
| `interpretive_plurality` | Multiple defensible readings | Present rival readings; do not pick silently |
| `source_bias` | Evidence base is skewed | Report the skew; attempt counter-position retrieval |
| `temporal_staleness` | Evidence may be superseded | State the as-at date; register a retraction watch |
| `domain_transfer_risk` | Finding imported across a domain boundary | State the transfer explicitly and justify it |

**Uncertainty declared before evidence gathering is scholarship. Uncertainty
discovered after drafting is a defect.** The research planner records known
uncertainties up front for exactly this reason.

---

## 6. Reasoning standards

The mode must fit the task. A single chain-of-thought monoculture is a design
error.

| Mode | Use for | Control it provides |
|---|---|---|
| Recursive decomposition | Essays, surveys, reports | Structural coverage |
| Tree-of-Thoughts exploration | Competing theses, rival interpretations, solution paths | Prevents first-idea lock-in and interpretive flattening |
| ReAct-style tool interleaving | Evidence-seeking and verification | Keeps reasoning tied to retrieval |
| Reflexion | Learning from failed drafts and reviewer feedback | Improvement without weight updates - **but writes to memory only under the memory contract** |
| Self-refine | Iterative improvement | **Capped at three iterations** |
| Cross-reflection | An independent critic with a rubric reviews the generator | Catches what self-review misses |

Quality dimensions applied throughout: validity, soundness, coverage, relevance,
method rigour, interpretive plausibility, counterargument handling, source
diversity.

**Reflexion carries a specific hazard.** Storing verbal reflections improves later
attempts, and it is also precisely how memory contamination begins. In SWOS,
reflections become memory only after support, review and expiry metadata are
attached. See the memory governance contract.

---

## 7. Interpretation frameworks

For humanities, art history and art criticism, interpretation is the work, not a
decoration on it.

* **Rival readings** - state at least two; explain the preference on evidential
  grounds, not stylistic ones.
* **Historical plausibility** - would this reading have been available in that
  context?
* **Visual evidence** - for art disciplines, an interpretive claim must anchor to
  observed features of the object, not to secondary commentary about it.
* **Translation limits** - flag where the argument depends on a translated term.
* **Reception history** - distinguish what a work meant, what it was taken to
  mean, and what it is taken to mean now.
* **Cultural context** - state the frame; do not naturalise it.

---

## 8. Discipline ontologies

Each discipline pack instantiates: reasoning module, evidence hierarchy, proof
standard, required analysis moves, failure modes, rubric and acceptance test.

| Discipline | Reasoning module | Must evaluate |
|---|---|---|
| Philosophy | Argument reconstruction, conceptual genealogy, counterexample generation, modal and normative distinction | Validity, soundness, hidden premises, equivocation, schools of interpretation, objections |
| Psychology | Method and evidence appraisal | Constructs, measurement validity, sample, power, bias, confounds, causal overreach, ethics |
| Materials science | Structure-property-process-performance reasoning | Materials class, synthesis route, microstructure, characterisation, mechanisms, property trade-offs |
| Engineering | System, constraint and trade-off reasoning | Requirements, assumptions, design alternatives, failure modes, operability, safety, maintainability |
| Art history | Object, formal and contextual analysis | Material, technique, style, iconography, provenance, patronage, function, historical plausibility |
| Art criticism | Interpretive judgement and critical voice | Sensory description, aesthetic claim, cultural frame, reception, originality, affect, ethical context |
| Humanities | Hermeneutic and historical reasoning | Context, archive, discourse, translation, ideology, reception, rival readings |
| Technical writing | Requirements and design reasoning | Requirements, assumptions, alternatives, constraints, trade-offs, failure modes, operational considerations |
| Interdisciplinary | Boundary translation | Terminology conflicts, method transfer, evidence mismatch, conceptual synthesis |

---

## 9. Writing standards

Applied **after** the evidence and argument work, never as a substitute for it.

* Genre-specific structure and section templates
* Citation style conformance
* AI-use disclosure where required
* Reviewer pack accompanying the output
* Provenance export in a PROV-compatible serialisation

**Editing may not change what a claim claims.** Removing a qualifier, sharpening a
hedge, or adding a transition that asserts a causal relation absent from the
Argument Graph are all defects, and are diffed against the Evidence Matrix before
the edit is accepted.
