# swarmachines / status

> continuity role: operational checkpoint
> status: v4x runner implemented; seam contract drafted, awaiting owner acceptance
> last verified: 2026-11-07 (round-3: all 12 tests pass, stale-report fixed)
> owns: exercised state, active work, gaps, and the next useful action
> update when: a meaningful stopping point changes these facts; replace this checkpoint in place

## verified checkpoint

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
was changed by this slice. the older runner/board status below is inherited
context and has not been refreshed by this viewer work.

branch `v4x-scripted-runner` (5e0f4d4) implements the turn-cycle runtime
from openspec change `add-turn-seam-event-log`. the runner is scripted
(zero model calls), replay-deterministic (same seed → byte-identical logs),
and implements the fixed turn cycle observe→exchange→act→record.

test suite (runtime/test_runner.py): 12/12 pass
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
curl --fail --silent --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:8765/
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

open the [proposal's team-choice section](plans/index.html#choose) with the
group and choose the world, lane owners, and first disturbance. record those
choices before drafting the first bounded runtime spec and agent handoffs.
the documentation bootstrap does not accept that future work on the team's
behalf.

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
