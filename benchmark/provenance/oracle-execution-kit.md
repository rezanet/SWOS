# Independent PROV Oracle Execution Kit

Status: `PREPARATION_ONLY / INDEPENDENT_ORACLE_EXECUTION_REQUIRED`
Feature: `specs/008-swos-v2-research-grade`
Assessed source head: `1f5135969f04a104d4a99764f921d1743d22710f`

This kit is a handoff for the exact independent ProvToolbox execution required by T094. It is not an oracle manifest, certificate, benchmark result, approval, or release artifact. It deliberately leaves the external tool version, licence evidence, artifact URI, artifact digest, and execution result unset. Do not replace the independent oracle with a SWOS converter or a fake/test provider.

## External maintainer inputs

The maintainer or steward must supply all of the following from an approved, permitted distribution:

| Field | Required value | Current value |
| --- | --- | --- |
| Implementation | ProvToolbox | `ProvToolbox` is declared; independent identity is not verified |
| Version | Exact immutable release/version | `UNSET_EXTERNAL` |
| Licence | Exact licence and approval evidence | `UNSET_EXTERNAL` |
| Artifact | Relative local path below `benchmark/provenance/` | `UNSET_EXTERNAL` |
| Artifact SHA-256 | Lowercase 64-character digest of the exact artifact | `UNSET_EXTERNAL` |
| Command | Non-empty argv list containing every required placeholder | `UNSET_EXTERNAL` |
| Approval | Named maintainer/steward disposition in an immutable external record | `UNSET_EXTERNAL` |

The accepted `benchmark/provenance/oracle-manifest.json` must contain `status` in an accepted state, a relative local `artifact_uri`, a present artifact whose SHA-256 equals `artifact_sha256`, and a command containing all five placeholders: `{artifact}`, `{input}`, `{profile}`, `{formats}`, and `{output}`. Absolute paths, URLs, missing digests, shell commands, and unresolved placeholders are rejected by the certifier.

## Exact permitted inputs

The execution must use the permitted cases in `benchmark/provenance/manifest.json`, not an invented EPG. Before execution, every case must have:

- a unique case ID;
- one of the required categories `valid`, `invalid`, `large`, `adversarial`, or `hostile_blank_node`;
- a relative EPG path below the manifest directory;
- a lowercase SHA-256 digest matching the exact EPG bytes; and
- the permission/right basis required by the fixture approval packet.

The fixed profile and format matrix are:

```text
profile: schemas/research-grade/prov-profile.json
profile_id: swos.prov-dm-round-trip.v2
formats: prov-json prov-n prov-o-trig
limits: benchmark/provenance/resource-limits.json
```

The currently committed corpus manifest has no cases and is `NOT_RUN`; execution must stop until T093 supplies the approved corpus. The currently declared resource limits are 5,000,000 bytes, 100,000 statements, 1,000,000 literal characters, depth 64, and 60 seconds, with required 1k/10k/100k and hostile blank-node performance coverage. These declarations are not evidence that the limits have been met.

## Exact invocation

The repository workflow is the authoritative invocation boundary:

```text
python tools/certify_prov_roundtrip.py --epg "${{ inputs.epg }}" --profile schemas/research-grade/prov-profile.json --formats prov-json prov-n prov-o-trig --oracle-manifest "${{ inputs.oracle }}" --limits benchmark/provenance/resource-limits.json --artifact-dir artifacts/research-grade/provenance --certificate-out artifacts/research-grade/provenance/roundtrip-certificate.json
```

Run it through `.github/workflows/prov-certification.yml` with the approved oracle manifest and an approved EPG, or use the corpus mode for the frozen fixture set:

```text
python tools/certify_prov_roundtrip.py --corpus-manifest benchmark/provenance/manifest.json --profile schemas/research-grade/prov-profile.json --formats prov-json prov-n prov-o-trig --oracle-manifest benchmark/provenance/oracle-manifest.json --limits benchmark/provenance/resource-limits.json --artifact-dir <artifact-directory> --certificate-out <certificate.json>
```

The artifact directory and certificate path must be new for each run. The certifier refuses to overwrite an existing oracle output or certificate, and it executes the command without a shell in a restricted environment.

## Required oracle output

For each exact input, the oracle command must create the output path supplied through `{output}` as a JSON object with at least:

```json
{
  "status": "pass",
  "input_digest": "<the certifier-computed exact input digest>",
  "profile": "swos.prov-dm-round-trip.v2",
  "formats": ["prov-json", "prov-n", "prov-o-trig"]
}
```

The values above are a schema requirement, not values to copy into an evidence file. The actual input digest, output, command, stdout, stderr, and artifact hashes must be captured from the execution. The result is accepted only when the status is accepted, the input digest matches the exact input, the profile matches the fixed profile, and the format list matches the fixed order.

The resulting certificate must contain `status: certified`, the profile, source and input digests, the requested paths, one certified leg per case, the oracle identity and execution records, the declared limits, and no unresolved limitation. Each oracle execution record must preserve the exit code and SHA-256 digests for the expanded command, stdout, stderr, and output file.

## Verification and hash binding

The external executor must retain the following immutable record set with the workflow run:

1. The exact `benchmark/provenance/oracle-manifest.json` and its digest.
2. The approved oracle artifact, its licence record, relative path, and lowercase SHA-256 digest.
3. The exact `benchmark/provenance/manifest.json` and digest.
4. Every case EPG path, category, byte digest, and certifier-computed input digest.
5. The exact profile file, profile ID, format order, and resource-limit manifest/digest.
6. The expanded command digest, exit code, stdout digest, stderr digest, and output digest for each case.
7. The final certificate digest and immutable workflow run identity.

Verify the local artifact digest before dispatch with the platform's native file-hash command (for example, `Get-FileHash -Algorithm SHA256 benchmark/provenance/<approved-oracle-artifact>` in PowerShell). Then run the repository command above and inspect the generated certificate with the schema and provenance tests. A successful local invocation alone is insufficient: T094 requires the exact independent oracle and its execution to be recorded in `.github/workflows/prov-certification.yml` evidence.

## Stop conditions

Stop and leave the task `NOT_RUN` if the artifact is not independently approved, its licence or digest is missing, any required corpus case is absent or unpermitted, a placeholder remains unresolved, the oracle output is not bound to the exact input/profile/formats, a resource limit is exceeded, or the hosted workflow result is unavailable. No synthetic output, SWOS converter output, or manually authored certificate may be promoted to evidence.
