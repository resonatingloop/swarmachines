# swarmachines / status

> continuity role: operational checkpoint
> status: event-log seal implemented on branch swarmachines-i64-eventlog-seal (fabrication-detectable logs); formal protocol accepted; seed-42 pair recorded; report synthesis pending
> last verified: 2026-11-08 (branch worktree at origin/master e42b23d + seal)
> owns: exercised state, active work, gaps, and the next useful action
> update when: a meaningful stopping point changes these facts; replace this checkpoint in place

## branch checkpoint (swarmachines-i64 — event-log seal)

**event-log seal (swarmachines-i64, this branch)**: every runner-appended
record now carries a sha256 `chain` hash (canonical JSON, genesis bound to
run_id — recomputable from the log alone), the log closes with a `run.seal`
certification record (terminal chain + record count + alg, strict schema
shape), appends after the seal are refused, and the offline analyzer
verifies the seal when present: edit/insert/remove of any chained record is
rejected categorically; legacy unsealed logs stay byte-compat and measure
identically. openspec change `add-eventlog-seal`. suites on this branch:
runtime 28/28 (4 new seal tests), analysis 17/17 (7 new), control_plane 74
OK, viewer 62, e2e pipeline PASS, ruff check+format clean. sample-run.jsonl
stays legacy (byte-compat fixture).

## verified checkpoint

**master tip**: `7acd2a7` — Merge pull request #38 from resonatingloop/t-006-freight-residue (fix: freight act-phase mislabel - legal no-ops logged as action.committed)

**sanitization respin (2026-11-08)**: delegation receipts now persist the model name only when the provider reports the fixed `glm-53-flash` constant (otherwise `unknown`) and validate each usage token count independently within 0..10^9, estimating cost only from a complete valid pair. This is the owner-ruled redo of the db2bc17 sanitization on a channel-preserving base: the bounded response-diagnostics channel from pr #22 (fixed reason codes, allowlisted status, receipt usage fallback) is untouched and no channel was removed. The sanitized delegation harness sha256 is registered in the read-only projection's recognized producers next to the legacy hashes, so budget provenance stays known for new receipts while prior receipts still project. 160 offline tests pass across control_plane, runtime and viewer (74+24+62) with mocked sdks and zero provider calls; control_plane ruff check and format are clean. Authored on branch t-011-sanitization-respin for review; gates and merge stay with the merge hand.

job-evidence slice: spec012 mapping approved; settled policy base `18218e706cf950c89161b6588166d14529f76726`. Versioned job instrumentation and an offline analyzer are implemented; 28 focused tests, legacy 24/24 runtime tests and 82 viewer tests pass. Noninterference against the pinned base and 386-record integration reconciliation pass; independent review pending. [operations](analysis/README.md). No formal experimental batch or provider calls.

**merge ledger (2026-11-08 01:26Z to 05:07Z)**: six recent merges are listed below; this is not the complete merge history since c5899d8:
- PR #28 (3491180): feat(data): real Adaption-generated data pack with full provenance (38 seed artifacts, per-run logs)
- PR #39 (572612a): feat(spec006): seed-42 formal pair — mesh vs ring under peer-mute:8:c (frozen manifest)
- PR #37 (12b819d): docs: prepare seed-42 candidate manifest and readiness gate
- PR #30 (3cf231c): feat: Langfuse-compatible execution tracing layer
- PR #36 (3834c9b): chore: mark runtime/freight_world.py executable (EXE001)
- PR #38 (7acd2a7): fix: freight act-phase mislabel - legal no-ops logged as action.committed

**closed superseded work**:
- PR #6: CLOSED — feat: freight-in-the-fog world integration (day-1 slice) — superseded by the merged freight-world wiring in PR #29 + subsequent fixes
- PR #35: CLOSED — docs: refresh STATUS.md checkpoint for post-#31 master tip — superseded by this regeneration
- PR #40: CLOSED — chore: mark swarmachines-fvh done on ledger (PR #15 merged) — ledger correction only, moot after TASKS.md retirement

**data pack verified**: `data/MANIFEST.md` records 38 artifacts (26 model-generated, 12 team-authored) from run gen-full-20261108; `data/runs/gen-full-20261108/` contains logs, receipts, and run.json with full provenance.

**report skeleton ready**: `docs/report/README.md` + `docs/report/report-skeleton.md` mirror the official Apart template (8pp cap, abstract 150-250 words, required Limitations/Dual-Use appendix stubbed). report prose belongs to colette; the scaffold task and report authorship are distinct.

**measurement readiness**: `docs/measurement-readiness.md` is a historical assessment pinned to pr #29 (`1c3fd50`), not a current policy blocker. pr #33 added the message-sensitive `route-gossip-v1` policy; pr #34 added versioned job evidence and the offline analyzer (`analysis/README.md`). the seed-42 pair uses that runtime at `0f84075`. report interpretation and measures framing remain separate from implemented instrumentation. the candidate packet in `experiments/pilot-42/` retains its historical pending-gate wording; use `runs/spec006/FROZEN-MANIFEST.md` for the recorded pair, without retroactively relabeling the candidate.

**board state**: pug reported 52 issues at 05:11z: 8 open, 2 in progress, 42 closed (10 active). this is an attributed snapshot, not a local live-board verification; later filings may change the count. beads is authoritative.

**pr snapshot**: #41 (this checkpoint refresh) was the only open pr during review. query github for current state; merging this document does not make its snapshot a live count.

**regression test filed**: swarmachines-oe3 — act-phase no-op labeling: freight acceptance tests pass on BOTH the pre-#38 mislabeled code and fixed code; needs a test that FAILS on false action.rejected for legal no-ops and PASSES on master.

## working now

- freight-world integration merged (PR #29 + PR #38 fix-forward); act-phase legal no-ops now correctly labeled action.committed
- spec006 formal pair recorded (PR #39): seed-42 mesh vs ring under peer-mute:8:c with frozen manifest
- tracing layer wired (PR #30): Langfuse-compatible tracer with --trace flag, offline default byte-identical
- data pack (PR #28): 38 seed artifacts with provenance for keyless teammate agents; these are experiment inputs, not observed results
- report skeleton scaffolded (docs/report/): structure only, colette owns report prose

## incomplete or broken

- report content pending (colette owns; skeleton ready, drafting unstarted)
- measures framing (T-007 / swarmachines-19m): accepted measure definitions — observable-source mapping review unclaimed
- regression test gap (swarmachines-oe3): act-phase fix needs discriminating test (FAILS on pre-#38, PASSES on master)
- viewer replay of real recorded episode (swarmachines-956): day-1 checkpoint unclaimed

## active work

- pug reports the prior integration/data/pair sequence complete after #38; report synthesis is the next main deliverable. follow-up regression coverage and measurement interpretation remain explicit work below
- report content: colette owns; skeleton in docs/report/ ready for drafting (deadline: Sunday Nov 8, 11:59 PM AoE)
- T-007: measure definitions review — huddled 01:14Z to caduceus, unclaimed
- swarmachines-oe3: regression test for act-phase no-op labeling — filed, unclaimed

## next useful action

colette drafts report prose from `docs/report/report-skeleton.md`. use the recorded pair in `runs/spec006/` and reconciled job measures as evidence, keeping the single scripted scenario, absent no-mute control, and unestablished coordination benefit explicit. describe runtime/tracing as methods and the generated data pack as seed material, not experimental results. coordinate measures framing and the discriminating no-op regression test with their current beads owners before claiming either task.

## re-entry notes

- checkout: use your own isolated clone of this repository; do not reuse another agent’s working directory. the author’s `/workspace/clones/dev-status-refresh` is host-specific, not a universal entry point.
- board reads: use the configured beads store for your host. pug’s store is `/workspace/.beads-store`; do not initialize a replacement board or assume that path exists elsewhere.
- pr state: `gh pr list --repo resonatingloop/swarmachines --state open`
- data pack: `data/runs/gen-full-20261108/` — logs/calls.jsonl, receipts/, run.json
- report skeleton: `docs/report/report-skeleton.md` — mirrors official Apart template
- TASKS.md: RETIRED 2026-11-08 — beads is sole tracker; do not edit or recreate

## provenance

this checkpoint regenerated fresh at master tip 7acd2a7. Supersedes closed PR #35 (prune-status-rot2) whose snapshot predated the six merges listed above. Zero model/API/provider calls — docs-only refresh.
