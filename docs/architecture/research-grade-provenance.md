# Research Grade provenance interchange

SWOS EPG v2 is a parallel, explicit `2.0.0` model. It preserves entities,
activities, agents, qualified relations, named bundles, typed/language
literals, SWOS extension assertions, scope, and integrity metadata. Relative
identifiers are rejected by the absolute namespace policy.

The advertised profile is a SWOS PROV-DM/PROV-N/PROV-O round-trip profile with
PROV-JSON Member Submission, JCS (RFC 8785), and RDF Dataset Canonicalization
(RDFC-1.0). PROV-JSON is a W3C Member Submission, not a W3C Recommendation;
SWOS does not claim W3C certification.

The certification tool runs EPG-to-PROV-JSON/PROV-N/PROV-O-TriG and the required
cross-format paths, checks semantic normal forms and extension/literal/bundle
preservation, applies bounded resources, and records stable fingerprints. An
independent ProvToolbox identity and checksummed corpus are mandatory for a
release certificate. Their absence is `NOT_RUN`, never a pass.
