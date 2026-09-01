# Research Grade programme memory boundaries

Research Grade RPM is a local SQLite implementation of a logical namespace,
programme, and project scope. The namespace is an operator-supplied partition;
it is not authenticated identity, RBAC, tenant isolation, or a hosted memory
service. Every read and write carries all three scope identifiers and project
bindings are explicit.

The event chain is append-only and projections are rebuildable. Corrections,
supersessions, contradictions, expiry, retirement, unbinding, and programme
closure preserve event history and release evidence. Normal reads exclude
expired, deleted, corrected, superseded, and contradicted items; exceptional
reads require a visible governance mode and an EPG-linked receipt.

Deletion is logical deletion inside the database. This implementation makes no
claim about SQLite pages, filesystem snapshots, backups, WAL files, or physical
media erasure. Operators must handle backup retention, access control, and
recovery separately. A failed transaction is rolled back atomically, while
crash recovery and corruption detection remain explicit verification duties.

Exchange bundles are inspected before an explicit destination commit. Archive
paths, checksums, event-chain integrity, classification ceilings, rights
exclusions, and ID/digest collisions are checked before mutation. Import never
chooses its destination and same-ID/different-digest data is rejected.
