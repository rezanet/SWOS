# Worked Example - Complete Output Bundle

A deliberately small but **complete** SWOS work item, carried from intake to
release, with every audit-pack artefact present and schema-valid.

The point of this example is not the subject matter. It is that you can open any
artefact and answer the four questions a reviewer must be able to answer without
asking anyone:

1. **What supports this claim?** - `evidence-matrix.json`
2. **Where did it come from and how was it produced?** - `epg.json`
3. **Why was this judgement made?** - `sdl.json`
4. **Who approved the release, and against what?** - `governance-gates.json`,
   `evaluation-result.json`

## The work

**Question:** Does the available evidence support a causal claim that intervention
X improves outcome Y in older adults?

**Discipline:** psychology. **Contribution type:** critique. **Audience:**
researchers. **Classification:** public.

## Why this example ends in a qualified conclusion

The interesting artefact here is not the manuscript. It is the fact that the work
**did not produce the claim it set out to test**.

The evidence supports an association, not a cause. Three things happened as a
result, and all three are visible in the audit pack:

* The Citation Auditor classified the key citation `partially_supports`, not
  `directly_supports` (`citation-audit.json`).
* The Methodologist withheld the causal licence (`reviewer-findings.json`).
* The SDL records the decision to qualify rather than assert, with the
  alternatives considered and the rationale (`sdl.json`, `dec-00000003`).

A system that optimised for prose would have written the confident version. The
audit trail is what makes the cautious version defensible rather than merely
timid.

## Files

| File | Artefact | Schema |
|---|---|---|
| `scholarly-state.json` | Lifecycle history with governance checkpoints | `state/scholarly-state.schema.json` |
| `research-plan.md` | The Rule #3 precondition | - |
| `evidence-matrix.json` | Claim-to-source map with support levels | `evidence-matrix/` |
| `argument-graph.json` | Toulmin structure with rival readings | `argument-graph/` |
| `epg.json` | PROV-compatible provenance bundle | `provenance-graph/` |
| `sdl.json` | Decision ledger | `decision-ledger/` |
| `reviewer-findings.json` | Panel output | `reviewer/` |
| `evaluation-result.json` | Eight-plane gate results | `evaluation/` |
| `governance-gates.json` | Gate records with NIST references | `governance/` |
| `citation-audit.md` | Human-readable citation audit |  - |
| `unsupported-claims.md` | The claims that did not make it | - |
| `uncertainty-statement.md` | Typed uncertainty | - |
| `manuscript.md` | The output itself | - |
| `disclosure.md` | AI-use disclosure | - |

## Rights note

All source metadata in this example is **synthetic or rights-cleared
placeholder**. No copyrighted text is reproduced. This is the same rule the
source-rights gate applies at runtime, applied to the repository itself.
