# swarmachines / status

> continuity role: operational checkpoint
> status: proposal ready for team review; direct and scored discord intake verified
> last verified: 2026-11-06
> owns: exercised state, active work, gaps, and the next useful action
> update when: a meaningful stopping point changes these facts; replace this checkpoint in place

## verified checkpoint

the working presentation remains [plans/index.html](plans/index.html).
[the written two-day plan](specs/001-hackathon-plan.md) records provisional
steps, lane responsibilities, integration checkpoints, workload choices,
fallbacks, and evidence required from a future implementation. its status is
`draft`; no runtime step has been executed as part of writing it.

planning started from commit `2158ea9` on `master`, matching the local
`origin/master` tracking reference. the presentation and bootstrap docs were
already tracked. this planning pass adds a draft and updates documentation
links; it does not commit or push. the unrelated `.env` was not read or changed.

documentation verification command:

```sh
python3 /home/resonatingloop/.resonance/exoresonance/repository-continuity/skills/manage-project-docs/scripts/check_docset.py .
```

the documentation checker returned 0 errors and the six known heading-casing
warnings. draft status, local links/anchors, workload arithmetic, and the
documentation diff were checked. the proposal's content hash is unchanged.
browser re-entry and the controls were exercised during the preceding
documentation work; no browser behavior changed in this pass.

discord setup now has a pinned local adapter and a machine-local codex MCP
registration. its stdio identity call authenticated as `asterion`, bot id
`1568464640424419338`. the owner changed the workroom to `general`, channel
`1567709897678655530`; its server id and readable recent history are verified.
pug's bot author id matches `1568444874133479476`. the owner authorized an
introduction and brief hackathon coordination in this channel. the introduction
was posted once as message `1568478900034609184`. pug-bot's reply
`1568479415145468068` cited that exact id and was read through the adapter;
the peer round trip is verified.
see [the connection record](docs/DISCORD.md) for exact ids and paths. the token
remains outside the repo; its value was not displayed.

the owner then requested scored ambient intake alongside coding and approved
a 1-credit / 1,000-judgment rolling daily cap through adaption. the machine-local
listener is installed and passed 23 offline tests. the adaption key and model
access are verified; four live synthetic scoring cases passed, using
`0.0001501185` estimated credits. the owner then launched the listener. live
intake queued one direct mention and one selected ambient message, while
ignoring two ambient bot messages. the ledger now records five judgments and
`0.0003024045` estimated credits at that checkpoint. the direct notification
arrived in this same coding session after its active response ended. asterion
reread the room, sent reply `1568489305255706717`, and read it back. busy-session
delivery is verified. the scored ambient notification subsequently arrived in
this same session, matching its source id, model call, and queued ledger entry;
no duplicate reply was sent. idle wakeup remains unverified.
the owner terminal can reach codex daemon `0.167.0`; this tool environment cannot access
its control socket. [discord setup](docs/DISCORD.md#selective-intake-alongside-coding)
owns the launch commands and boundaries.

## working now

- one self-contained visual proposal, with no install or build step.
- four explorable lane dossiers, an illustrative disruption/repair sequence,
  and a call-count calculator whose default is 768 calls.
- print presentation of all four dossiers and readable summaries without
  javascript. desktop/mobile, keyboard, and reduced-motion behavior were
  exercised during the preceding presentation work.
- a front door, project brief, agent guide, and repeatable development
  instructions for owner and teammate re-entry.
- a written route through day-one integration, day-two comparisons, adaption
  use, evidence review, and final handoffs.
- local asterion launcher, authenticated bot identity, readable room messages,
  and a confirmed peer round trip through the installed MCP adapter.
- selective intake with approved adaption caps, live message processing, two
  queue submissions, and verified direct and scored delivery into this coding
  session between responses, with one read-back discord reply.

## incomplete or broken

- no world simulation, agent runner, measured event log, replay of real runs,
  or accepted event/action contract has been implemented.
- the adaption grant balance, broader credit coverage, and experimental-run
  spend allocation remain unverified. the listener's hosted model access,
  published rates, small scoring calls, and local cap are verified. langfuse
  tracing has not been connected or exercised.
- discord native session tool discovery remains unverified. live read/send
  proof used a stdio client with the configured MCP launcher;
  these tools are not yet present in this conversation's native tool catalog.
- selective listener idle-session wakeup remains unverified. direct and scored
  delivery between responses is verified; four synthetic judgments remain a
  smoke check, not a calibrated participation evaluation.
- no committed automated test suite, deployment, or accepted implementation
  spec exists. the documentation checker reports six casing-only warnings
  because its expected checkpoint headings use title case.

## active work

- accepted runtime spec: none.
- draft: [001-hackathon-plan](specs/001-hackathon-plan.md).
- current focus: return to team review and lane selection; the local listener
  pilot has verified direct and scored intake into the active coding session.
- pending decisions: world, lane owners, runtime, communication arrangements,
  disturbance semantics, first implementation slice, exact dependencies, and
  provider budget/access details.
- agent context handoffs: requested for when the team is ready; not authored
  or assigned yet.

## next useful action

the listener pilot has verified both direct and scored delivery. to move it
out of the foreground terminal, stop that run with ctrl+c and use the
[background launch command](docs/DISCORD.md#background-run). the owner has now
launched it: test `1568510802430922815` was logged, queued, received by this
session, and answered with a read-back reply. terminal-close and suspend/resume
survival have not been exercised. the bounded two-hour duration and existing
caps remain in place. see
[discord setup](docs/DISCORD.md) for status and stop commands. a fresh coding
session needs its own explicit target-thread configuration.

review the [working defaults](specs/001-hackathon-plan.md#working-defaults-to-review)
with the team. choose owners and the first bounded implementation slice, then
revise and explicitly accept that slice before building. the later weekend
route can remain provisional beyond it.

## re-entry notes

- checkout: `/home/resonatingloop/.organocybernetics/swarmachines`.
- launch from the repository root using the command above, or open
  `plans/index.html` directly; root-level `index.html` is not the entry point.
- the page requires no credentials and stores no application state.
- the visual calculator still counts four conditions by default. the written
  plan separately explains additional control runs; it does not change the ui.
- serve `plans`, not the repository root. stop your preview with ctrl+c.
- the harness guides are distributed separately; see the reference and
  coordination expectations in [AGENTS.md](AGENTS.md).
- consult [development](docs/DEVELOPMENT.md) for a busy port, missing browser
  tooling, repeatable checks, and the checker's casing mismatch.
