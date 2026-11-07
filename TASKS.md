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
- [doing] swarmachines-mnp-load-events: load_events hardening (commits 6b51134/b8a5f1b ride PR #5 ancestry + swarmachines-mnp-load-events-hardening-clean branch; NOT PR #16 — gh-verified) — owner: forge — updated: 2026-11-07T20:57Z
- [doing] T-001: PR #16 merge condition — rebase #2 resolved: head 56389e5 (on master 89e6517, MERGEABLE/CLEAN; suites 61/61 escaping + 122/122 viewer incl. 5 sast-probe tests; sast findings of review 5815211389 fixed) — re-gate (verifier+sast) in flight, then merge-hand — owner: dev — updated: 2026-11-07T22:19Z
- [doing] T-005: PR #8 (Adaption adapter) gates + live-smoke coordination — head adf712a (latest respin); lint/ruff respin + sast MEDIUM scrub (SDK error strings verbatim) owned by the sibling lane; smoke host = colette's process (key not visible in this container, SDK absent) — owner: pug-bot (sibling lane) — updated: 2026-11-07T22:19Z
- [open] T-006: integrated freight + ring/peer-mute acceptance commit — exact zero-provider invocation, job release/completion evidence, policy fixture: received information changes a legal decision; PR #19 fix-forward now merged (89e6517), still waits on PR #6 — owner: pug-bot (assignee TBD: dev/forge) — updated: 2026-11-07T22:19Z
- [open] T-007: accepted measure definitions — observable-source mapping review — owner: caduceus — updated: 2026-11-07T22:05Z
- [doing] T-003: PR #8 merge condition — code APPROVED, head PINNED adf712a (env-only contract enforced); merge waits on key-holder green-smoke receipt at pinned head (colette's host) — owner: colette — updated: 2026-11-07T22:28Z
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

- [done] swarmachines-pr18-spec006: PR #18 merged (spec006 acceptance record + atlas @ 70b0421, merge 29d28e2; gates CLEAR/CLEAR pre-merge) — owner: forge — updated: 2026-11-07T21:24Z
- [done] swarmachines-9e5: Bidirectional ring topology + peer-mute disturbance — PR #5 merged @aa38f63 21:25:12Z (owner direct merge, mid-gate); post-merge third gate found net regression → fixed by PR #19 (merged 89e6517) — owner: dev — updated: 2026-11-07T22:19Z
- [done] T-002: PR #19 fix-forward gates — resolved: PR #19 merged as 89e6517 (ring + peer-mute regression behavior restored, 20/20 tests; STATUS.md reflects fix state) — owner: verifier+sast — updated: 2026-11-07T22:19Z
- [done] swarmachines-crh: Fix PR #6 freight world wiring — owner: forge
- [done] swarmachines-de5: Push and open PR for bd-cwt-relay-loss-payload — owner: forge
- [done] swarmachines-jyc: PR #6 hygiene rebase + strip — owner: forge
- [done] swarmachines-1iy: seam accepted, ledger+gates ratified ruling recorded — owner: forge
- [done] swarmachines-mar: topology mapping ruling recorded in openspec — owner: dev
- [done] swarmachines-qbv: freight world mapped onto runner turn cycle — owner: dev
- [done] swarmachines-zpz, wwn, e74, r08, deb, 3x2, 8s2, 60c, psx, cwt, cu8, kmr, d86, mnp: closed rounds 1-3 — owner: various
