# SWOS Prose dogfooding

This directory is for **local empirical testing** of the first `polish` rewrite pipeline.

`corpus/` and `results/` are ignored by Git by default because dogfood material may contain unpublished, internal, or copyrighted prose. Do not remove that protection merely to make examples convenient.

## Setup

Install the optional OpenAI SDK used by the current reference providers:

```bash
python -m pip install openai
```

Supply the API key through your shell environment, or create a local `.env` file and pass it explicitly with `--env-file`. The dogfood command does **not** automatically load `.env` at import time.

PowerShell example:

```powershell
$env:OPENAI_API_KEY = "<your local key>"
python -m swos_prose.cli dogfood `
  --input-dir dogfood/corpus `
  --output-dir dogfood/results `
  --assurance strict
```

Explicit local environment-file example:

```text
OPENAI_API_KEY=<your local key>
# Optional:
# SWOS_PROSE_OPENAI_MODEL=<verifier model override>
# SWOS_PROSE_OPENAI_REWRITE_MODEL=<rewriter model override>
```

Then run:

```bash
python -m swos_prose.cli dogfood \
  --input-dir dogfood/corpus \
  --output-dir dogfood/results \
  --assurance strict \
  --env-file .env
```

Existing process environment variables take precedence over values in `--env-file`.

## Diagnostics and calibration

Pre-generation diagnostics are enabled by default. They may return `NO_CHANGE_RECOMMENDED` before generation only when a deliberately narrow deterministic recogniser has **positive evidence** for a simple already-good prose shape and no reviewed defect/uncertainty signal is present. Absence of a known defect is not enough.

A diagnostics abstention returns the source unchanged and makes zero rewrite-provider and zero semantic-verifier calls. Dogfood records expose this through `diagnostics_before`, `generation_skipped_by_diagnostics`, and the `diagnostics_no_change` skip reason.

Use `--skip-diagnostics` when the purpose of a run is semantic calibration and the rewriter/verifier must be exercised even on prose that diagnostics could otherwise abstain on. This is how the trusted five-case Luna calibration workflow keeps the diagnostics signal separate from the verifier signal.

The first diagnostics slice is intentionally context-blind. If `polish_text` receives neighbouring context directly, early abstention is disabled until context-aware diagnostics exist.

## Corpus shape

Put one reviewable sample in each `.txt` or `.md` file. For the first run, use 5–10 varied paragraphs rather than long documents.

Recommended initial mix:

1. dense technical/scientific prose;
2. humanities or critical prose;
3. a SWOS documentation paragraph;
4. deliberately formulaic or weak machine-generated prose;
5. already-strong human prose.

## Results

The collector writes one JSON record per source file plus `summary.json`.

Each record contains:

- source, candidate, and final text;
- PASS / REPAIR / REVIEW / REJECT status where verification ran;
- `NO_CHANGE_RECOMMENDED` where the source is intentionally preserved without a material rewrite;
- whether the source fallback was used;
- semantic deltas;
- rewrite and verifier token usage when available;
- provider notes/provenance;
- `diagnostics_before` when diagnostics ran, including recommendation, signals, positive evidence, and simple size metrics;
- `generation_skipped_by_diagnostics` so zero-cost abstentions are distinguishable from provider/verifier no-change outcomes;
- empty fields for a manual human-review category and notes.

`preset` and `diagnostics_after` remain `null` because presets and post-rewrite prose diagnostics are not implemented yet. The collector does not fabricate those capabilities.

## Human review taxonomy

After each run, classify every sample manually as one of:

- **safe_improved** — safe and materially better;
- **safe_unnecessary** — safe but the original was preferable;
- **unsafe_caught** — verifier/fallback correctly blocked an unsafe rewrite;
- **unsafe_not_caught** — bad-but-PASS; treat as a priority bug;
- **semantic_ambiguity** — legitimate unresolved meaning or over-conservative verification.

Write the category and short notes into the local JSON result before summarising findings.

## Current scope

Dogfooding currently exercises `mode="polish"` only. It includes the first conservative pre-generation diagnostics/abstention slice. Do not use this harness as evidence that `naturalise`, `clarify`, `tighten`, presets, post-rewrite diagnostics, or repair are implemented.
