# Tasks: SWOS v1.1 Retrieval and Citation Assurance

## Cross-encoder path

- [x] T001 [US1] Add failing score/order/provenance tests in `tests/runtime/test_reranking.py`.
- [x] T002 [US1] Implement optional injectable cross-encoder in `swos_runtime/reranking.py`.
- [x] T003 [US1] Route broker and adapter composition through `swos_runtime/broker.py` and `swos_runtime/adapter_factory.py`.

## Citation assurance

- [x] T004 [US2] Add failing metadata/retraction/licence tests in `tests/runtime/test_citation_assurance.py`.
- [x] T005 [US2] Add normalized assurance fields in `swos_runtime/models.py`.
- [x] T006 [US2] Parse OpenAlex/Crossref assurance evidence in `swos_runtime/retrieval.py`.
- [x] T007 [US2] Enforce assurance, quotation and support admission in `swos_runtime/finalizer.py` and `swos_runtime/work_orders.py`.
- [x] T008 [US2] Update deterministic fixtures in `tests/runtime/test_runtime.py` and `tests/runtime/test_finalizer.py`.

## Operator and governance gates

- [x] T009 [US3] Add offline command coverage in `tests/runtime/test_cli.py`.
- [x] T010 [US3] Add this feature's authority records in `docs/document-manifest.json`.
- [x] T011 [US3] Run focused, runtime, Spec Kit, manifest, schema, governance, portability and Ruff gates from `specs/003-swos-v1-1-retrieval-citation-assurance/spec.md`.
