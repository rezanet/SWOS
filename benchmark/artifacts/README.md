# Frozen benchmark evidence

`raw-evidence-v0.2/` preserves the exact 237,086-byte `baseline.json` emitted by
GitHub Actions run `32450085166`.

Because this connector writes repository text objects but not binary files directly,
the raw JSON is xz-compressed and its base64 transport is split into five immutable
Git blobs. `raw-evidence-v0.2/manifest.json` records every part SHA and the
reconstruction command.

Provenance:

- workflow run: `32450085166`
- artifact ID: `9435636550`
- evidence source commit: `7637a487a93266e30fcbefbc40ad2266fec600b8`
- raw report SHA-256: `1287335a681acd5890588bd3f9d3aa6e61ccac6d35aa8de9b65b840ef5597c9a`
- compressed raw report SHA-256: `c994d4eaede343b31391a4a284a08784c3c10e52cd0f1677cf8de0be6d62aed9`
- original Actions artifact ZIP SHA-256: `c8347bb7578923664972ec6682e98303931ed4593497297f0a169520bc243202`

Reconstruct from inside `raw-evidence-v0.2/`:

```bash
cat part-*.b64 | base64 -d > baseline.json.xz
sha256sum baseline.json.xz
xz -dc baseline.json.xz > baseline.json
sha256sum baseline.json
```

The final two digests must match the compressed and raw report SHA-256 values above.
Do not replace frozen evidence in place; a new live campaign requires a new
versioned evidence directory.
