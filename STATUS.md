# swarmachines / status

> continuity role: operational checkpoint
> status: formal protocol accepted; integrated runtime readiness pending
> last verified: 2026-11-08 (master tip c5899d8 via pr #24: read-only worker receipts projection; verifier clear 48/48 and sast clear)
> owns: exercised state, active work, gaps, and the next useful action
> update when: a meaningful stopping point changes these facts; replace this checkpoint in place

## verified checkpoint

merge ledger (2026-11-07 23:25z to 2026-11-08 00:52z): master tip is c5899d8
(pr #24: read-only worker receipts projection; verifier clear 48/48 and sast
clear). this window also merged pr #16 (331a65c: viewer evidence escaping
chain, suite 127/127), pr #20 (0d0aee8: control-plane observer board), pr #21
(46d84a5: prior checkpoint refresh), pr #22 (523ee5d: bounded local delegation
and investigator trial), pr #23 (984448a: smoke outcome/accounting fix) and
pr #25 (6bbcf4d: trial-narrative correction). open work: pr #6's fix round
(freight-world integration, sast findings and rebase fold) is stalled on an
AGENTS.md protected-file owner approval, and draft pr #26 (ecc948d, spec010
task-submission workflow) is held for owner review with no merge request and
zero provider calls; the delegation slice below carries a post-merge sast redo
tracked as task t-011.

receipt-board slice: owner accepted [spec009](specs/009-worker-receipt-board.md)
on 2026-11-08. optional read-only worker projection implemented; snapshot v2
preserves v1 rendering. 48 offline tests pass, scoped ruff passes, and browser
checks cover 1440/720/320 reflow, keyboard disclosure, no external requests and
empty storage. real private capture shows four live attempts (two completed,
two failed), one separate offline proof, 0.4 credits reserved and a known-usage
subtotal of 0.0016241 credits across 3/4 live attempts. actual billing unknown.
source queue hashes/sizes and directory inventory stayed unchanged. no provider
calls. WAL sources are refused rather than risking sidecar writes. pr #24
merged as master tip c5899d8 after its verifier (48/48) and sast reviews
cleared.

smoke outcome correction: failures in calls 2–4 now produce aggregate `error`
and CLI exit 1; failed call 1 counts its attempted invocation. five offline
regression tests cover outcomes, counting, exit codes and SDK-free blocked
behavior. no provider calls in this change. pr #23 merged as 984448a;
provider retry/configuration behavior remains unchanged.

local delegation slice (2026-11-07): accepted spec008 and owner-approved trial
limited to 1 credit / four requests / one worker / no automatic retries. pug
accepted the v1 mapping. 33 tests (18 delegation + 15 observer), scoped ruff and
atlas freshness pass. four-attempt chronology: attempt 1 smoke-outcome-investigation-01
FAILED, usage unknown; attempt 2 diagnostic-transport-02 COMPLETED, 278/87 tokens,
result sha 126c5b0ceae0d50a569d6e513677ca60ed04ed690a8c28f6134f76f663993e2e;
attempt 3 smoke-audit-03 FAILED with response status incomplete, 1878/2048 tokens;
attempt 4 smoke-branch-audit-04 COMPLETED, 418/341 tokens, result sha
f6cb7c7458ee99479c988aea822b8774ac0f3ac9fed0d75272727a45258de050.
four requests consumed, 0.4 credits reserved locally, billing unobserved. usage
known for three attempts; dated estimate subtotal 0.0016241 credits, excluding
the first unknown request. the second completed task was a fictional source; the
fourth was a narrow real-code excerpt with its finding independently checked
offline. this does not establish broad investigator quality. duplicate replays
reuse receipts without calls or reservations. bounded status/usage diagnostics
distinguish response-validation failures without logging provider text. pr #23
corrects smoke failure status and attempted-call accounting. a post-merge
sast review on this slice requested changes; the sanitization respin is
tracked as task t-011. see
[delegation operations](control_plane/DELEGATION.md). older evidence below is
historical, not a current merge ledger.

control-plane observer: owner-approved first slice implemented in
`control_plane/`. a live pinned-ledger/github capture produced 33 supported task
rows, 19 prs and 12 reconciliation diagnostics. these are snapshot counts, not
a live board or worker inventory. fifteen offline tests pass; browser checks
cover desktop/720px/320px reflow, keyboard disclosure and no external requests.
pr #20 merged at 0d0aee8 after independent review. no dispatch or provider
activity occurred in the observer slice.
see [operations](control_plane/README.md). later checkpoints below are historical.


owner accepted [formal experiment protocol](specs/006-formal-experiment-handoff.md)
on 2026-11-07. source recovered into a durable worktree and atlas regenerated.
pr #14 is merged at 19b69e3; pr #5 (db0fde8) merged 2026-11-07 21:25Z and
pr #6 (46d54a3) remains open at this check. no formal run or provider
expenditure started. the historical
slice evidence below is retained; its pending-review labels are not a current
merge ledger. `bd prime` could not run here (`bd: command not found`); no board
was initialized or replaced.

evidence export: accepted spec005 implemented in the paired viewer. selected
turns produce bounded json/markdown previews and explicit local downloads with
exact-byte source hashes and slot-scoped references. nineteen model tests and
all three browser suites pass; downloaded files match previews. independent
export-boundary review is pending. no raw payload or outcome export is added.

evidence export: rework pushed 2026-11-07 on PR #16 (head 02daf4d). Restored master's
evidence-packet module API (build/prepare/markdown/sha256, CAVEATS, MAX_BYTES, comparison.js
integration, CJS/global shim). Added LRM/RLM/ALM + 12-char bidi map coverage ADDITIVELY to
text() function. Fixed all gate findings: & escaped first (prevents &#x202E; bypass), \n/\r
escaped in cells, U+2028/2029 + C0/C1 restored, config.seed escaped, optional chars
(U+200B/200C/200D, U+00AD, U+FEFF) added, JSDoc example corrected. Both test suites green:
evidence.test.cjs 4/4, evidence.test.js 46/46. Merged 2026-11-07 as 331a65c.

paired viewer: owner accepted `specs/004-paired-episode-comparison.md`.
`viewer/compare.html` implements turn-end alignment, slot-scoped evidence,
per-turn record counts and configuration comparison. fifteen model tests and
both browser suites pass. desktop/320px renders inspected; independent review,
screen-reader operation and full-size UI performance remain pending.

freight handoff follow-up: accepted `specs/003-freight-replay-handoff.md`;
compatibility fixture and provenance manifest added under `viewer/fixtures`.
ten model tests and browser checks pass against the pinned 394-event candidate.
the inspected pr #6 revision reproduces that fixture byte-for-byte but does not
connect the freight world to observations, actions or outcome totals. runtime
owner notified; world-backed acceptance remains blocked. no viewer runtime or
runner code changed. pr #9 is merged with caduceus review clear.

viewer slice: owner accepted `specs/002-episode-replay.md` on 2026-11-07.
local implementation in `viewer/index.html` opens recorded episodes offline,
plays append order, and inspects prefix-scoped evidence. see `viewer/README.md`
for commands and limits. nine model tests and the chrome browser checks pass;
independent import-boundary review and release remain pending. no runner code
was changed by this viewer work. the older runner/board status below is inherited
context and has not been refreshed by this viewer work.

branch `v4x-scripted-runner` (5e0f4d4) implements the turn-cycle runtime
from openspec change `add-turn-seam-event-log`. the runner is scripted
(zero model calls), replay-deterministic (same seed → byte-identical logs),
and implements the fixed turn cycle observe→exchange→act→record.

test suite (runtime/test_runner.py): 20/20 pass
- basic run produces valid event log with all required types
- determinism: same seed produces byte-identical output
- relay-loss disturbance applied and logged correctly with undelivered messages
- stale-report disturbance applied and logged correctly with before/after detail
- hub-spoke topology configuration works and delivers messages through hub
- message lifecycle tracking (sent→delivered→seen→acted_on) complete
- topology-independence: non-comm events identical across mesh/hub-spoke
- zero model/network calls in runner
- RNG stream independence: send decisions don't affect acted_on decisions (swarmachines-8s2)
- delivery_config_sha correctly named and validated (swarmachines-3x2)

sample outputs:
- runtime/sample-run.jsonl: 67 events (seed 7, 3 turns, relay-loss@turn 2)
- runtime/examples/sample-episode.jsonl: 23-event hand-authored illustrative sample
- runtime/schema/events.schema.json: JSON schema for event records

the unrelated `.env` was not read or changed.

verification commands and procedures:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory plans
curl --fail --silent --output /dev/null --write-out '%{http_code}\\n' http://127.0.0.1:8765/
python3 /home/resonatingloop/.resonance/exoresonance/repository-continuity/skills/manage-project-docs/scripts/check_docset.py .
```

the preview returned `200`. isolated chrome loaded the documented entry point,
opened all four dossiers, exercised relay loss and hypothetical repair, and
confirmed the calculator's 768-to-960 example without runtime exceptions.
the documentation checker returned 0 errors and six heading-casing warnings;
there were no other warnings. the five documentation files were classified
green by the codebase-care advisory checker. a content hash confirmed that
the proposal was unchanged by the bootstrap.

## working now

- one self-contained visual proposal, with no install or build step.
- four explorable lane dossiers, an illustrative disruption/repair sequence,
  and a call-count calculator whose default is 768 calls.
- print presentation of all four dossiers and readable summaries without
  javascript. desktop/mobile, keyboard, and reduced-motion behavior were
  exercised during the preceding presentation work.
- a front door, project brief, agent guide, and repeatable development
  instructions for owner and teammate re-entry.

## incomplete or broken

- adaption access, credit coverage, rates, spend allocation, and model serving
  have not been verified. langfuse tracing has not been connected or exercised.
- the distributed discord guides do not establish a live connection. no
  project room card, installed adapter, or peer round trip has been verified
  in this work.
- no deployment or accepted implementation spec exists. the documentation
  checker reports six casing-only warnings because its expected checkpoint
  headings use title case.

## active work

- seam contract owner-accepted per 2026-11-07 in-channel ruling (swarmachines-1iy);
  openspec change `add-turn-seam-event-log` implemented on branch
  `v4x-scripted-runner` (5e0f4d4). task 8 (observatory pointer) unblocked by
  that ruling.
- bd board (recreated twice by stray `bd init` — 16:22 UTC by a lost
  dispatch, 16:39 UTC by the dev child working around a bd
  workspace-identity mismatch; rule: never run bd init on this checkout,
  set BEADS_SKIP_IDENTITY_CHECK=1 instead):
  - swarmachines-m1p: v4x scripted runner — **closed** (implemented; 7/7
    tests re-run and verified by pug-bot 16:45 UTC)
  - swarmachines-e4i: my7 sample event log + determinism check — done;
    deliverables independently confirmed per the 11:00 CST checkpoint
    (determinism, schema-validity, zero-model-calls). board entry lost in
    the second wipe, not re-seeded because the work is confirmed
  - swarmachines-zpz: v4x round-2 residuals — **round-3 complete**: stale-report
    now uses real message in circulation (3 lifecycle entries: sent/delivered/seen);
    dead imports removed (timezone, json); action.rejected added to required set;
    agent-id regex fixed (\Z); verify_events path fixed; test_runner uses validated
    load_events. 11/11 tests pass. filed: swarmachines-8s2 (comm-RNG entanglement),
    swarmachines-3x2 (delivery_map_sha naming).
  - swarmachines-8s2: **implemented** — split exchange_rng into exchange_send_rng and
    exchange_acted_rng to prevent RNG state entanglement; test added (12/12 pass).
  - swarmachines-3x2: **implemented** — renamed delivery_map_sha to delivery_config_sha
    with docstring clarifying it hashes hub/topology config, not delivery graph; tests
    updated.
  - swarmachines-60c: y50 post-acceptance docs — **complete** (2026-11-07: topology ruling merged via PR #2, tasks.md updated, STATUS.md checkpoint recorded)
- report scaffold: docs/report/ (README submission checklist +
  report-skeleton.md mirroring the official Apart template: 8pp cap,
  abstract 150-250, required Limitations/Dual-Use appendix stubbed) —
  PR #4 from bd-swarmachines-bpk-report-skeleton; structure only,
  colette keeps m9p content ownership.
- current focus: freight-world integration (day-1 slice), adaption adapter (blocked on API key), topology comparison implementation
- pending decisions: world choice, lane owners, first disturbance choice
  ordering, provider budget/access details; room-process decisions from the
  09:34 CST huddle: discord/bridge re-enable, claim-before-work ledger
  convention, sast merge-gates sign-off; asterion's swim-lane split (pug=world/runner
  integration, colette=observatory+report) proposed in #general 17:44Z — awaiting
  colette's approval; github push/PR unblocked by the operator 2026-11-07
  (git-cred-sh helper + gh 2.103.3 auto-auth, checkout-wide) — 6031149 pushed
  to origin/v4x-scripted-runner; sast+verifier merge gates dispatched on the
  pushed branch.
- deadline: hackathon ends 2026-11-08 AoE (owner, #general 17:41:53Z) —
  tonight: one real replayable episode; tomorrow: matched comparison + report.
- agent context handoffs: requested for when the team is ready; not authored
  or assigned yet.
- prune pass 2026-11-07 (swarmachines-fvh): runtime/ ruff findings 14→3,
  behavior-preserving only — dead unpacked vars, nested-if collapse,
  set()/list-slice rewrites, ClassVar annotation, exec bits on the three
  scripts; runtime/test_runner.py 13/13 before and after. the three remaining
  findings are intentional (test-harness broad catch, non-checking subprocess
  helper, py<3.11 fromisoformat compat) and were not suppressed.

## next useful action

review pr #24's receipt projection at its current head before merging. refresh
private captures deliberately after task/receipt changes; existing HTML is frozen.
no dispatch, retries or new provider budget are implied by the board. separate
runtime integration and provider-sanitization work remain with their owners.

## re-entry notes

- checkout: `/home/resonatingloop/.organocybernetics/swarmachines`.
- launch from the repository root using the command above, or open
  `plans/index.html` directly; root-level `index.html` is not the entry point.
- the page requires no credentials and stores no application state.
- serve `plans`, not the repository root. stop your preview with ctrl+c.
- the harness guides are distributed separately; see the reference and
  coordination expectations in [AGENTS.md](AGENTS.md).
- consult [development](docs/DEVELOPMENT.md) for a busy port, missing browser
  tooling, repeatable checks, and the checker's casing mismatch.
