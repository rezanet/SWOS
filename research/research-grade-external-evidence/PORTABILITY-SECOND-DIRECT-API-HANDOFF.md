# Portability Gap Handoff — Second Direct-API Adapter

Status: IMPLEMENTATION HANDOFF / NOT PASS EVIDENCE  
Baseline authority: `1f5135969f04a104d4a99764f921d1743d22710f`  
Frozen case: `api_provider_changed`  

## Problem statement

The frozen portability matrix requires a genuine second `direct_api` execution whose adapter differs from the `openai_api` baseline. Current main does not expose such an executable path.

Current facts:

- `swos research-write --adapter` accepts only `openai-api`.
- without `--host-bundle`, `research-write` always calls `build_openai_api_broker()`.
- the checked-in direct API capability manifest is `adapters/openai-api/capabilities-v1.json` with `execution_mode=direct_api` and `model_host=OpenAI API`.
- the host-independent architecture already names provider-specific direct adapters such as `anthropic-api` as legitimate thin adapters behind the SWOS capability boundary.
- adapter policy is explicit: adapters translate; they never decide, relax gates, alter schemas, or own scholarly policy.
- `record_portability_acceptance.py` refuses `api_provider_changed` if the execution adapter equals the `openai_api` baseline adapter.

Therefore `api_provider_changed` is presently blocked by a small but real implementation gap rather than by missing human review alone.

## Architectural decision for the implementation builder

Implement the smallest conforming second direct-API transport path. The preferred candidate is `anthropic-api` because the existing architecture already identifies it, but another real provider is acceptable only if it satisfies the frozen matrix without changing scholarly policy.

This is not permission to redesign the broker, portability matrix, scholarly state machine, evidence rules, review policy, or release gates.

## Required implementation surface

### 1. Capability manifest

Add a provider-specific manifest such as:

`adapters/anthropic-api/capabilities-v1.json`

It must use the same `swos.capabilities.v1` contract set and truthfully declare:

- adapter identity;
- provider/model host;
- `execution_mode=direct_api`;
- `api_key_used=true` for a real direct API run;
- capability levels and limitations;
- reviewer-independence limitations no stronger than actually demonstrated.

Do not copy an OpenAI capability claim that the second provider cannot satisfy.

### 2. Stage transport

Add a thin provider transport implementing the same SWOS scholarly capability calls currently implemented by `OpenAIStageProvider`.

Preferred shape:

`swos_runtime/llm_anthropic.py`

or a provider-neutral base plus provider-specific transport if that is less code and does not widen scope.

The adapter must:

- load the same canonical SWOS stage instructions;
- accept the same bounded SWOS request payloads;
- return the same contract-shaped data;
- record provider/model/response/timing/token provenance;
- map provider errors to explicit SWOS failure states;
- never redefine scholarly prompts, stage order, evidence policy, review policy or approval logic.

Provider-specific structured-output mechanics may differ. Normalize them inside the adapter rather than changing SWOS schemas to fit the provider.

### 3. Broker/factory path

Add the minimum factory path needed to construct the second direct provider broker, for example:

`build_anthropic_api_broker()`

The resulting adapter manifest/provenance must identify the actual provider and adapter used.

### 4. CLI selection

Extend `research-write --adapter` so the second direct adapter is selectable, for example:

`--adapter anthropic-api`

Dispatch explicitly to the matching broker factory.

Do not make provider choice implicit from whichever credential happens to exist.

### 5. Retrieval-provider contamination guard

This is the most important implementation detail.

The canonical run must not be advertised as `api_provider_changed` if hidden OpenAI model calls still perform retrieval, reranking, drafting, verification, review, or any other model capability.

The current public retrieval module contains ordinary HTTP/authoritative-source retrieval as well as an optional OpenAI Responses web-search path. For the second-provider acceptance run:

- provider-neutral HTTP/repository/API source retrieval is allowed;
- the selected second provider may provide an explicitly governed retrieval capability if implemented;
- an OpenAI model/web-search call is not allowed to silently remain in the provider-changed case.

Add provenance assertions proving that no OpenAI model call occurred in a second-provider canonical run.

The purpose of this case is provider replacement, not merely replacing the drafting call while retaining OpenAI elsewhere.

### 6. Credential isolation

For the second direct provider run:

- use only the credential required by that provider;
- never persist or log the secret;
- do not require `OPENAI_API_KEY` merely because the baseline implementation did;
- preferably run the acceptance case with `OPENAI_API_KEY` absent so hidden OpenAI dependency becomes a hard failure.

This credential-absence condition is a recommended execution guard for the provider-change proof even if the frozen matrix does not currently list it as a forbidden variable for this case.

## Required tests

Add focused regression tests before claiming the path is ready:

1. **manifest conformance** — second adapter validates against the host/capability contract and declares `direct_api` truthfully;
2. **CLI routing** — `research-write --adapter <second-provider>` builds the second provider broker and never the OpenAI broker;
3. **instruction identity** — both direct providers consume the same canonical SWOS instruction assets/digests for equivalent stages;
4. **schema identity** — second transport returns the same SWOS contract shapes without schema weakening;
5. **governance immutability** — adapter cannot alter scholarly state transitions, approval requirements, support vocabulary, release blockers or stage ordering;
6. **provider provenance** — all model capability events in a provider-changed run identify the actual second provider/model/adapter;
7. **no OpenAI contamination** — with `OPENAI_API_KEY` absent, the second-provider canonical path cannot make an OpenAI model/web-search call;
8. **secret hygiene** — evidence/run artifacts contain no provider secret values;
9. **recorder dependency** — `api_provider_changed` recording still requires a prior real `openai_api` evidence record and refuses the same adapter;
10. **canonical validation** — the resulting run package must pass `tools/validate_autonomous_run.py --canonical` before the recorder can emit PASS.

## Acceptance execution

After implementation and ordinary CI are green:

1. produce a genuine `openai_api` baseline evidence record first;
2. execute the canonical request through the second direct API provider;
3. retain complete execution provenance and run artifacts;
4. run:

```bash
python tools/validate_autonomous_run.py <SECOND_PROVIDER_RUN_DIR> --canonical
```

5. only if that passes, run:

```bash
python tools/record_portability_acceptance.py \
  api_provider_changed \
  <SECOND_PROVIDER_RUN_DIR>
```

6. verify the recorder observed an adapter different from the baseline;
7. keep the generated PASS record absent if any provider identity, provenance or governed outcome is unresolved.

## Explicit non-goals

Do not:

- alter the six-case portability matrix;
- lower the canonical governed-outcome contract;
- add provider-specific scholarly policy;
- call a Claude Code subscription run the direct Anthropic API case;
- call replay a provider-change case;
- hand-author portability evidence;
- claim provider independence if any OpenAI model call remains in the changed-provider run;
- release or deploy as part of this implementation.

## Builder terminal state

The implementation work may end at:

`SECOND_DIRECT_API_PATH_READY_FOR_REAL_PORTABILITY_RUN`

T127 and `api_provider_changed` remain OPEN until a real second-provider execution passes the canonical validator and the official recorder produces the evidence record.