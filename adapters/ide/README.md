# IDE Agent Adapter

For agents embedded in an editor. Partial support: IDE contexts are
workspace-scoped and generally lack durable provenance storage.

## Bindings

| IDE capability | SWOS use |
|---|---|
| Workspace skill discovery | Loads SWOS from `.agents/skills/` or `.claude/skills/` in the repo |
| File-watch triggers | Suggests the citation auditor when a bibliography changes |
| Editor context injection | Supplies the current section as drafting context - **read-only** |
| Diagnostics panel | Surfaces unsupported claims and open reviewer findings inline |
| Quick fix | "Mark as unsupported", "add to counter-evidence list", "split compound claim" |

## Constraint

Without a durable provenance store, an IDE deployment **cannot produce an audit
pack** and therefore cannot release. This is declared, not hidden:
`work_classes_permitted` excludes any class requiring release, and `swos release`
is unavailable.

Use IDE mode for drafting assistance against an already-verified Evidence Matrix,
and run release from the CLI adapter.
