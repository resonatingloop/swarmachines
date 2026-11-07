# paired episodes / what changed in the record?

status: accepted

accepted by colette in the coding conversation on 2026-11-07; all recommendations approved for implementation.

owner: colette · proposed implementer: asterion · 2026-11-07

## owner view

- change: load two local episodes and inspect their recorded communication, observations and actions at the same logical turn.
- before: the observatory inspects one episode; comparisons require remembering one record while opening another.
- after: a shared turn control keeps two labeled evidence panes aligned, with per-turn record counts and visible configuration differences.
- authority: this is an accepted viewer slice. it does not certify an experimental match, infer causal effects, or accept a runtime/provider change.

## context

build on the accepted [single-episode contract](002-episode-replay.md), its shared replay model in [replay.js](../viewer/replay.js), the [event schema](../runtime/schema/events.schema.json), and the [freight provenance gate](003-freight-replay-handoff.md). pr #9 delivered single-episode inspection; pr #11 carries compatibility-only freight proof. the comparison can work on scripted records while world-backed outcomes remain gated.

“paired” means two chosen files. “matched experiment” requires controlled generation and provenance beyond what these event envelopes currently prove. seed-based run ids may collide across conditions; neither a shared run id nor a shared seed establishes a match.

## scope

in:
- separate offline comparison entry point, sharing the existing parser and snapshot logic.
- independent left/right local file loading, visible source labels and a common logical-turn selector.
- per-turn communication/action record counts, agent observation inspection, disturbance records, and exact raw evidence on each side.
- a configuration comparison showing known equal, different, missing, or conflicting fields.

out:
- provider calls, live runs, uploads, storage, multi-run statistics, outcome scoring, causal labels or automatic morphology classification.
- inferred message/action correspondence across runs, dynamic cargo reconstruction, or automatic certification of an experimental match.
- changing the existing single-episode page or adding a world-backed outcome panel before the freight handoff gate clears.

## owner decisions

### align at turn end

- recommendation: each shared turn selects the last recorded event at or before that turn on each side. show per-turn records beside cumulative prefix state.
- alternative: align individual event indices; this falsely couples unrelated records when traffic counts differ.
- consequence: this first slice compares logical-turn boundaries. within-turn synchronization and autoplay are deferred; raw records remain independently inspectable.

### descriptive comparison first

- recommendation: keep all valid pairs inspectable, with visible mismatches and unknown provenance. call the page “paired episode comparison.”
- alternative: refuse every pair with incomplete provenance; current scaffold logs would make the tool mostly unusable.
- consequence: the page makes recorded differences legible without deciding whether a causal experiment is valid.

## comparison contract

1. retain left/right slot identity independently from `run_id`. identify evidence by `(slot, run_id, seq)`; same ids across files never merge records or messages.
2. use the sorted union of recorded turn numbers, including initialization. event order within each file remains append order. comparison requires nondecreasing turn numbers; reject decreasing-turn files with a clear comparison-specific error while leaving single-episode parsing unchanged.
3. at selected turn T, the cutoff is the final event with turn <= T. if none exists, the side has an empty prefix; never borrow a future observation. if the file has no events at T but has later turns, label “no records for this turn.” if T exceeds its last turn, label “beyond recorded horizon.”
4. missing-turn and beyond-horizon per-turn counts are unavailable, not zero. previous observations may remain visible only as explicitly carried-forward records with their original turn and seq. the presence of run.end says the file reports an end; absence does not prove a truncated file, so label it “no run.end recorded.”
5. counts cover records whose turn equals T: sent, delivered with status delivered, delivered with status undelivered, seen, acted_on, action.proposed, action.validated, action.committed and action.rejected. they are event counts, not unique messages, completed jobs or successful decisions. duplicate records, if accepted by the envelope, count as recorded.
6. show right-minus-left differences only when both sides have records at T. use neutral signs/colors; more messages is not inherently better. every count opens its exact contributing events, including a readable empty list for an observed zero.
7. keep agent observations and action records grouped by their recorded agent id within each slot. identical agent labels may be visually adjacent but never establish equivalent roles. preserve missing agents and different observation times. no automatic semantic diff or cross-run action/message matching.
8. show each side's disturbance records through T with original turns; future disturbances stay hidden. a mismatch in disturbance timing is visible, not silently realigned.
9. retain per-side raw inspection and the existing unavailable-body/reference rules. selecting a record changes the detail pane, not the shared turn. moving the turn resets detail selection to an in-prefix record or the empty state, preventing future-evidence leakage.

## configuration and provenance strip

file-level metadata is deliberately separate from cursor-scoped evidence. show filename, run_id, event count, recorded turn range and whether run.end is present. label that range “file coverage,” not elapsed progress.

compare initial run.config payload fields: seed, agents, comm_topology, disturbance_schedule and delivery_config_sha. compare JSON structurally with object-key order ignored and array order preserved. display absent fields as unknown; distinguish null from missing. multiple run.config records produce a conflict warning and remain independently inspectable rather than choosing a hidden winner. missing config does not prevent raw comparison.

these are logged configuration values, not verified provenance. display a persistent note that runtime revision, model/policy, world initialization and generation controls are not certified by matching these fields. comm_topology or disturbance differences may be the intended treatment; the viewer does not decide. never call delivery_config_sha a physical-world graph hash.

## interaction and recovery

open `viewer/compare.html` directly. left and right file controls each retain the existing utf-8/5 mib/20,000-event/10,000-character-line limits; at most two episodes are held. imported strings remain inert; no network, reference resolution or storage is added.

one loaded side is inspectable with a “waiting for second episode” state; deltas are unavailable. a successful replacement rebuilds the turn union and resets to its earliest turn. failed import preserves both loaded episodes and the selected turn, with a slot-specific error. reset clears both slots; reload does the same. show loading/errors accessibly and guard asynchronous loads so a late file read cannot replace a newer selection.

desktop has two labeled panes; narrow screens stack left then right under the shared turn control, repeating slot identity on evidence. keyboard operation must reach both file controls, the turn selector and contributing records with visible focus. no motion is required.

## change shape

| dimension | changed? | source of truth | proof |
|---|---|---|---|
| user-visible behavior | yes | paired viewer contract | browser comparison checks |
| persisted state or schema | no | existing event schema | no storage or runtime schema edits |
| external or provider-visible behavior | no | offline boundary | network observation |
| identifiers, secrets or privacy | yes | slot-scoped identities and two local files | collision and inert-text tests |
| lifecycle or terminal states | yes | empty/missing/horizon/import states | prefix and recovery tests |
| setup, operation or recovery | yes | compare.html entry point | offline open/reset/reload |
| normative contract or decision | yes | this spec's alignment rules | owner acceptance |
| cross-repository dependency | no | shared local viewer model | no external runtime dependency |

## implementation order

1. add pure comparison helpers for turn cutoffs, slot identity, per-turn counts and configuration status; test missing turns, unequal horizons and duplicate ids before building UI.
2. add the offline dual-file shell with safe import, independent error handling and shared turn selection; reuse parser and prefix reconstruction.
3. render configuration, record-count contributors, observations/actions and raw details with explicit provenance and horizon labels.
4. run regression and browser proof on authored boundary fixtures and the existing scripted sample; keep fixtures labeled illustrative. document operation and use the standing commit/pr/caduceus handoff.

likely changes: `viewer/compare.html`, comparison controller/styles and pure helper module, focused tests/fixtures, browser checks and viewer notes. keep the single-episode path working; do not fork its parser or change the runner.

## done when

- same run/message/action ids in both files stay separate and inspectable by slot.
- unequal event counts align by logical turn, not sequence position or timestamp.
- rewind removes later evidence from counts, observations, disturbances and raw detail selections on both sides.
- missing turns and shorter horizons produce unavailable comparisons, not artificial zero differences; carried-forward observations disclose their age.
- every count agrees with its contributing source records; unknown config values never become “equal.”
- config differences, missing agents and disturbance timing differences remain visible without causal language.
- malformed and decreasing-turn imports preserve the previous pair; late reads cannot overwrite newer selections; reload/reset clears both files.
- both single and paired pages pass offline, inert-text, keyboard, 320px, zoom-reflow and no-storage/no-network checks.

## validation

extend `node --test viewer/*.test.cjs` with comparison cases. keep `node viewer/browser-check.mjs` green and add an equivalent comparison-page browser check. validate actual file inputs, both slot replacement paths, shared-turn controls, raw contributors and reset. run documentation checks, atlas freshness and full-diff review before handoff. no provider expenditure or runtime repair is required.

## risks and unknowns

- current logs do not establish experimental matching or causal influence. equal logged fields must not be presented as proof of control.
- long episodes can make prefix reconstruction and DOM lists expensive; bound visible record lists with access to every contributor, and test representative upper limits before claiming large-log support.
- world-backed freight outcomes remain a separate runtime dependency; this slice can finish without inventing them.
- no paired-view implementation or browser proof exists yet.

## open questions

- none; end-of-turn alignment and descriptive comparison were accepted.

## review surfaces

[change atlas](paired-replay-review/index.html) projects the complete draft and displays its source fingerprint. a separate attention-aperture companion is omitted because its bundled instruments do not model paired temporal comparison; no artificial append-record trace is substituted. this markdown owns the proposed contract.
