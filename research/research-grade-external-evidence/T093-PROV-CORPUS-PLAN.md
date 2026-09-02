# T093–T095 PROV Corpus / Oracle / Performance Plan

Status: RESEARCH/PREPARATION ONLY
Baseline: `1f5135969f04a104d4a99764f921d1743d22710f`

## Goal

Prepare permitted, checksummed PROV fixtures and the independently pinned oracle path without claiming external execution has occurred.

## Standards basis

- PROV overview: https://www.w3.org/TR/prov-overview/
- PROV-N: https://www.w3.org/TR/prov-n/
- PROV-CONSTRAINTS: https://www.w3.org/TR/prov-constraints/
- PROV-JSON Member Submission: https://www.w3.org/submissions/prov-json/
- W3C implementation report: https://www.w3.org/TR/prov-implementations/

The W3C implementation report records 280 PROV-CONSTRAINTS test cases. These can be useful seed material, but each actual source fixture must have a verified redistribution/modification licence before admission.

W3C test-suite licensing guidance: https://www.w3.org/copyright/test-suites-licenses/

Use unchanged upstream tests when the applicable licence permits copying but not modification. Use a 3-clause BSD/software-licensed source or SWOS-original fixture when mutation/adversarial modification is required. Never relabel a modified W3C test as an authoritative W3C conformance test.

## T093 candidate fixture strata

Build a manifest with source/right/digest records for:

### Valid
- minimal entity/activity/agent cases;
- generation/use/derivation/association/delegation;
- named bundles;
- typed literals;
- language-tagged literals;
- qualified relations;
- deterministic statement IDs;
- extension namespace preservation;
- nested/cross-bundle references allowed by the profile.

### Invalid
- malformed syntax per advertised serialization;
- invalid relation typing;
- missing required relation endpoints;
- invalid bundle membership/reference;
- impossible temporal/order constraints;
- duplicate/conflicting identifiers where prohibited;
- unsupported fields that must fail rather than disappear.

### Round-trip stress
- PROV-JSON ↔ PROV-N;
- PROV-N ↔ PROV-O/TriG;
- PROV-JSON ↔ PROV-O/TriG;
- complete multi-leg advertised matrix;
- second-round fingerprint stability;
- extension assertion multiset preservation;
- named-bundle correspondence.

### Canonicalization/adversarial
- blank-node heavy graphs;
- semantically equal RDF datasets with different prefix/order/blank-node labels;
- deeply nested but bounded extension structures;
- duplicate namespace aliases;
- long literal/Unicode/language-tag cases;
- intentionally expensive shapes that should hit `resource_limit` rather than pass or hang.

## Oracle recommendation

Upstream: https://github.com/lucmoreau/ProvToolbox

Current GitHub release research found `ProvToolbox-2.2.2`. The tag's `license.txt` grants MIT-style permission to use/copy/modify/distribute with the copyright/permission notice retained.

T094 should not freeze only a version string. Pin:

- exact tag/release;
- exact executable artifact/JAR or approved archive;
- Maven coordinate if used;
- artifact SHA-256;
- licence text + licence digest;
- Java/runtime requirement;
- exact invocation command;
- expected output/certificate format;
- maintainer/steward approval bound to these identities.

The independent oracle cannot be SWOS's own converter.

## T095 performance/resource corpus

Prepare deterministic 1k and 10k assertion cases plus hostile blank-node/canonicalization cases.

Every case must record:

- generator version/digest;
- generator seed/input parameters;
- resulting fixture SHA-256;
- assertion count;
- format/profile;
- expected status;
- CPU limit;
- memory limit;
- wall-clock limit;
- runner identity in actual execution evidence.

Do not choose limits after observing benchmark results. Limits are inputs to the release benchmark.

## Human/external boundary

Research/preparation can construct permitted fixtures and the oracle manifest candidate. T094 remains OPEN until the exact approved external ProvToolbox artifact is actually executed through the frozen workflow and immutable output is retained. T095 remains OPEN until the real performance/resource corpus and measurements satisfy its acceptance criteria.