# Research: SWOS v1.1 Simple Release Record

## Decision

Use one human-owned JSON release record for the current source-release threat
model. Keep exact commit binding, deterministic tests, provider-free public
proof, independent reproduction, source/citation hashes, checksums, SBOM,
provenance, conformance and limitations. Do not require detached signatures or
an allowed-signers trust policy.

## Rationale

SWOS is a public repository with one maintainer and no package-distribution
surface. A detached signature would establish possession of a key, but it
would not improve the scholarly evidence, source provenance or reproducibility
that the candidate already verifies. The previous approval pack, decision
ledger and signature policy introduced multiple files and role assumptions
without a current operational need. A single readable record is easier for the
owner and an independent reviewer to inspect, while exact SHA and SHA-256
bindings preserve protection against accidental or unnoticed substitution.

The record is not an automated approval: an identified maintainer supplies the
decision, date and rationale after reviewing evidence. The verifier checks that
statement; it does not infer approval from a runtime `APPROVED` status.

## Alternatives considered

1. **Retain the existing approval pack and mandatory OpenSSH trust policy**:
   rejected as disproportionate for a sole-maintainer source repository and
   unnecessarily complex for the current distribution model.
2. **Remove approval entirely**: rejected because a release still needs a
   visible owner decision and rationale.
3. **Use a hosted release service or identity provider**: rejected because it
   would introduce hidden state and violate host independence.
4. **One exact-SHA record plus hashed evidence**: selected because it preserves
   the useful controls with the smallest review surface.

## Future option

If SWOS later distributes packages or gains multiple maintainers, package
signing may be added as an optional outer distribution layer. It must not be
retroactively required for the current source-release contract.
