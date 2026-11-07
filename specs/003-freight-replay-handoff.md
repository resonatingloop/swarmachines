# freight replay / prove the handoff

status: accepted

accepted by colette in the coding conversation on 2026-11-07; bounded implementation authorized.

owner: colette · proposed viewer implementer: asterion · runtime owner: pug

## owner view

- change: prove the viewer can inspect a world-backed freight episode without upgrading scaffold records into research evidence.
- before: the merged viewer reads one episode and preserves prefix evidence; the candidate freight log already parses.
- after: one pinned freight fixture has explicit provenance, regression checks and browser replay proof; any missing runtime evidence remains visibly missing.
- authority: this bounded viewer handoff is accepted. it does not authorize runtime repairs, approve pr #6, or accept the freight model.

## context

pr #9 merged as `19fc349f85833b901f5b5ec9e4f65286440d4c8f`. caduceus's review on head `4463b45` reports independent import/render review clear and reruns passing; formal github approval was unavailable because the authenticated identity was also the author.

read-only inspection of open [pr #6](https://github.com/resonatingloop/swarmachines/pull/6) pinned to `46d54a31f45b43ec6c190a5e7badfad29a2d076c` found:

- `runtime/freight-episode.jsonl` parses unchanged with the current viewer: 394 records, 16 turns plus initialization, 71 sent, 71 delivery records, 51 seen, 23 acted-on records, 27 committed and 4 rejected actions.
- fixture sha256: `f4b6a3432a69577074d4c38a826d8160c793a5b83ba73f654a73a9aa1100dcad`.
- the inspected `runtime/runner.py` has no freight-world integration: observations and action legality remain randomized, commits report “freight queued,” and lines 583–593 draw delivery totals from the rng.
- `runtime/freight_world.py` defines world state and statistics, but its existence does not establish that this runner uses them. the candidate fixture's world-shaped observations do not establish reproducibility from this inspected runner.
- only one `world.changed` event exists, at initialization. the log cannot support reconstructing subsequent cargo movement.

these findings apply to that exact candidate revision, not future updates. follow-up implementation evidence: the inspected standard-library runner was executed in isolation with the manifest command and reproduced the candidate byte-for-byte. this proves reproducibility, not world integration. the viewer parser also accepts the downloaded log.

## scope

in:
- refresh the runtime handoff at a pinned reviewed revision; compare source, fixture and rerun command.
- add the verified fixture and provenance manifest to the viewer's regression inputs, with its source commit and hash.
- exercise all events, turn navigation, lifecycle evidence, rewind and reported summary in model/browser checks.
- make only demonstrated compatibility fixes; retain one replay algorithm and existing import protections.

out:
- runtime repair, freight simulation in the viewer, provider calls, morphology classification, or matched-run comparisons.
- replacing the bundled default sample before the provenance gate clears.

## owner decisions

### evidence before animation

- recommendation: keep the current viewer semantics and require the runtime handoff below before labeling an episode world-backed.
- alternative: add the current candidate as an explicitly unverified compatibility fixture only.
- consequence: compatibility can progress now, but an experiment demonstration waits for evidence that the world drives actions and outcomes.

## handoff contract

runtime supplies a pinned commit, exact fixture, invocation, seed, turn count, topology/disturbance configuration and dependencies. verification must show that observations come from the world, actions validate and mutate that world, and end totals come from its state. rerunning in an isolated environment must reproduce the artifact or explain declared nondeterminism. no provider call is needed for this scripted slice.

the viewer does not invent missing snapshots. keep initialization labeled as recorded initialization, later changes as raw records, and end values as reported summary. missing message bodies stay unavailable. source changes invalidate the old fixture/hash review.

## change shape

| dimension | changed? | source of truth | proof |
|---|---|---|---|
| user-visible behavior | yes | fixture provenance label | browser inspection |
| persisted state or schema | no | existing runtime event contract | no schema or storage edits |
| external or provider-visible behavior | no | offline viewer | no network/provider calls |
| identifiers, secrets or privacy | no | existing import boundary | inert rendering regression |
| lifecycle or terminal states | no | accepted viewer spec | prefix and rewind checks |
| setup, operation or recovery | yes | reproducible fixture handoff | documented rerun and hash |
| normative contract or decision | yes | this spec's evidence gate | owner acceptance |
| cross-repository dependency | no | same repository runtime | pinned local artifact |

## implementation order

1. recheck pr #6 and collect a corrected, reviewed runtime handoff; do not copy a moving branch as evidence.
2. verify source-to-event correspondence and rerun provenance in isolation; report discrepancies to the runtime owner.
3. add the pinned fixture, provenance manifest and regression cases; make minimal viewer compatibility fixes only if tests demonstrate a gap.
4. inspect real browser playback and deliver a separate pr for review.

likely changes: viewer fixture/provenance files, `viewer/replay.test.cjs`, `viewer/browser-check.mjs`, and viewer operation notes. runner files remain owned by the runtime lane.

## done when

- the fixture is traceable to a reviewed runtime revision and a reproducible invocation.
- source inspection and execution support world-backed observations, state transitions and reported totals.
- every record is reachable; rewinding removes later evidence, including the end summary.
- message transitions and missing bodies retain their exact meanings; no new world animation is inferred.
- model and browser checks pass against both the existing scaffold and the new fixture; provenance differences are explicit.

## validation

run `node --test viewer/replay.test.cjs` and `node viewer/browser-check.mjs` after adding fixture cases. run the runtime owner's documented scripted invocation in isolation only after inspecting its setup and side effects. compare artifact hashes. run documentation checks and inspect the complete diff before handoff.

## risks and unknowns

- pr #6 remains open and may change; this candidate is not accepted freight evidence.
- the initial planning pass performed no runtime execution; follow-up implementation proof is recorded in the fixture manifest and viewer notes.
- actual browser-menu zoom, screen-reader behavior and large-log responsiveness remain separate existing viewer limitations.

## open questions

- runtime handoff prerequisite: which reviewed revision actually connects the world to the runner and generates the supplied episode? the inspected revision does not.

## review surfaces

[change atlas](freight-replay-review/index.html) provides the complete review projection. no separate attention-aperture companion is added: this small provenance gate does not benefit from its append-record cabinet model. the markdown remains canonical.
