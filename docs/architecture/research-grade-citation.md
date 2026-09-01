# Research Grade citation support and diversity

SWOS Research Grade separates deterministic evidence eligibility from advisory
model judgement. Citation support uses the fixed five-label vocabulary and emits
all probabilities, calibration/model/dataset/ontology identities, canonical
input digest, deterministic checks, and abstention reason. The finalizer accepts
only the core eligibility state; a model label alone cannot admit evidence.

Source diversity is measured over canonical source families actually referenced
by admitted claims. The v2 report covers work family, publisher/owner, venue,
author/institution cluster, geography, language, period, methodology, source
type, access mode, and stance. Each dimension reports metadata evidence state,
unknownness, source-count and claim-exposure concentration, effective categories,
normalized balance, required-strata coverage, and corrective queries. A
versioned geometric composite is diagnostic alongside dimension gates; the v1
provider-count scalar remains readable only for compatibility and never gates v2.

Training, calibration, locked evaluation, human review, source licences, and
benchmark packets are release evidence rather than synthetic examples. This
checkout records unavailable external or human evidence as `NOT_RUN`.
