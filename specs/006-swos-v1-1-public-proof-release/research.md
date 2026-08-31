# Research: SWOS v1.1 Public Proof and Release

> **Historical decision:** The release-signing design below is superseded by
> the simpler source-release record in `specs/007-simple-release-record/`.

## R1 — Public corpus

Use three official NIST AI RMF resources: the AI RMF 1.0 publication record, the
AI RMF Core, and the AI RMF Playbook FAQ. They are primary public sources with
stable institutional identity. Store bounded exact snapshots, upstream URLs,
document/version labels, access date and SHA-256. Treat upstream refresh as a
manual compatibility check because NIST states the framework/playbook evolve.

## R2 — Reproduction semantics

Runtime IDs and timestamps are intentionally unique. Byte-for-byte directory
comparison would be false assurance. Compare a canonical semantic fingerprint of
source snapshots, status, article digest, evidence relationships, argument shape
and eight-plane outcomes while retaining unique run IDs as provenance.

## R3 — SBOM

Generate CycloneDX JSON from `pyproject.toml` direct dependencies and the complete
committed development lock. Mark the dependency source for every component; do
not query a package service or infer uncommitted transitive metadata.

## R4 — Signing

Use OpenSSH signatures because `ssh-keygen -Y sign/verify` is cross-platform,
already available with Git/OpenSSH, supports explicit namespaces and requires no
new Python crypto dependency. The signer supplies the private key externally;
the verifier receives an explicit allowed-signers file and principal. Test keys
exist only in temporary test directories.

## R5 — Profiles and claims

Deterministic PR and offline public-proof profiles may pass from local evidence.
Portability remains definitions-only unless a release gate passed. Live-provider
profiles remain unclaimed without manual evidence. Conformance generation is
therefore an evidence compiler, not a claim generator.

## R6 — Human boundary

Feature `005` approval-pack and SDL-compatible human decisions remain the only
release approval authority. A cryptographic signature proves possession of a
trusted key over exact bytes; it does not prove that governance review occurred.
