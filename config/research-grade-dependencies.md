# SWOS Research Grade optional dependencies

This is the reviewed dependency manifest for build, training, and independent
interchange checks. The hashes are SHA-256 digests of the named PyPI wheel
artifacts downloaded on 2026-09-01. They are supply-chain evidence, not a
request for ordinary CI to install or import every optional package.

| Group | Distribution | Version | License / Licence | Artifact | SHA-256 |
|---|---|---:|---|---|---|
| ontology | rdflib | 7.6.0 | BSD-3-Clause | `rdflib-7.6.0-py3-none-any.whl` | `sha256:30c0a3ebf4c0e09215f066be7246794b6492e054e782d7ac2a34c9f70a15e0dd` |
| ontology | pyshacl | 0.40.1 | Apache-2.0 | `pyshacl-0.40.1-py3-none-any.whl` | `sha256:27dd58c8ddfa103303b4a8c40b2c666332ffc912dbcd3137f7adc7b7bc5e6bda` |
| provenance | prov | 3.1.0 | MIT | `prov-3.1.0-py3-none-any.whl` | `sha256:c70f2785e353bc3366f4711d7a5488380249026498fcf6274c71f783f2773545` |
| training | sentence-transformers | 6.0.1 | Apache-2.0 | `sentence_transformers-6.0.1-py3-none-any.whl` | `sha256:b8888d72c707ba33c63aa30845850702dd5acadf1dd0d051436380bcebe4fd0f` |

The regular `retrieval` extra remains the frozen v1-compatible range. The
Research Grade extras are explicit and pinned so a release workflow can run
with a separately reviewed environment. Ordinary CI uses the standard
library plus the existing runtime dependencies: it performs no model download,
credential read, network inference, paid call, or PROV oracle execution.

Transitive dependencies must be resolved with hashes by the dedicated release
workflow and recorded in its immutable environment manifest. A missing
package, licence statement, or digest is a release blocker rather than a
reason to substitute an unpinned package.
