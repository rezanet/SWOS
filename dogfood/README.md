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
- whether the source fallback was used;
- semantic deltas;
- rewrite and verifier token usage when available;
- provider notes/provenance;
- empty fields for a manual human-review category and notes.

`preset`, `diagnostics_before`, and `diagnostics_after` are currently `null` because presets and prose diagnostics are not implemented yet. The collector does not fabricate those capabilities.

## Human review taxonomy

After each run, classify every sample manually as one of:

- **safe_improved** — safe and materially better;
- **safe_unnecessary** — safe but the original was preferable;
- **unsafe_caught** — verifier/fallback correctly blocked an unsafe rewrite;
- **unsafe_not_caught** — bad-but-PASS; treat as a priority bug;
- **semantic_ambiguity** — legitimate unresolved meaning or over-conservative verification.

Write the category and short notes into the local JSON result before summarising findings.

## Current scope

Dogfooding currently exercises `mode="polish"` only. Do not use this harness as evidence that `naturalise`, `clarify`, `tighten`, presets, diagnostics, or repair are implemented.
