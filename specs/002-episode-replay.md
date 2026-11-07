# episode replay / the first observatory

status: accepted

accepted by colette in the coding conversation on 2026-11-07; implementation authorized.

owner: colette · proposed implementer: asterion · task: swarmachines-956

baseline: bb3f87042dfcd3d4ecbe68af293a99580c50d6ec · 2026-11-07

## owner view

- change: a local, offline viewer for one recorded episode, with a scrubbable event timeline and evidence inspection.
- before: the scripted runner emits readable jsonl; understanding a message requires following several separate records by hand.
- after: open a log, move through it, select an agent or message, and inspect the exact records supporting the visible state.
- authority: this bounded viewer slice is accepted; it does not accept the wider experiment design. acceptance applies to this spec revision; runtime changes and research claims remain separately owned.

## context

pug owns the runner; asterion owns this inspection surface. caduceus manages pug's prs. the first integration target is the merged scripted episode, not a second simulator. the viewer should remain useful as the freight world replaces the scaffolding.

sources: [event schema](../runtime/schema/events.schema.json), [scripted sample](../runtime/sample-run.jsonl), [runner](../runtime/runner.py), [turn seam](../openspec/changes/add-turn-seam-event-log/specs/turn-seam/spec.md), and [topology ruling](../openspec/changes/add-turn-seam-event-log/topology-ruling.md). these govern record meaning. older front-door statements that no runtime exists are stale against this baseline.

## scope

in:
- open one local jsonl file; offer a bundled, explicitly labeled scripted sample.
- event stepping, play/pause, event scrubber, and turn navigation.
- message lifecycle, latest recorded observation per agent, disturbances, raw event inspection, and run identity.
- responsive keyboard-operable page, usable directly from a local file without installation.

out:
- live discord, provider calls, uploads, saved browser state, or remote body retrieval.
- a second runner, multi-run comparisons, morphology classification, causal influence scores, or report authoring.
- animated freight movement or reconstructed world state derived from free-form descriptions.

## owner decisions

### proposed first landing

- recommendation: build the evidence-first timeline and message inspector before adding a graph. the initial map can appear as recorded initialization data.
- alternative: begin with a network animation; this costs more and risks making the scaffold look like measured behavior.
- consequence: the first demo proves replay and inspectability; a richer map can follow when the world exports structured state.

## playback contract

1. preserve append order, governed by strictly increasing `seq`, within exactly one `run_id`. never sort by `ts`: the current runner's timestamps can move backward across event categories.
2. the cursor includes its selected record. all observations, messages, disturbances, and summaries derive only from that prefix. rewinding removes later evidence.
3. select a turn at its first recorded event. play advances one event per tick, pauses at the end, and never reruns agents. manual navigation pauses playback.
4. retain `message.sent`, `message.delivered`, `message.seen`, and `message.acted_on` separately. preserve undelivered status and reason. show orphan or unexpected transitions as recorded, with a warning; do not fabricate missing stages.
5. show message bodies only when explicitly present in the record. a `body_ref` remains inert text with “body unavailable”; do not resolve paths or urls.
6. show the initial map as “as recorded at initialization.” show later `world.changed` payloads as records. display `run.end` values under “reported summary,” not independently calculated outcomes.
7. every detail retains `(run_id, seq)`, event type, turn, and raw payload. unknown event types remain inspectable with an unsupported-type label; do not silently discard them.

## first screen

- top: file chooser, sample button, run id, source label, event count, and a persistent scripted-sample caveat when appropriate.
- center: event timeline with cursor, previous/next, play/pause, and turn selector.
- below: agent observation cards and message rows with distinct lifecycle markers; selecting either opens supporting records.
- detail: selected event's readable fields and escaped raw json, with disturbance and world-change records reachable from the timeline.
- no loaded file: explanatory empty state. invalid import: clear line-specific error where possible; retain the previous episode and cursor, paused. successful import: reset to the first event, paused. reload clears imported data.

## import boundary

accept utf-8 jsonl up to 5 mib, 20,000 records, and 10,000 characters per line. reject empty input, malformed json, invalid envelope fields, mixed run ids, and duplicate/decreasing sequences. gaps in sequence numbers are allowed and visibly reported. preserve unknown payload fields.

validate required payload fields for supported lifecycle events before presenting derived lifecycle state; envelope acceptance alone is not full schema validation. render all imported strings as text, never html, executable code, or links. no storage, network requests, telemetry, or arbitrary reference resolution. file size must be checked before reading. imported files and their rendering require focused trust-boundary review before implementation is considered complete.

## change shape

| dimension | changed? | source of truth | proof |
|---|---|---|---|
| user-visible behavior | yes | this spec | browser playback and inspection checks |
| persisted state or schema | no | runtime schema stays authoritative | no write paths; reload check |
| external or provider-visible behavior | no | offline boundary | network observation |
| identifiers, secrets or privacy | yes | local file import boundary | inert rendering; no upload or storage |
| lifecycle or terminal states | yes | playback and import rules | rewind, end, invalid import tests |
| setup, operation or recovery | yes | local-file entry point | clean browser open and reload |
| normative contract or decision | yes | this spec owns viewer semantics only | owner review |
| cross-repository dependency | no | bundled local assets | offline open |

## implementation order

1. fix the prefix-replay model and import validation against the real sample, including malformed and unknown records.
2. build the minimal local-file shell and inert event inspector; connect file loading without network or storage.
3. add cursor controls, message lifecycle and agent observations; exercise rewind and failed-import recovery.
4. verify the browser surface, document operation, then hand over a bounded pr through the existing review route. no runner edits are needed.

likely files: `viewer/replay.cjs`, `viewer/replay.test.cjs`, a browser-compatible export of the same model, `viewer/index.html`, local styling/controller, bundled sample, and focused browser checks. avoid maintaining two replay algorithms.

## done when

- the real 67-event sample loads and every event is reachable in append order, including backward timestamps.
- rewinding before a delivery, disturbance, observation, or run end removes that later evidence from all derived panels.
- both undelivered messages in the sample remain distinct; no later lifecycle stage is implied.
- malformed, mixed-run, oversized and duplicate-sequence inputs fail clearly; unknown types and missing body files remain inspectable without fabricated content.
- markup-like imported text stays literal; body references cause no requests; no imported data survives reload.
- keyboard controls, visible focus, reduced motion, 320px width and 200% zoom remain usable; selection and playback never hide the raw evidence path.
- the page opens offline from its entry file and identifies the bundled sample as scripted scaffolding.

## validation

existing model check: `node --test viewer/replay.test.cjs`.

implementation must add boundary cases above and exercise actual browser loading, controls, rewind, failed import, literal-text rendering, offline behavior, and responsive layout. run the repository documentation checker and `git diff --check` before handoff. python changes, if any become necessary, also require the team's ruff and test gates.

## risks and unknowns

- the current runner uses scripted/randomized observations, acted-on flags and summary values. these are scaffold records, not evidence that messages changed agent decisions or that freight was delivered.
- the 23-event example is hand-authored; the 67-event sample is runner-generated. keep these provenances distinct.
- new runtime records may require new adapters. preserve their raw form until semantics are agreed rather than guessing.
- six provisional model tests exist and passed before this spec; no browser viewer or browser acceptance is complete. those tests do not prove full schema validation.
- board claim acknowledgment is pending; the local board cli is unavailable. do not recreate the team's board.

## open questions

- none for this slice; the owner accepted the timeline-first design.

## review surfaces

[local change atlas](replay-review/index.html) is a generated projection of this spec, with source fingerprint; it accepts nothing. no separate attention-aperture companion is needed for this small slice: its central mechanism is prefix playback, which the bundled cabinet trace does not model. the atlas retains the complete written contract.
