# episode observatory

open `index.html` directly in a modern browser. choose “explore scripted sample”
or open a local utf-8 jsonl episode. no server, install, credentials, network,
or saved browser state is required. keep this directory's assets together.

play advances recorded events; it never runs agents. the slider uses append
order, not timestamps. changing turns goes to that turn's first record.
message and observation buttons inspect exact records without moving the
cursor. reload forgets the episode. failed imports retain the previous episode
and cursor, paused.

the bundled sample comes from `runtime/sample-run.jsonl` at bb3f870 and is
scripted scaffolding, not a completed freight experiment. `body_ref` is shown
as text and never resolved. the viewer validates envelopes and lifecycle
fields, not the complete runtime json schema; unknown types remain inspectable.

## proof and operation

```sh
node --test viewer/replay.test.cjs
node viewer/browser-check.mjs
```

the browser check uses node's built-in websocket and a local chrome executable;
set `CHROME_BIN` if chrome is not at `/usr/bin/google-chrome`. it starts an
isolated temporary profile (created with `mkdtemp` in the system temp dir) and
removes it on exit. screenshots are written inside that temp dir and cleaned up
automatically. it checks offline loading, rewind, keyboard range control,
playback end, import recovery, inert markup, responsive widths, reload, and
absence of remote requests/storage writes. a 720px viewport at device scale 2
is a zoom-equivalent reflow check, not a browser-menu zoom test.

`replay.js` is the shared node/browser model. `replay.cjs` is a compatibility
entry point. `sample.js` is a generated javascript string containing only the
committed fixture; never generate executable assets from a user's imported
file. imported files enter through strict utf-8 decoding, bounded json parsing,
and DOM text nodes. the content security policy blocks connections and inline
script. runtime imports cannot change the policy or resolve references.

independent review of this file-import boundary is still required before
release. browser-menu zoom, screen-reader behavior and very large log interaction
performance have not been verified. no commit, push, release or provider run
is part of this local handoff.

## freight handoff candidate

`fixtures/freight-candidate.jsonl` is pinned to pr #6 revision
`46d54a31f45b43ec6c190a5e7badfad29a2d076c`; the adjacent provenance json records
its sha256, source-file hashes, invocation and evidence limits. it reproduces
byte-for-byte from that runner, but that revision still randomizes observations,
action legality and delivery totals rather than integrating its freight world.
**compatibility-only: not world-backed experiment evidence.**

the ten model tests now check every prefix of this 394-event fixture; browser
checks import it, navigate turns, inspect message evidence and rewind. the
bundled default remains the original scripted sample. no viewer runtime change
was needed. complete freight acceptance waits for a reviewed runtime handoff
that derives observations, state transitions and outcomes from its world.

## paired episode comparison

open `compare.html` directly and choose left/right jsonl files. the shared
turn selector aligns at the last record of each logical turn, while counts
cover only that turn. click a count to inspect its contributors. record lists
paginate at 40 entries; all contributors remain reachable. agent labels and
run/message ids stay scoped to their file slot.

missing turns and shorter horizons yield unavailable deltas, not zeros.
configuration is file-level metadata, separate from cursor evidence; equal
logged fields do not certify a matched experiment. reset/reload clears both
slots. each import uses the original size/utf-8/parser boundaries; comparison
additionally refuses decreasing turn order. failed replacements preserve the
previous pair and turn; older asynchronous reads cannot undo newer selections.

```sh
node --test viewer/*.test.cjs
node viewer/compare-browser-check.mjs
```

comparison browser proof covers offline import, both replacement paths,
configuration differences, colliding ids, missing turns, raw evidence, rewind,
keyboard controls, reset/reload, late-read races, inert text and no remote
requests/storage. desktop and 320px renders were inspected. 720px at device
scale 2 checks zoom-equivalent reflow, not browser-menu zoom. the pure model
also exercises a 20,000-record input; full UI performance at that ceiling and
screen-reader operation remain unverified. no automatic matching, causal
scoring or outcome interpretation is provided.
