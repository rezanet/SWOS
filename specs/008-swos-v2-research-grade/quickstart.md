# Builder Quickstart: SWOS v2.0 Research Grade

This is a sequencing and verification guide, not permission to merge or deploy.
Build on an isolated branch/worktree from the approved base and preserve unrelated
changes. Do not begin a later gate while a prerequisite is red.

## 1. Establish the exact subject

```powershell
git status --short
git rev-parse HEAD
git merge-base --is-ancestor origin/main HEAD
python --version
python tools/check_spec_kit_artifacts.py
```

Record the base and feature heads. Recompute all exact-head evidence after any
code, data, model, ontology, policy, fixture, or documentation change.

## 2. Create a v2 compatibility shell first

Add parallel `2.0.0` schemas/contracts and explicit version dispatch. Before new
behavior, prove frozen v1.0 artifacts and v1.1 inputs still validate and execute.
Do not edit old `$id` semantics in place.

Run the schema, contract, and compatibility suites specified in `tasks.md`.

## 3. Build shared foundations test-first

In order:

1. canonical JSON/digest and exact evaluation-subject helpers;
2. typed v2 models and error codes;
3. licence/classification/rights and resource-limit policies;
4. release audit-pack manifest/verifier;
5. deterministic fixture adapters that call production paths.

Commit no placeholder pass path. Missing artifacts, unsupported versions, and
optional live dependencies must fail closed or report `NOT_RUN` as contracted.

## 4. Build user stories in dependency order

### US1: cross-project RPM

Implement SQLite migrations/event chain/projection, explicit project registration,
evidence-bound staged writes, governed reads, lifecycle operations, then safe
exchange. Test scope isolation, TOCTOU, crash injection, concurrency, projection
rebuild, deletion semantics, and hostile archives before integration.

### US2: ontologies and critique

Author the core vocabulary/shapes and resolve the enum/pack mismatch. Compile all
pack modules to deterministic JSON. Then bind research planning, claims, critique
criteria, and diversity requirements to stable IRIs and digests. Add human-reviewed
fixtures for every supported discipline.

### US3: citation support and diversity

Implement production interfaces with deterministic fakes first. Build the
licensed, leakage-safe annotation pipeline; train, calibrate, and freeze the real
artifact only after annotation/agreement gates pass. Replace provider-count
diversity with source-family and claim-exposure metrics. Core finalization stays
the only admission authority.

### US4: PROV certification

Create EPG v2, converters, parsers, validation, semantic normal form, and
fingerprints. Pass the complete internal matrix before invoking the pinned
independent oracle. Never advertise a format before all legs certify.

### US5: multimodal/object analysis

Implement object/media/rights/selectors before provider integration. Add bounded
2D analysis through both the deterministic fake and the real opt-in OpenAI
adapter, observation/interpretation separation, cross-modal support, and
discipline critique. Promotion remains default-off until exact-head corpus and
human evidence satisfy every gate.

## 5. Governed command matrix

The builder must keep this matrix current as paths stabilize:

```powershell
python -m unittest discover -s tests/runtime -p 'test_*.py'
python -m unittest discover -s tests/prose -p 'test_*.py'
python tools/validate_schemas.py
python tools/validate_contract_examples.py
python tools/compile_discipline_ontologies.py --manifest discipline-packs/manifest-v2.json --shapes discipline-packs/ontology/swos-discipline-shapes.ttl --out discipline-packs/compiled/v2 --report artifacts/ontology/compile-report.json
python tools/evaluate_citation_classifier.py --model-manifest models/citation-support/current/manifest.json --calibration models/citation-support/current/calibration.json --locked-test benchmark/citation-support/splits/locked-test.jsonl --predictions-out artifacts/citation-support/predictions.jsonl --report-out artifacts/citation-support/report.json
python tools/run_source_diversity_benchmark.py --manifest benchmark/source-diversity/manifest.json
python tools/certify_prov_roundtrip.py --corpus-manifest evals/fixtures/provenance/manifest.json --profile schemas/research-grade/prov-profile.json --formats prov-json prov-n prov-o-trig --oracle-manifest benchmark/provenance/oracle-manifest.json --limits benchmark/provenance/resource-limits.json --artifact-dir artifacts/provenance --certificate-out artifacts/provenance/certificate.json
python tools/run_rpm_benchmark.py --manifest benchmark/rpm/manifest.json
python tools/run_multimodal_evals.py --manifest evals/fixtures/multimodal/manifest.json
python evals/harness/run_evals.py --all-planes --fail-on-gate
python tools/assemble_research_grade_audit_pack.py --verify-only
ruff check .
```

Commands shown for new tools become executable acceptance contracts when their
tasks land. Use the repository's locked environment and existing security,
coverage, portability, and manifest checks. Ordinary CI must remain offline.

## 6. Release-only governed workflows

Run these only from the exact clean release-candidate SHA:

- citation dataset verification, training, calibration, and locked evaluation;
- independent ProvToolbox/conformance certification;
- full 100k-item RPM and large PROV benchmarks;
- live multimodal provider evaluation where credentials and rights permit;
- competent human adjudication and capability-promotion review.

Each workflow uploads immutable raw and summary artifacts and records dependency,
model/oracle, corpus, policy, hardware, and source identities. A missing
credential or unavailable oracle is `NOT_RUN`; it does not produce a pass.

## 7. Evidence and review gate

Before requesting final review:

1. freeze the release candidate head;
2. run all deterministic and release-only required workflows on that head;
3. assemble and verify the audit pack;
4. confirm every requirement and success criterion has an artifact pointer;
5. confirm no unresolved review threads or known blockers are hidden;
6. request independent review against the exact head.

Any change after evidence or review invalidates affected results and the final
review. Rerun and obtain fresh exact-head evidence.

## 8. No-merge checklist

Do not merge when any of the following is true:

- v1 artifacts were silently redefined or compatibility regressed;
- namespace scoping is presented as authenticated multitenancy;
- an RPM API is unscoped, evidence IDs are unresolved, or import can choose its
  destination;
- ontology/shape/pack coverage or deterministic compilation fails;
- trained data, model, calibration, licence, or locked evaluation is missing or
  below threshold;
- a provider/LLM verdict can directly verify a citation;
- diversity improves through duplicates, unknown metadata, or provider renaming;
- PROV conversion loses semantics, lacks constraints validation, or validates
  only against itself;
- multimodal rights, identity, selector, observation, cross-modal, accessibility,
  or promotion evidence is incomplete;
- ordinary CI needs network, credentials, downloads, or paid calls;
- the exact-head audit pack, green CI, independent review, or limitation record
  is incomplete.

## 9. Rollback behavior

- RPM migration/import failure leaves the prior database and chain readable and
  records no partial success.
- Ontology/compiler failure prevents Research Grade planning; it does not fall
  back to an unrelated pack.
- Classifier failure abstains and blocks auto-admission.
- Diversity failure triggers bounded expansion/review or a visible governed
  narrow-corpus exception.
- PROV failure produces a failed certificate and disables the advertised format.
- Multimodal failure reverts the capability to pack-only/default-off and retains
  the evidence for diagnosis.
