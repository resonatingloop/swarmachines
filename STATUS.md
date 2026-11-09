# swarmachines / status

> continuity role: operational checkpoint
> status: task10 response/langfuse repair implemented offline on candidate branch; exact-head review and every external call remain gated; dataset-pack lane core merged (#64 @ d95de98), beads-dir anchor docs merged (#72 @ 1dc0c38), model-evidence causal seal merged (#71 @ f6196f6); event-log seal merged (PR #46); report synthesis pending
> last verified: 2026-11-08 (checkpoint merge window through 20:07:52Z; query origin/master for the current tip)
> owns: exercised state, active work, gaps, and the next useful action
> update when: a meaningful stopping point changes these facts; replace this checkpoint in place

## event-log seal (swarmachines-i64 — merged via PR #46)

**event-log seal (swarmachines-i64, merged 2026-11-08 as 4ea45df)**: every runner-appended
record now carries a sha256 `chain` hash (canonical JSON, genesis bound to
run_id — recomputable from the log alone), the log closes with a `run.seal`
certification record (terminal chain + record count + alg, strict schema
shape), appends after the seal are refused, and the offline analyzer
verifies the seal when present: edit/insert/remove of any chained record is
rejected categorically; legacy unsealed logs stay byte-compat and measure
identically. openspec change `add-eventlog-seal`. suites re-verified at the
#46 landing: runtime 28/28 (includes the e2e pipeline test; 4 new
seal tests), analysis 17/17 (7 new), control_plane 74 OK, viewer 82 cjs +
46 esm = 128 pass (`node --test`). repo-wide ruff re-verified at the #50
landing: 31 pre-existing
scripts/ findings + 4 format-dirty scripts, all claimed by open PR #43.
sample-run.jsonl stays legacy (byte-compat fixture).

## verified checkpoint

**checkpoint merge window**: 2026-11-08 01:26Z–20:07:52Z; the recent merge ledger below records the attested sequence. query origin/master for the current tip rather than treating this document as a live pointer.

**sanitization respin (2026-11-08)**: delegation receipts now persist the model name only when the provider reports the fixed `glm-53-flash` constant (otherwise `unknown`) and validate each usage token count independently within 0..10^9, estimating cost only from a complete valid pair. This is the owner-ruled redo of the db2bc17 sanitization on a channel-preserving base: the bounded response-diagnostics channel from pr #22 (fixed reason codes, allowlisted status, receipt usage fallback) is untouched and no channel was removed. The sanitized delegation harness sha256 is registered in the read-only projection's recognized producers next to the legacy hashes, so budget provenance stays known for new receipts while prior receipts still project. 160 offline tests passed at its df73cd1 merge across control_plane, runtime and viewer (74+24+62) with mocked sdks and zero provider calls; control_plane ruff check and format are clean. Landed via PR #42 (2026-11-08 05:52Z).

job-evidence slice: spec012 mapping approved; settled policy base `18218e706cf950c89161b6588166d14529f76726`. Versioned job instrumentation and an offline analyzer are implemented; 28 focused tests, legacy 24/24 runtime tests and 82 viewer tests pass. Noninterference against the pinned base and a 386-record
integration reconciliation pass (fixture `spec006-seed42-ring-mutec-t8`:
all records parse, 4/4 delivered jobs reconciled; recorded in pr #34);
independent review pending. [operations](analysis/README.md). No formal
experimental batch or provider calls.

**merge ledger (recent window ending 20:07:52Z)**: the recent merges below are an attested window, not a live count or current-tip claim; this is not the complete merge history since c5899d8:
- PR #44 (839ab6a): refactor: collapse nested disturbance guards in can_communicate (prune-guard-collapse)
- PR #72 (1dc0c38): chore(beads): anchor .beads control files in-repo (payload excluded; dolt remote is the data plane)
- PR #64 (d95de98): feat(dataset_pack): implement tasks 1-9 — HF dataset packager
- PR #71 (f6196f6): fix(dataset_pack): seal model evidence causally
- PR #50 (4e63cee): docs: refresh STATUS.md checkpoint for post-#49 master tip
- PR #49 (3f475e4): docs: refresh STATUS.md checkpoint for post-#47 master tip
- PR #28 (3491180): feat(data): real Adaption-generated data pack with full provenance (38 seed artifacts, per-run logs)
- PR #39 (572612a): feat(spec006): seed-42 formal pair — mesh vs ring under peer-mute:8:c (frozen manifest)
- PR #37 (12b819d): docs: prepare seed-42 candidate manifest and readiness gate
- PR #30 (3cf231c): feat: Langfuse-compatible execution tracing layer
- PR #36 (3834c9b): chore: mark runtime/freight_world.py executable (EXE001)
- PR #38 (7acd2a7): fix: freight act-phase mislabel - legal no-ops logged as action.committed
- PR #41 (e42b23d): docs: refresh STATUS.md checkpoint for tip 7acd2a7
- PR #42 (df73cd1): T-011: channel-preserving model/usage sanitization (swarmachines-t011)
- PR #46 (4ea45df): feat(runtime): seal the EventLog against policy-level fabrication (swarmachines-i64)
- PR #47 (ba409be): docs: refresh STATUS.md checkpoint for post-#46 master tip

**closed superseded work**:
- PR #6: CLOSED — feat: freight-in-the-fog world integration (day-1 slice) — superseded by the merged freight-world wiring in PR #29 + subsequent fixes
- PR #35: CLOSED — docs: refresh STATUS.md checkpoint for post-#31 master tip — superseded by this regeneration
- PR #40: CLOSED — chore: mark swarmachines-fvh done on ledger (PR #15 merged) — ledger correction only, moot after TASKS.md retirement

**data pack verified**: `data/MANIFEST.md` records 38 artifacts (26 model-generated, 12 team-authored) from run gen-full-20261108; `data/runs/gen-full-20261108/` contains logs, receipts, and run.json with full provenance.

**report skeleton ready**: `docs/report/README.md` + `docs/report/report-skeleton.md` mirror the official Apart template (8pp cap, abstract 150-250 words, required Limitations/Dual-Use appendix stubbed). report prose belongs to colette; the scaffold task and report authorship are distinct.

**measurement readiness**: `docs/measurement-readiness.md` is a historical assessment pinned to pr #29 (`1c3fd50`), not a current policy blocker. pr #33 added the message-sensitive `route-gossip-v1` policy; pr #34 added versioned job evidence and the offline analyzer (`analysis/README.md`). the seed-42 pair uses that runtime at `0f84075`. report interpretation and measures framing remain separate from implemented instrumentation. the candidate packet in `experiments/pilot-42/` retains its historical pending-gate wording; use `runs/spec006/FROZEN-MANIFEST.md` for the recorded pair, without retroactively relabeling the candidate.

**board state**: attributed room readback at 2026-11-08T20:20:00Z: 82 total / 8 open / 9 in_progress / 65 closed. this is an attributed snapshot, not a local live-board verification; later filings may change the count. beads is authoritative.

**pr snapshot**: open-pr state observed at 2026-11-08T20:20:00Z. query github for current state; merging this document does not make the snapshot a live count. Gate-complete items at stated heads: #56 219a100 (rebased post-checkpoint; gate status TBD), #65 fe83db9 (rebased post-checkpoint; gate status TBD). Other open: #57 61ef9fa, #59 9b939f5, #66 1ff9857, #67 77cca41, #68 a6fc13e, #70 48bb464, #73 9f3a88c (this PR; docs-only, head at content freeze), plus rebased #56/#65 at current heads above (not gate-complete). #44 merged at 839ab6ac42ae7d0c3552d1d50b3de997d00bf6c8 (20:07:52Z).

**regression test filed**: swarmachines-oe3 — act-phase no-op labeling: freight acceptance tests pass on BOTH the pre-#38 mislabeled code and fixed code; needs a test that FAILS on false action.rejected for legal no-ops and PASSES on master.

## working now

- task10 repair candidate: 4,096-token visible-response mode, bounded response
  diagnostics, fail-closed empty/incomplete handling, langfuse 5.x generations
  with hashes-only export and strict flush, explicit private credential-file
  loading, one source-linked `model.call.failed` event per rejected attempt,
  pre-seal schema validation, and pre-package seal verification
- freight-world integration merged (PR #29 + PR #38 fix-forward); act-phase legal no-ops now correctly labeled action.committed
- spec006 formal pair recorded (PR #39): seed-42 mesh vs ring under peer-mute:8:c with frozen manifest
- tracing layer wired (PR #30): Langfuse-compatible tracer with --trace flag, offline default byte-identical
- data pack (PR #28): 38 seed artifacts with provenance for keyless teammate agents; these are experiment inputs, not observed results
- dataset-pack lane core merged (PR #64 @ d95de98): HF dataset packager tasks 1-9 complete
- beads-dir anchor docs merged (PR #72 @ 1dc0c38): .beads control files anchored in-repo (payload excluded; dolt remote is the data plane)
- model-evidence causal seal merged (PR #71 @ f6196f6): dataset_pack evidence sealing
- report skeleton scaffolded (docs/report/): structure only, colette owns report prose

## incomplete or broken

- task10 external proof is intentionally unrun: no langfuse authentication,
  synthetic trace, adaption diagnostic call, continuation of runs 005–015,
  packaging, upload, or publication is authorized by the offline candidate
- task10 exact-head independent review is pending a commit/push/pr gate; pr #75
  is a separate implementation and is not the accepted candidate described here
- local beads writes are blocked by a project-id mismatch between workspace
  metadata and the authoritative database; the existing board remains readable
  and no bootstrap, fix, init, or sync was attempted
- report content pending (colette owns; skeleton ready, drafting unstarted)
- measures framing (T-007 / swarmachines-19m): accepted measure definitions — observable-source mapping review unclaimed
- regression test gap (swarmachines-oe3): act-phase fix needs discriminating test (FAILS on pre-#38, PASSES on master)
- viewer replay of real recorded episode (swarmachines-956): day-1 checkpoint unclaimed

## active work

- pug reports the prior integration/data/pair sequence complete after #64/#71/#72; report synthesis is the next main deliverable. follow-up regression coverage and measurement interpretation remain explicit work below
- report content: colette owns; skeleton in docs/report/ ready for drafting (deadline: Sunday Nov 8, 11:59 PM AoE)
- T-007: measure definitions review — huddled 01:14Z to caduceus, unclaimed
- swarmachines-oe3: regression test for act-phase no-op labeling — filed, unclaimed

## next useful action

colette drafts report prose from `docs/report/report-skeleton.md`. use the recorded pair in `runs/spec006/` and reconciled job measures as evidence, keeping the single scripted scenario, absent no-mute control, and unestablished coordination benefit explicit. describe runtime/tracing as methods and the generated data pack as seed material, not experimental results. coordinate measures framing and the discriminating no-op regression test with their current beads owners before claiming either task.

## re-entry notes

- checkout: use your own isolated clone of this repository; do not reuse another agent's working directory. the author's `/workspace/clones/dev-status-refresh` is host-specific, not a universal entry point.
- board reads: use the configured beads store for your host. pug's store is `/workspace/.beads-store`; do not initialize a replacement board or assume that path exists elsewhere.

## provenance

this checkpoint refreshed during the 20:07:52Z checkpoint merge window, extending the prior regeneration chain through PR #44. supersedes earlier rotating snapshots in the PR #35/#47 chain. zero model/API/provider calls — docs-only refresh.
