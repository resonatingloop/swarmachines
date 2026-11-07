# control plane / agree, prove, connect

status: accepted

owner: colette · local implementation: asterion · peer interface: pug

## owner view

- change: make one delegated task produce a persisted acknowledgment and result receipt, then exercise a bounded adaption investigator.
- before: observer-only board; work handoffs are prose without a common executable local envelope.
- after: explicit task packet, atomic local claim, advisory result and duplicate-safe replay under a persistent trial budget.
- authority: owner approved the control-plane proposal, then “agree and prove, then connect”; after pausing, explicitly approved the proposed 1-credit / four-request / one-worker / no-retry trial on 2026-11-07. no unrestricted use of the reported 1500-credit balance is inferred.

## scope and invariants

one local queue and read-only single-generation investigator. use explicit,
selected inline source; preserve ids, revision, hashes, timestamps, execution
mode and provider token usage. duplicate delivery must not produce duplicate
execution. reserve before calling; retain the reservation on failure. never
convert model advice into a review verdict or executable instruction.

out: remote deployment, automatic scheduling, queue migration, shell/file-edit
tools, experimental swarm changes, model training, automatic retry/recovery,
account-wide budget claims and source-truth claims from hashes alone.

## peer agreement

pug accepted a goal/context/deliverable mapping with a canonical JSON hash,
`schema_version: v1`, and UTC `emitted_at` fields. their transport has neither
idempotency nor credit metering; the local queue owns those boundaries.
[protocol and limits](../control_plane/DELEGATION.md) records the exact producer
scope. peer agreement is observed; remote round-trip execution is not implied.

## implementation sequence

1. persist assignment and acknowledgment transactionally; enforce single slot.
2. prove duplicate replay, conflicts, interrupted-worker holds and persistent caps offline.
3. execute one explicitly bounded paid investigator packet through the same path.
4. inspect its advisory output independently; replay the packet without a second call.
5. publish code for independent review; preserve local packet/result state privately.

## change shape

| dimension | changed? | source of truth | proof |
|---|---|---|---|
| user-visible behavior | yes | explicit CLI metadata and receipt | local round trip |
| persisted state or schema | yes | private SQLite jobs/budget | restart and immutability tests |
| external or provider-visible behavior | yes | fixed adaption generation | SDK-boundary tests and bounded live proof |
| identifiers, secrets or privacy | yes | hash-bound packet; env-only key | private state, sanitized errors, no key in packet |
| lifecycle or terminal states | yes | running/completed/failed | duplicate/crash/conflict tests |
| setup, operation or recovery | yes | delegation operations | no automatic reset/retry |
| normative contract or decision | yes | accepted slice and peer mapping | explicit scope limitations |
| cross-repository dependency | no | same repository, local worker | no peer host mutation |

## acceptance and validation

run `python3 -m unittest control_plane.test_delegation -v` and scoped ruff.
a valid offline assignment must persist its acknowledgment before execution;
repeating it returns the same receipt. concurrent claims cannot bypass the
single slot. failures retain their budget reservation; a fifth live claim is
blocked after four, including across restart. missing usage is unknown.

live acceptance requires one completed provider response with a matching packet
and result hash; source/model text remains untrusted and advisory. human review
of the finding is separate from transport success. no deployment or merge
acceptance is inferred from this proof.

## review surface

[change atlas](delegation-review/index.html) projects this bounded slice.
the protocol is described directly in operations; no additional speculative
dispatch visualization is introduced.
