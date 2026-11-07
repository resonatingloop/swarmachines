# Task Ledger — swarmachines

Durable, human-readable task state. Replaces beads (retired 2026-11-07).
Format: one line per task, exactly `- [STATUS] ID: title — owner: NODE — updated: TS`
STATUS: open | doing | blocked | done. IDs: T-NNN (new) or legacy swarmachines-XXX.
Claim by moving a line to `doing` with your node as owner. Close by moving to `done`.
Check this file before starting any work; update it when status changes.
The coordinator owns routing; the ledger is the single source of truth.

## Active

- [doing] swarmachines-73o: sast HIGH (f92dfd8): markdown export passes raw HTML through — evidence.test.cjs fails — owner: forge — updated: 2026-11-07T20:08Z
- [doing] swarmachines-b9f: PR#6 sast HIGH: freight-world integration dead code — run() never wires FreightWorld — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-bof: Fix PR #5: decouple freight-world contamination, gate peer-mute on turn, restore undeliverable — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-bpk: m9p-a: report skeleton scaffold in docs/report/ (colette keeps m9p content ownership) — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-avf: freight world + runner integration: day-1 recorded episode (schema-valid, replayable) — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-fvn: Langfuse trace wiring: spec'd in 001-hackathon-plan, zero code refs — owner: forge — updated: 2026-11-07T20:08Z
- [open] swarmachines-m9p: Report skeleton on official template — owner: colette — updated: 2026-11-07T20:35Z
- [open] swarmachines-956: Viewer: replay real recorded episode (day-1 checkpoint) — owner: asterion — updated: 2026-11-07T20:35Z
- [open] swarmachines-19m: Measures and comparison framing for report — owner: caduceus — updated: 2026-11-07T20:35Z
- [doing] swarmachines-9e5: Bidirectional ring topology + peer-mute disturbance — owner: dev — updated: 2026-11-07T20:30Z
- [doing] swarmachines-i3v: DEVELOPMENT.md/AGENTS.md claim stale: no committed automated test suite — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-h1m: CLAUDE.md template residue: unfilled placeholders — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-m04: Harden viewer/evidence.js markdown escaping (U+200E/200F, U+061C bidi) — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-fvh: prune: ruff-clean runtime/ mechanical lint findings — owner: pruner — updated: 2026-11-07T20:00Z
- [doing] swarmachines-a6y: Harden viewer/browser-check.mjs temp handling — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-i5s: PR#6 sast MEDIUM: run.end deliveries counts fabricated randint values — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-50u: PR#6 sast MEDIUM: route capacity never decrements (dead pass loop) — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-9p4: PR#6 sast MEDIUM: validate_action rejection reasons echo raw hostile input — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-ysv: PR#6 sast MEDIUM: apply_action fails open on malformed input — owner: forge — updated: 2026-11-07T20:00Z

## Done (recent — prune weekly)

- [done] swarmachines-crh: Fix PR #6 freight world wiring — owner: forge
- [done] swarmachines-de5: Push and open PR for bd-cwt-relay-loss-payload — owner: forge
- [done] swarmachines-jyc: PR #6 hygiene rebase + strip — owner: forge
- [done] swarmachines-1iy: seam accepted, ledger+gates ratified ruling recorded — owner: forge
- [done] swarmachines-mar: topology mapping ruling recorded in openspec — owner: dev
- [done] swarmachines-qbv: freight world mapped onto runner turn cycle — owner: dev
- [done] swarmachines-zpz, wwn, e74, r08, deb, 3x2, 8s2, 60c, psx, cwt, cu8, kmr, d86, mnp: closed rounds 1-3 — owner: various
