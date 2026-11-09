# proposal: repair task10 response capture and observability

> status: accepted — the owner accepted this exact 4096-token visible-response
> and langfuse contract on 2026-11-08 and authorized bounded implementation.
> paid provider calls, upload, publication, and continuation of runs `005–015`
> remain separately gated.

## why

the interrupted task10 execution produced four structurally complete, sealed
runs, but `507/512` persisted model responses are empty and `510/512` calls
report exactly `256` output tokens. every empty response hit that ceiling.
adaption sdk `0.19.0` exposed response status, incomplete details, structured
output items, and usage details, but the adapter retained only `output_text`
and aggregate token counts. the generated receipts cannot recover the discarded
diagnostics. the existing langfuse-compatible tracer uses a deprecated client
surface, is absent from `requirements.txt`, has no real-export proof, and is
not connected to dataset-pack model calls.

adaption's documented responses api has no reasoning or thinking-disable
parameter. this change therefore defines enforceable **visible-response mode**
rather than claiming to disable a hidden provider mechanism.

## contract

### 1. visible-response provider call

each task10 provider request must:

- use the exact selected model with `tools=[]`, `tool_choice="none"`,
  `agentic_memory=False`, `store=False`, and no retry or fallback;
- supply a fixed instruction to answer directly in at most 120 visible words;
- allow at most `4096` output tokens. under the existing published rates and
  conservative input reservation, all original `1,920` calls still reserve
  less than the existing 10-credit ceiling;
- use a bounded transport timeout;
- accept a call only when provider status is `completed` and stripped
  `output_text` is nonempty;
- fail closed on incomplete, failed, cancelled, queued, in-progress, empty,
  malformed, or over-limit responses. no failed call is retried.

reasoning items may exist in the provider response. their content is neither
treated as the answer nor exported. if one instrumented probe still consumes
the allowance without visible text, the selected model is rejected for this
experiment and a different model requires a separate owner ruling.

### 2. bounded local diagnostics

the local call record and receipt must preserve only bounded, allowlisted
diagnostics needed to distinguish failure modes:

- response id hash, allowlisted status, and allowlisted incomplete reason;
- output item type counts and message-content type counts;
- visible response character count;
- bounded input, output, total, and provider-reported detail token counts;
- model allowlist result, latency, credit accounting, and categorical error.

raw reasoning, encrypted reasoning content, provider error text, headers,
credentials, and unbounded provider-controlled strings must not persist.
every provider attempt must produce exactly one source-linked event:
`model.call` for an accepted response or `model.call.failed` for a rejected
attempt. both must validate against the committed schema before the event log
is sealed. a failed partial run is sealed as failure evidence, but cannot
produce `run.status=completed`.

### 3. real langfuse tracing

replace the legacy real-client path with the current sdk surface compatible
with the owner's server. one root observation represents a run; each provider
call creates one generation observation under its turn/agent context. export
only:

- anonymous run/call identifiers and local content hashes;
- condition, topology, seed, turn, phase, agent id, and source event type;
- allowlisted response diagnostics, latency, usage, cost, and terminal state;
- code release and schema versions.

do not export raw prompts, completions, reasoning, artifacts, source, command
output, paths, exception text, credentials, or local receipt bodies. apply an
export-stage masking hook as defense in depth. flush explicitly at each run
terminal and batch terminal. tracing failure is recorded locally and stops the
live experiment before another provider call; it never repeats a paid call.

### 4. credentials and external proof

credentials are loaded only from an explicit owner-supplied private file
outside the repository. the loader must refuse symlinks, wrong ownership,
group/world-readable mode, missing public/secret key pair, and invalid base
url. values are never printed, persisted, included in commands, or added to
process-wide environment variables.

the owner directly supplied and accepted the explicit external private-file
contract. that ruling supersedes the intermediate proxy checklist's request
for a repo-relative default: the cli intentionally requires
`--langfuse-credentials`, does not guess a host path, and does not place or
seek secrets inside the repository.

after offline verification and independent exact-head review, external proof
is staged:

1. langfuse authentication check with no provider call;
2. one fictional metadata-only synthetic trace, flushed and read back;
3. one separately owner-authorized adaption diagnostic call with tracing;
4. read back the generation and reconcile it with the local receipt.

none of these steps authorizes runs `005–015`, packaging, upload, publication,
or reuse of runs `001–004` as analytically complete results.

## preserved evidence

runs `001–004` remain immutable structural and failure-behavior specimens.
their emptiness is evidence of the old capture path and must not be repaired,
backfilled, or relabeled. the prior receipt remains an aborted-partial record.

## acceptance evidence

- fake provider responses cover visible completed output, reasoning-only
  completed output, incomplete max-token output, refusal, malformed usage,
  timeout, and provider exception;
- fake langfuse proof covers current-sdk observation nesting, allowlist,
  export-stage masking, explicit flush, exporter failure, and zero-network
  default;
- event schema rejects empty completed responses before sealing and preserves
  one canonical source-linked `model.call.failed` event for rejected attempts;
- trace-off paths remain byte-identical and provider-call counts do not change;
- interruption cannot duplicate a provider call;
- persisted-log seals are verified immediately before manifest/package work;
- full project-owned offline gates pass at the exact candidate head.

## resolved sdk choice

the private credential shape identifies the langfuse cloud endpoint. the
implementation therefore pins `langfuse>=5,<6`; offline verification exercised
the installed `5.2.0` observation, masking, generation, and flush surfaces with
an in-memory exporter and no network.
