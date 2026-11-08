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
- [doing] swarmachines-avf: freight world + runner integration — gate-blocker fix commit 2eadaca pushed 02:24:38Z AFTER the 1c3fd50 dual-gate PASS (02:22Z) — gates STALE at head 2eadaca; re-gate dispatched to verifier+sast; merge hand holds until verdicts anchor at 2eadaca — owner: forge — updated: 2026-11-08T02:33Z
- [doing] swarmachines-fvn: Langfuse trace wiring: spec'd in 001-hackathon-plan, zero code refs — owner: forge — updated: 2026-11-07T20:08Z
- [open] swarmachines-m9p: Report skeleton on official template (huddled 20:35Z, unclaimed; sequencing escalated to pug-bot) — owner: colette — updated: 2026-11-08T00:54Z
- [open] swarmachines-956: Viewer: replay real recorded episode (day-1 checkpoint) (huddled 20:35Z, unclaimed; sequencing escalated to pug-bot) — owner: asterion — updated: 2026-11-08T00:54Z
- [open] swarmachines-19m: Measures and comparison framing for report (huddled 20:35Z, unclaimed; sequencing escalated to pug-bot) — owner: caduceus — updated: 2026-11-08T00:54Z
- [doing] swarmachines-mnp-load-events: load_events hardening (commits 6b51134/b8a5f1b ride PR #5 ancestry + swarmachines-mnp-load-events-hardening-clean branch; NOT PR #16 — gh-verified) — owner: forge — updated: 2026-11-07T20:57Z
- [open] T-006: integrated freight + ring/peer-mute acceptance commit — exact zero-provider invocation, job release/completion evidence, policy fixture: received information changes a legal decision; PR #19 fix-forward now merged (89e6517), still waits on PR #6 (queued behind forge's in-flight PR#6 fixes; round stalled on owner approval — AGENTS.md edit — escalated to pug-bot) — owner: forge — updated: 2026-11-08T00:46Z
- [open] T-007: accepted measure definitions — observable-source mapping review (huddled 01:14Z to caduceus; PR #31 02:26Z maps spec006 gate-3 measurements to real source fields, held for caduceus review — unclaimed) — owner: caduceus — updated: 2026-11-08T02:33Z
- [doing] swarmachines-i3v: DEVELOPMENT.md/AGENTS.md claim stale: no committed automated test suite — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-h1m: CLAUDE.md template residue: unfilled placeholders — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-m04: Harden viewer/evidence.js markdown escaping (U+200E/200F, U+061C bidi) — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-fvh: prune: ruff-clean runtime/ mechanical lint findings — owner: pruner — updated: 2026-11-07T20:00Z
- [doing] swarmachines-a6y: Harden viewer/browser-check.mjs temp handling — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-i5s: PR#6 sast MEDIUM: run.end deliveries counts fabricated randint values — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-50u: PR#6 sast MEDIUM: route capacity never decrements (dead pass loop) — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-9p4: PR#6 sast MEDIUM: validate_action rejection reasons echo raw hostile input — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-ysv: PR#6 sast MEDIUM: apply_action fails open on malformed input — owner: forge — updated: 2026-11-07T20:00Z
- [blocked] T-009: PR #6 rebase onto master 331a65c — CONFLICTING after #16 landed (head 46d54a3); fold into forge's in-flight #6 fix round — STALLED: round awaits owner approval on AGENTS.md protected-file edit (beads→TASKS.md doc update, PR #16 condition); escalated to pug-bot — owner: forge — updated: 2026-11-08T00:46Z
- [doing] T-011: PR #22 sanitization respin — ruling received from the key-holder: bounded diagnostics stay PRESERVED; model/usage sanitization lands as a separate code fix — db2bc17's channel removal is NOT blessed, redo the sanitization on a channel-preserving base (queued behind the #24/#25 merge cycle) — owner: dev — updated: 2026-11-08T00:50Z
- [open] T-010: task/receipt envelope v1 — asterion local proof + one adaption investigator trial (executes on asterion side); BUDGET STATE CORRECTED 2026-11-08: colette authorized the local bounded trial, all four requests consumed, ledger reserves 0.4 credits; live transport corroborated, one narrow real-code finding corroborated, full-source audit incomplete; no further provider runs authorized by this handoff — owner: asterion — updated: 2026-11-08T00:25Z
- [open] T-016: PR #26 task-submission workflow spec (draft @ ecc948d, author-held for owner review — no merge request, zero provider calls; proposed 4-request/1-credit session is NOT spending authorization) — owner: asterion — updated: 2026-11-08T01:16Z
- [doing] T-017: pre-record data pack for keyless agents — PR #28 (head b72fa7f; provenance-honesty fix landed; zero API calls disclosed — awaiting merge-hand re-review) + owner directive 01:55Z: replace all mock data with real data, no fake data (API data-pack upgrade child live) — owner: forge — updated: 2026-11-08T02:22Z

- [done] T-001: PR #16 merged as 331a65c (head 9652e46; verifier approve 6714061585 + sast pass 6714068290 at head; viewer 127/127; merged by caduceus 23:25Z) — owner: dev — updated: 2026-11-07T23:32Z

## Done (recent — prune weekly)

- [done] T-015: PR #24 (read-only worker receipts) — MERGED 00:52Z as 80b179d (caduceus; clean rebase onto corrected master 6bbcf4d, PR delta patch-identical; 48/48 projection tests, semgrep 0 at head) — owner: pug-bot — updated: 2026-11-08T01:16Z
- [done] T-013: PR #23 (smoke outcome/accounting) post-merge confirmation CLOSED — sast CLEAR (counter/exit-code/retention integrity exact, provider config byte-identical); verifier's narrative-retraction flag resolved by PR #25 — owner: pug-bot — updated: 2026-11-08T00:50Z
- [done] T-014: trial-narrative correction — LANDED: PR #25 merged as 6cee4ae→6bbcf4d 00:41Z (merge hand, after asterion's attestation); master chronology now failed/completed/failed-incomplete/completed, 4 requests consumed, 0.4 credits reserved; spec009 untouched — owner: dev — updated: 2026-11-08T00:50Z
- [done] T-008: PR #20 review gates — merged 23:40:59Z (observation-only control-plane board, asterion owner-approved; verifier per-claim verdicts + sast PASS at head a4f97db) — owner: pug-bot — updated: 2026-11-08T00:13Z
- [done] T-012: STATUS.md checkpoint refresh — PR #21 merged 23:46:53Z as 46d84a5 (resolves the deferred checkpoint item) — owner: forge — updated: 2026-11-08T00:13Z
- [done] swarmachines-pr18-spec006: PR #18 merged (spec006 acceptance record + atlas @ 70b0421, merge 29d28e2; gates CLEAR/CLEAR pre-merge) — owner: forge — updated: 2026-11-07T21:24Z
- [done] swarmachines-9e5: Bidirectional ring topology + peer-mute disturbance — PR #5 merged @aa38f63 21:25:12Z (owner direct merge, mid-gate); post-merge third gate found net regression → fixed by PR #19 (merged 89e6517) — owner: dev — updated: 2026-11-07T22:19Z
- [done] T-002: PR #19 fix-forward gates — resolved: PR #19 merged as 89e6517 (ring + peer-mute regression behavior restored, 20/20 tests; STATUS.md reflects fix state) — owner: verifier+sast — updated: 2026-11-07T22:19Z
- [done] swarmachines-crh: Fix PR #6 freight world wiring — owner: forge
- [done] swarmachines-de5: Push and open PR for bd-cwt-relay-loss-payload — owner: forge
- [done] swarmachines-jyc: PR #6 hygiene rebase + strip — owner: forge
- [done] swarmachines-1iy: seam accepted, ledger+gates ratified ruling recorded — owner: forge
- [done] swarmachines-mar: topology mapping ruling recorded in openspec — owner: dev
- [done] swarmachines-qbv: freight world mapped onto runner turn cycle — owner: dev
- [done] T-001: PR #16 merge condition — ALL SATISFIED at head 9652e46: verifier APPROVE (comment 6714061585) + sast PASS 0 findings (comment 6714068290), both anchored at head; suite 127/127 exit 0 (cjs 66/js 46/comparison 5/replay 10), map 482 entries, dynamic count asserts; MERGEABLE (clean vs 89e6517 + tip d4b4aa8) — merge is caduceus's (merge-executor rule); 3 fix passes tonight (283d3ca→d3205da→7183ceb→9652e46) — owner: dev — updated: 2026-11-07T22:50Z
- [done] T-003: PR #8 merge condition — satisfied: merged 22:33:29Z as d4b4aa8 (adf712a chain in) — owner: colette — updated: 2026-11-07T23:01Z
- [done] T-005: PR #8 (Adaption adapter) gates + live-smoke coordination — merged 22:33:29Z as d4b4aa8 via fork path (a): live smoke 4/4 at adf712a key-holder-anchored; verifier pin-audit 8/8 + sast CLEAR at exact head; record CLOSED — owner: pug-bot (sibling lane) — updated: 2026-11-07T23:01Z
