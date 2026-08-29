# Requirements Checklist: SWOS v1.1 Retrieval and Citation Assurance

- [x] FR-001 explicit cross-encoder and score provenance are implemented.
- [x] FR-002 the reference adapter uses the dedicated rerank binding.
- [x] FR-003 citation metadata is normalized and tested.
- [x] FR-004 retraction checks are source-owned and fail closed.
- [x] FR-005 licence checks are source-owned and fail closed.
- [x] FR-006 quotation verification remains deterministic.
- [x] FR-007 all frozen support values are validated and only direct support is admitted.
- [x] FR-008 audit artifacts contain complete assurance evidence.
- [x] FR-009 CLI coverage is deterministic and offline.
- [x] NFR-001 unsafe and malformed states fail closed.
- [x] NFR-002 cross-encoder dependencies are optional and lazily imported.
- [x] NFR-003 ordinary checks make no provider calls.
- [x] NFR-004 `1.0.0`, `v1.1` and `v2.0` remain consistent.
- [x] NFR-005 frozen schema validation passes without contract drift.
