# T093/T094 ProvToolbox Oracle Candidate — 2.2.3

Status: CANDIDATE / NOT APPROVED / NOT EXECUTED
Baseline: `1f5135969f04a104d4a99764f921d1743d22710f`
Verified: 2026-09-03

## Candidate identity

Project: ProvToolbox
Upstream repository: https://github.com/lucmoreau/ProvToolbox
Candidate tag: `ProvToolbox-2.2.3`
Annotated tag object: `37e37913f815689d0f4f2eaba55537dcd5b3a9f0`
Tagged commit: `aef0816c2a277958774fac88cf0076248e7065cc`
Tag date: 2026-03-16

Maven coordinate for the command-line converter:

`org.openprovenance.prov:provconvert:2.2.3`

Maven Central describes `provconvert` as a command-line tool for manipulating PROV representations.

## Important correction to earlier research

Earlier research recorded GitHub's `releases/latest` result as 2.2.2. That is not sufficient authority for the current oracle version: the upstream repository has a `ProvToolbox-2.2.3` tag and Maven Central publishes `provconvert:2.2.3` dated 2026-03-16.

Therefore 2.2.3 is now the preferred oracle candidate for maintainer/steward review, unless the frozen workflow has a justified compatibility reason to pin an older version.

Do not silently keep 2.2.2 merely because GitHub's release UI metadata lags Maven/tag state.

## Licence

ProvToolbox uses an MIT-style licence permitting use, copying, modification and distribution subject to preservation of the copyright/permission notice.

Before T094 completion, preserve the exact licence file from the chosen tag and compute its SHA-256 together with the executable artifact.

## W3C fixture licensing

W3C publishes two test-suite licence routes:

- 3-clause BSD route: tests may be copied and modified for software development/testing, but modified tests must not be used to make W3C performance/conformance claims;
- W3C test-suite licence: unmodified tests may be used where specification-performance claims are made; modification is not permitted under this route.

Operational rule for SWOS:

- use the BSD route for copied/mutated/adversarial development fixtures when the source test is covered by that dual-licensing policy;
- retain all required notices;
- never call modified cases authoritative W3C conformance tests;
- use unchanged authoritative tests only where their exact licence permits the intended performance/conformance claim;
- keep SWOS-original adversarial/resource-limit fixtures clearly identified as SWOS fixtures.

Authoritative W3C references:

- https://www.w3.org/copyright/test-suites-licenses/
- https://www.w3.org/copyright/3-clause-bsd-license-2008/

## Remaining work before T094 can pass

1. choose the exact executable distribution strategy (Maven-resolved artifact/dependency set or approved packaged archive);
2. acquire the exact artifact in the execution environment;
3. compute SHA-256 over the exact executable/package bytes;
4. retain licence text and licence SHA-256;
5. record Java/runtime identity;
6. freeze the exact oracle invocation command accepted by `.github/workflows/prov-certification.yml`;
7. obtain the required maintainer/steward approval bound to these identities;
8. execute the oracle externally on the frozen permitted corpus;
9. retain immutable workflow/certificate/input/output hashes.

Until those steps happen, this file is only a verified candidate record. T094 remains OPEN.