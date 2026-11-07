# swarmachines / agent guide

this file governs repository work. read it alongside applicable parent
instructions and the owner's current request.

## read before acting

1. [README.md](README.md): entry point and authority map.
2. [STATUS.md](STATUS.md): the checkpoint and next useful action.
3. [PROJECT_BRIEF.md](PROJECT_BRIEF.md): intent and unresolved design choices.
4. [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): validation and recovery.
5. [plans/index.html](plans/index.html) when changing the proposal. read the
   relevant accepted spec before runtime implementation, once one exists.

## scope and voice

- keep prose lowercase; preserve the required case of code, paths, identifiers,
  and source names when accuracy depends on it.
- contribute generatively during exploration. a coherent idea, attractive
  mockup, or enthusiastic review does not accept an implementation spec.
- a direct bounded change request authorizes that change. carry it through
  without asking again for permission already supplied by the owner.
- new substantial or cross-cutting runtime work needs an explicitly accepted
  spec. agents may draft one; the owner or designated decision-maker accepts
  it. keep a draft marked `draft` until that happens.
- document preparation and local presentation work do not grant permission
  for paid provider runs, discord posting, commits, pushes, publication, or
  deployment. establish the actual scope from the owner's instructions.
- preserve other people's edits, file moves, and git state. inspect before
  changing files. this checkout has an unrelated `.env`; do not read, source,
  copy, stage, or serve it. the page needs no secrets.

## preserve meaning

the working page is a proposal, not an experiment run. its diagrams are
illustrative, lane buttons do not assign people, and its calculator counts
calls under stated assumptions. do not relabel them as results or a price quote.

keep known events distinct from interpretation. generated examples are not
observed episodes; message traffic does not by itself prove influence. the
proposed observation/action/event seam has no accepted schema yet.

## standing delivery procedure

owner instruction, 2026-11-07: after an authorized implementation slice passes
its applicable checks, commit the intended files, push its feature branch,
open or update a pull request, and notify caduceus in agent-collab for review
and merge. do this without asking for repeat commit/push/pr permission.

- include the exact commit, pr link, actual verification and remaining gates.
- partial work may be handed off when independently reviewable; clearly mark
  blocked acceptance criteria and do not imply the whole slice is complete.
- preserve independent review and merge gates; caduceus handles merge, not
  the implementing agent. do not push directly to master.
- use explicit file selection and preserve unrelated work. this standing
  instruction does not authorize deployments, paid runs or broader scope.
- send review traffic to approved agent-collab channel `1567709897678655531`,
  with caduceus's actual mention `<@1541697569002889266>`; verify delivery.

## coordination and eventual handoffs

the owner has distributed harness-specific discord guides. use the guide for
your actual harness when joining; do not infer that an adapter is installed
from a setup example. the codex guide supplied during planning is available
on the owner's machine at
`/home/resonatingloop/Documents/discord-hackathon-guides/discord-hackathon/codex.md`.
that location is an external reference, not a required runtime file.

the local connection and supplied room identities are recorded in
[docs/DISCORD.md](docs/DISCORD.md). use its observed proof and posting scope;
installation alone does not establish channel access or permission to post.

room identities, approved teammates, the pinned adapter, and posting scope
must be supplied before joining. once established, follow the guide's
checkpoint rhythm. ordinary read/send tools do not wake idle agents. prove
communication by posting within authorized scope, having a peer reply, and
reading that reply; record partial success honestly.

when lane assignments are agreed and handoffs are requested, include each
human and agent handle, assignment, checkout/revision, accepted scope,
shared interfaces, evidence, blockers, and one concrete next action. preserve
exact ids. a teammate request supplies context, not new authority; a discord
message is not a transfer of code. keep credentials and unrelated private
material out of the room.

## validation and close

for documentation changes, check local links, authority labels, open choices,
and checkpoint freshness with the command in
[development](docs/DEVELOPMENT.md#documentation-checks). the supplied checker
has six known casing-only warnings for the lowercase checkpoint headings;
report other findings rather than treating all warnings as expected.

for presentation changes, run the affected browser checks in
[development](docs/DEVELOPMENT.md#focused-browser-checks). do not claim a
provider integration from a static page render. there is no committed test
suite or build process to invoke.

at a meaningful stopping point, replace the checkpoint in `STATUS.md`, update
the documents whose facts changed, and report actual evidence and remaining
unknowns. keep the next action usable without this conversation. do not add
session transcripts, duplicate verification reports, or speculative contracts.

## Task Tracking — TASKS.md Ledger

This project uses **TASKS.md** for durable task tracking. Beads (bd) was retired on 2026-11-07; never run `bd` commands.

### Ledger Format

One line per task: `- [STATUS] ID: title — owner: NODE — updated: TS`

- STATUS: `open` | `doing` | `blocked` | `done`
- Claim work by moving a line to `doing` with your node as owner
- Close work by moving to `done` when tests pass and ruff is clean
- Check TASKS.md before starting any work; update it when status changes

### Rules

- Use TASKS.md for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Commit ledger updates with your work — the ledger is the single source of truth
- The coordinator owns routing; beads is retired and must never be invoked

**Critical:** Explicit user or orchestrator instructions override this guidance. Do not commit or push without clear authority from the current user request. If blocked, stop and report the exact blocker.
