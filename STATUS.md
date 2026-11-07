# swarmachines / status

> continuity role: operational checkpoint
> status: v4x runner implemented; seam contract drafted, awaiting owner acceptance
> last verified: 2026-11-07
> owns: exercised state, active work, gaps, and the next useful action
> update when: a meaningful stopping point changes these facts; replace this checkpoint in place

## verified checkpoint

branch `v4x-scripted-runner` (68f66a2) implements the turn-cycle runtime
from openspec change `add-turn-seam-event-log`. the runner is scripted
(zero model calls), replay-deterministic (same seed → byte-identical logs),
and implements the fixed turn cycle observe→exchange→act→record.

test suite (runtime/test_runner.py): 11/11 pass
- basic run produces valid event log with all required types
- determinism: same seed produces byte-identical output
- relay-loss disturbance applied and logged correctly with undelivered messages
- stale-report disturbance applied and logged correctly with before/after detail
- hub-spoke topology configuration works and delivers messages through hub
- message lifecycle tracking (sent→delivered→seen→acted_on) complete
- topology-independence: non-comm events identical across mesh/hub-spoke
- zero model/network calls in runner

sample outputs:
- runtime/sample-run.jsonl: 61 events (seed 7, 3 turns, relay-loss@turn 2)
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

- owner acceptance of the seam contract (`add-turn-seam-event-log`) pending;
  task 8 (update STATUS.md checkpoint, point observatory lane at sample log)
  is gated on acceptance.
- adaption access, credit coverage, rates, spend allocation, and model serving
  have not been verified. langfuse tracing has not been connected or exercised.
- the distributed discord guides do not establish a live connection. no
  project room card, installed adapter, or peer round trip has been verified
  in this work.
- no deployment or accepted implementation spec exists. the documentation
  checker reports six casing-only warnings because its expected checkpoint
  headings use title case.

## active work

- accepted runtime spec: none. drafted, unaccepted: openspec change
  `add-turn-seam-event-log` (turn cycle, event schema, comm topologies,
  message lifecycle, two disturbances, replay determinism, zero-model
  operation). implementation complete on branch `v4x-scripted-runner`
  (68f66a2); awaiting owner acceptance before task 8 (observatory pointer).
- bd board (recreated twice by stray `bd init` — 16:22 UTC by a lost
  dispatch, 16:39 UTC by the dev child working around a bd
  workspace-identity mismatch; rule: never run bd init on this checkout,
  set BEADS_SKIP_IDENTITY_CHECK=1 instead):
  - swarmachines-m1p: v4x scripted runner — **closed** (implemented; 7/7
    tests re-run and verified by pug-bot 16:45 UTC)
  - swarmachines-e4i: my7 sample event log + determinism check — open,
    ready (deliverables appear to exist on the branch; verifier to confirm)
  - swarmachines-60c: y50 post-acceptance docs — open, gated on owner
    acceptance
- current focus: owner acceptance or amendment of the seam change.
- pending decisions: world choice, lane owners, first disturbance choice
  ordering, provider budget/access details; room-process decisions from the
  09:34 CST huddle: discord/bridge re-enable, claim-before-work ledger
  convention, sast merge-gates sign-off.
- agent context handoffs: requested for when the team is ready; not authored
  or assigned yet.

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
