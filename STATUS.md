# swarmachines / status

> continuity role: operational checkpoint
> status: seam contract drafted; awaiting owner acceptance
> last verified: 2026-11-07
> owns: exercised state, active work, gaps, and the next useful action
> update when: a meaningful stopping point changes these facts; replace this checkpoint in place

## verified checkpoint

the working entry point is [plans/index.html](plans/index.html). the
documentation bootstrap preserves the proposal and its existing location.
the repository has no commits on `master`; the proposal and docs are local
untracked work. the unrelated `.env` was not read or changed.

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

- no world simulation, agent runner, measured event log, replay of real runs,
  or accepted event/action contract has been implemented.
- adaption access, credit coverage, rates, spend allocation, and model serving
  have not been verified. langfuse tracing has not been connected or exercised.
- the distributed discord guides do not establish a live connection. no
  project room card, installed adapter, or peer round trip has been verified
  in this work.
- no committed automated test suite, deployment, or accepted implementation
  spec exists. the documentation checker reports six casing-only warnings
  because its expected checkpoint headings use title case.

## active work

- accepted runtime spec: none. drafted, unaccepted: openspec change
  `add-turn-seam-event-log` (turn cycle, event schema, comm topologies,
  message lifecycle, two disturbances, replay determinism, zero-model
  operation) with a 23-event sample episode under `runtime/`.
- bd board re-seeded 16:33 UTC after a bd-init wipe (16:22, commit 4f0200d,
  pug-bot identity; old dolt state under .beads/backup): 81u = 087 closed
  (schema + sample), lto = v4x (scripted runner, dispatched to dev),
  459 = my7 (blocked-by lto), a3r = y50 (post-acceptance docs, gated on
  owner acceptance).
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
