# Data Model: SWOS v1.1 Public Proof and Release

## PublicProofProject

- `project_version`, `project_id`, `topic`, `requested_length`
- `source_snapshots[]`
- `claims[]` with source, exact quote, stance and rationale
- `known_limitations[]`

## PublicSourceSnapshot

- stable `source_id`, title, public URL, publisher, document version, access date
- rights/access metadata, exact snapshot text and `sha256`
- refresh metadata is informative; the checked-in digest is execution authority

## ProofResult

- proof format and project identity
- distinct runtime `run_id` and work identity
- source manifest digest, finalized status, article digest
- normalized evidence and argument summaries
- eight plane names/results and semantic `proof_fingerprint`

## ReproductionReport

- primary and independent proof paths/digests
- fingerprint comparison and governed-outcome comparison
- `pass` or `fail` plus explicit reasons

## ReleaseCandidateManifest

- exact selected commit and repository identity
- proof, approval, SBOM, provenance, conformance and limitation artifacts
- checksum inventory identity and unsigned/signed state

## BuildProvenance

- builder name/version, selected commit, source-tree cleanliness
- operating system, architecture, Python version
- committed input paths and SHA-256 digests
- output artifact identities and build timestamp supplied by caller

## ConformanceReport

- profile name, status (`passed`, `failed`, `not_claimed`)
- evidence references and limitations
- aggregate release recommendation, which remains blocked without approval/signature

## SignatureTrustPolicy

- fixed namespace `swos-release`
- requested principal and allowed-signers file
- checksum/signature paths and verification outcome
