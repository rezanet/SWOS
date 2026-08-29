# SWOS Vision

## A scholarly operating system for epistemic control

SWOS exists because the hard problem in serious writing is not producing
grammatical sentences. It is deciding what may be claimed, what supports it,
how strong the support is, what remains uncertain, which interpretation was
chosen, and who is accountable for releasing the result.

The system is therefore an assurance and governance layer beneath scholarly
work. It makes research reasoning inspectable: evidence is acquired before
prose, claims are typed, arguments are explicit, provenance remembers the path
of justification, decisions and dissent remain visible, and release is a
human-accountable act supported by reproducible evidence.

The supplied roadmap and writing-skills files informed this vision as research
input. They are not normative authorities. Normative rules live in the
constitution, frozen contracts, schemas and governance policies; the source
files, hashes and derived canonical documents are recorded in the
[documentation manifest](docs/document-manifest.json).

## The philosophical problem

### Scholarship is epistemic, not merely stylistic

Writing is the visible surface of a chain of judgements. A system that only
optimises fluency can make unsupported reasoning harder to see. SWOS treats a
manuscript as the last expression of a governed research process, not as the
first place where the process begins.

### Fluency is a risk signal

Fluent language can conceal weak retrieval, citation mismatch, overconfident
inference and accidental invention. In SWOS, fluency without commensurate
evidence increases scrutiny. A rough but well-supported statement is safer than
an elegant statement whose support cannot be opened, classified and traced.

### Evidence comes before prose

Before drafting, SWOS establishes the research question, evidence plan,
candidate sources, claim inventory, citation relationships, argument graph,
uncertainty and decision record. The prose is constrained by those artefacts;
it does not manufacture them after the fact.

### Claims and citations are typed support relationships

A citation is not a decorative reference or a URL-shaped confidence token. A
claim has an epistemic status such as observed fact, source-backed claim,
inference, interpretation, hypothesis, speculation or normative judgement. Its
support relationship is separately classified: direct, partial, contextual,
contradictory or failed. Existence, metadata, licence/retraction state,
quotation boundaries and claim support are distinct checks.

### Arguments are structures, not paragraph soup

An argument consists of claims, warrants, backing, objections, rebuttals,
implications and rival readings. SWOS represents those relationships explicitly
so that missing warrants, unsupported leaps and unresolved objections are
detectable. A paragraph can be beautiful and still be structurally incomplete.

### Provenance is the memory of justification

SWOS provenance records where a source, claim, transformation, evaluation and
decision came from and how they relate. It is not merely a log of prompts or a
central store of conversational memory. Provenance lets a reviewer reconstruct
why a statement exists, which evidence changed, which tool acted, and which
person approved the release.

### Uncertainty, dissent, correction and supersession are first-class

Knowledge changes. Sources conflict. Interpretations remain provisional. SWOS
must preserve uncertainty rather than flatten it into confidence, preserve
dissent rather than erase it, record corrections rather than silently mutate
history, and mark supersession rather than pretend that an old statement was
always current. A corrected claim remains auditable as a corrected claim.

### Governance is continuous accountability

Governance is present across Discover, Design, Build, Validate, Release,
Operate, Evolve and Retire. It covers authority, access, retention, source
rights, incident response, review, provenance and release evidence. A final
checkbox cannot repair an uncontrolled research process.

### Humans remain responsible

SWOS can organise evidence, expose gaps, compare interpretations and prepare a
reviewable manuscript. It cannot inherit the scholar's responsibility for
judgement. Human approval is required for release, and separation of duties
keeps acquisition, synthesis, verification, governance review and approval
meaningfully distinct.

## Portability and restraint

SWOS is host-independent, model-independent and retrieval-independent. Its
contracts, schemas, events and evidence artefacts are defined without assuming
one provider, one subscription, one user interface or one memory system. A
provider adapter may be replaced without changing what counts as support or
approval.

The reference runtime is deliberately minimal. It proves a portable, local,
file-backed path through the contracts and gates. Minimalism is a safety
property: a smaller surface is easier to inspect, reproduce, secure and replace.

SWOS is open-source scholarly infrastructure. It should be usable by researchers,
students, engineers, artists, historians, philosophers, policy teams and
reviewers without making a hosted vendor the source of truth. The project is
built in this sequence:

**Proof → Portability → Ecosystem → Standardisation**

Proof means one complete governed path. Portability means the same obligations
survive host, model and retriever changes. Ecosystem means adapters, packs and
tools can participate without weakening the core. Standardisation means the
contracts and evidence conventions are stable enough for wider scholarly use.

## What SWOS refuses to become

SWOS is not:

- a chatbot whose conversational confidence substitutes for evidence;
- a giant prompt with architecture hidden in prose;
- a prose stylist that improves fluency while ignoring truth conditions;
- a SaaS platform or enterprise dashboard that makes hosting central to trust;
- an autonomous publisher that removes human responsibility;
- a central memory service that turns unsupported reflection into fact; or
- an enterprise identity, tenancy and service-management platform.

Those capabilities may exist around SWOS as optional host or organisational
systems, but they are not the scholarly assurance core. If a requirement can be
solved by a contract, schema, evidence record, deterministic validator or
human-governance process, it belongs there rather than in a larger prompt or a
new agent.

## Version tracks

The tracks are intentionally separate:

| Track | Current target | Meaning |
|---|---:|---|
| Core/specification | `1.0.0` | Frozen contracts, schemas and governance baseline |
| Reference runtime | `v1.1` | Minimal working implementation of the governed path |
| Research Grade | `v2.0` | Measured cross-project memory, classifiers, multimodal and deeper research capabilities |

The runtime track can advance without silently changing the Core/specification
track. A Research Grade experiment does not become a Core guarantee until it has
its own reviewed contract, evidence and versioned decision.

## The promise

For a completed governed work, a reviewer should be able to open the audit pack
and answer four questions without asking the implementation team:

1. What supports this claim?
2. Where did the evidence and transformation come from?
3. Why was this judgement made, including uncertainty and dissent?
4. Who approved the release, against which exact head and evidence?

Everything else is subordinate to making those answers truthful, inspectable and
reproducible.
