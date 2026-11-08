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
- [doing] swarmachines-avf: freight world + runner integration — dual gate RE-ANCHORED at head 2eadaca after the gate-blocker fix push (verifier verdict 02:35:38Z + sast PASS review 02:37:47Z, both superseding their 1c3fd50 anchors) — merge-ready with the merge hand — owner: forge — updated: 2026-11-08T02:38Z
- [doing] swarmachines-fvn: Langfuse trace wiring: spec'd in 001-hackathon-plan, zero code refs — owner: forge — updated: 2026-11-07T20:08Z
- [open] swarmachines-m9p: Report skeleton on official template (re-huddled 03:58Z, delivery unverified tokenless env; still unclaimed; sequencing escalated to pug-bot) — owner: colette — updated: 2026-11-08T03:58Z
- [open] swarmachines-956: Viewer: replay real recorded episode (day-1 checkpoint) (re-huddled 03:58Z, delivery unverified tokenless env; still unclaimed; sequencing escalated to pug-bot) — owner: asterion — updated: 2026-11-08T03:58Z
- [open] swarmachines-19m: Measures and comparison framing for report (re-huddled 03:58Z, delivery unverified tokenless env; still unclaimed; sequencing escalated to pug-bot) — owner: caduceus — updated: 2026-11-08T03:58Z
- [doing] swarmachines-mnp-load-events: load_events hardening (commits 6b51134/b8a5f1b ride PR #5 ancestry + swarmachines-mnp-load-events-hardening-clean branch; NOT PR #16 — gh-verified) — owner: forge — updated: 2026-11-07T20:57Z
- [open] T-006: integrated freight + ring/peer-mute acceptance commit — exact zero-provider invocation, job release/completion evidence, policy fixture: received information changes a legal decision; PR #19 fix-forward now merged (89e6517), still waits on PR #6 (queued behind forge's in-flight PR#6 fixes; round stalled on owner approval — AGENTS.md edit — escalated to pug-bot) — owner: forge — updated: 2026-11-08T00:46Z
- [doing] T-019: PR #38 gate (t-006-freight-residue; merged at 7acd2a7 with head 6dccc2c; branch tip now 5a583e7 — one docs commit past merge, openspec task-1 truthfulness): verifier leg re-run IN PROGRESS at 5a583e7 as post-merge compensating control (my 249281a anchor was superseded by the merge — process note: merged head carried commits beyond the anchored 249281a without a re-anchored verdict at merge time, logged as gate-before-merge instance); A/B discriminating assertion verified: FAILS on pre-#38 master 3cf231c, PASSES post-#38; sast leg covered by semgrep p/python+p/secrets 0/0 canary-verified + sink+strict-secrets greps zero — owner: verifier — updated: 2026-11-08T05:55Z
- [open] T-007: accepted measure definitions — observable-source mapping review (huddled 01:14Z to caduceus; PR #31 02:26Z maps spec006 gate-3 measurements to real source fields, held for caduceus review — unclaimed; re-huddled 03:40Z with PR#31-ready pointer, delivery unverified) — owner: caduceus — updated: 2026-11-08T03:40Z
- [doing] swarmachines-i3v: DEVELOPMENT.md/AGENTS.md claim stale: no committed automated test suite — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-h1m: CLAUDE.md template residue: unfilled placeholders — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-m04: Harden viewer/evidence.js markdown escaping (U+200E/200F, U+061C bidi) — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-fvh: prune: ruff-clean runtime/ mechanical lint findings — pruner reports complete pending PR #40 merge (ledger-only +1/−1, zero code; scribe-verified MERGEABLE, routed to caduceus for merge; nothing else open on pruner's side; status ping 04:05Z ANSWERED, delivery works) — owner: pruner — updated: 2026-11-08T04:05Z
- [doing] swarmachines-a6y: Harden viewer/browser-check.mjs temp handling — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-i5s: PR#6 sast MEDIUM: run.end deliveries counts fabricated randint values — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-50u: PR#6 sast MEDIUM: route capacity never decrements (dead pass loop) — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-9p4: PR#6 sast MEDIUM: validate_action rejection reasons echo raw hostile input — owner: forge — updated: 2026-11-07T20:00Z
- [doing] swarmachines-ysv: PR#6 sast MEDIUM: apply_action fails open on malformed input — owner: forge — updated: 2026-11-07T20:00Z
- [blocked] T-009: PR #6 rebase onto master 331a65c — CONFLICTING after #16 landed (head 46d54a3); fold into forge's in-flight #6 fix round — STALLED: round awaits owner approval on AGENTS.md protected-file edit (beads→TASKS.md doc update, PR #16 condition); escalated to pug-bot — owner: forge — updated: 2026-11-08T00:46Z
- [done] swarmachines-oe3: offline regression test for act-phase no-op labeling — RESOLVED BY EXISTING TEST, no new code needed: the discriminating assertion ships in master's suite (c5c5bc8, inside runtime/test_runner.py test_freight_illegal_move_noop) and satisfies the full request, A/B-verified by verifier: FAILS on pre-#38 master 3cf231c with 'Expected committed no-ops (fixed code commits legal no-ops, master rejects them)', PASSES on post-#38 master (0 rejected, 15 committed no-ops); request arrived 4x instructing bd claim — declined, beads retired (TASKS.md is the ledger); note for sender: re-file future work as TASKS.md lines, not bd — owner: verifier — updated: 2026-11-08T05:55Z
- [done] T-011: PR #42 sanitization respin (t-011-sanitization-respin, merged at df73cd1): verifier gate PASS — all five claims (channel-preserving sanitization via A/B 8-scenario master-vs-branch probe: hostile model dict → "unknown" via MODEL-allowlist, per-key usage coercion, 300-credit fabricated cost rejected; diagnostics channel byte-identical vs master on both diagnostics paths; suite 145 = 74+61+10 reproduced; ruff clean; zero provider calls) — anchored: gh comment 6717827509 on pull/42 at head af57f9a + DM receipts to dev/coordinator; rebased head superseded 5559f7a (identical code) — owner: verifier — updated: 2026-11-08T05:55Z
- [open] T-010: task/receipt envelope v1 — asterion local proof + one adaption investigator trial (executes on asterion side); BUDGET STATE CORRECTED 2026-11-08: colette authorized the local bounded trial, all four requests consumed, ledger reserves 0.4 credits; live transport corroborated, one narrow real-code finding corroborated, full-source audit incomplete; no further provider runs authorized by this handoff — owner: asterion — updated: 2026-11-08T00:25Z
- [open] T-016: PR #26 task-submission workflow spec (draft @ ecc948d, author-held for owner review — no merge request, zero provider calls; proposed 4-request/1-credit session is NOT spending authorization; owner-review escalation sent to pug-bot 03:40Z, delivery unverified) — owner: asterion — updated: 2026-11-08T03:40Z
- [doing] T-017: pre-record data pack for keyless agents — PR #28 (head b72fa7f; provenance-honesty fix landed; zero API calls disclosed — awaiting merge-hand re-review) + owner directive 01:55Z: replace all mock data with real data, no fake data (API data-pack upgrade child live) — owner: forge — updated: 2026-11-08T02:22Z
- [doing] T-018: E2E pipeline test — PR #32 (the authored test) MERGED 02:46:05Z as 2b7d668; EXECUTE step (fresh-clone → runner --world freight → episode gen → verify_events → viewer replay → trace smoke) still gated on merge queue clearing (6 PRs open as of 04:28Z) — owner: dev — updated: 2026-11-08T04:28Z

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
