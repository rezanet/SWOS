# Data Model: SWOS v1.1 Programme Foundation

## Document record

One repository-relative documentation path maps to exactly one stable document
record. The record contains:

- `id`: immutable kebab-case identifier;
- `path`: normalized repository-relative path;
- `title`: human-readable document title;
- `owner`: accountable team or role;
- `authority`: constitutional, normative, governance, operational, informative
  or historical;
- `status`: draft, active, superseded, deprecated or historical;
- `version_scheme`: semver, date or living;
- `version`: value valid for the selected scheme;
- `canonical_for`: one or more unique authority-domain names;
- `supersedes`: document IDs this record replaces; and
- `superseded_by`: document IDs that replace this record.

Document IDs and paths are unique. Supersession is a reciprocal directed
relationship. An active document cannot have a non-empty `superseded_by` list.
At most one record may be canonical for an authority domain.

## Source input record

An external research file is recorded without its machine-specific path:

- `filename` — supplied file name;
- `sha256` — lowercase 64-character digest;
- `date` — recording date;
- `role` — `research_input`; and
- `derived_canonical_documents` — document IDs that synthesize the input.

## Corpus policy

The corpus discovers Markdown documents at the repository root and in the
declared documentation roots, plus `LICENSE`. It excludes tests, dogfood
outputs, GitHub templates/workflows, generated evidence, Spec Kit templates and
agent-local files. The manifest itself and JSON schemas are machine artifacts,
not document records.

## Release profile record

Release profiles are documented rather than stored in the document manifest:

| Profile | Trigger | Provider credential | Evidence claim |
|---|---|---|---|
| Deterministic PR | pull request / protected push | Never read | Deterministic correctness only |
| Offline release | Explicit local release procedure | Never read | Offline conformance only |
| Live-compatible release | `workflow_dispatch` with exact SHA | Required | Compatibility only for the passed profile |

## Capability state

Capability progress uses an ordered vocabulary: `specified`, `implemented`,
`tested`, `demonstrated`, `certified`. A later state requires evidence beyond
the earlier state and cannot be inferred from it.
