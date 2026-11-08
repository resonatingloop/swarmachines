# switchboard / worker receipts in view

status: draft

owner: colette · proposed implementation: asterion

## owner view

- change: add a read-only local worker-attempt panel to the existing frozen switchboard.
- before: the board shows ledger claims and github facts; private worker receipts and trial reservations require separate inspection.
- after: a new capture shows assignments, recorded outcomes, bounded usage and local budget accounting together, with unknowns and provenance visible.
- authority: owner requested this saved spec. implementation is not approved. this spec authorizes no provider request, new trial budget, task dispatch or source-state mutation.

## current ground

base inspected: `984448a`, containing the observer, delegation queue and smoke
outcome correction. [observer operations](../control_plane/README.md) owns
capture behavior; [delegation operations](../control_plane/DELEGATION.md) and
[spec008](008-delegation-roundtrip.md) own worker execution semantics.

observed private trial evidence contains four live attempts: failed, completed,
failed, completed. a separate offline proof also exists and must remain clearly
offline. the live ledger records four requests and 400,000 microcredits reserved
(0.4 credits); one request has unknown usage. these are acceptance examples,
not constants to hardcode or private fixtures to commit.

provider model/usage sanitization is a separate team follow-up. this reader must
validate its own projection, including older receipts; do not depend on that
follow-up landing or rewrite the queue to fit this spec.

## recommended decisions

1. explicit opt-in: add `--worker-state-dir PATH` to the observer. omission
   preserves the existing board and labels worker evidence “not supplied.”
   alternative: autodiscovery; rejected because it obscures private input scope.
2. keep worker attempts in their own panel. task ids do not automatically join
   ledger ids, PRs, owners or review verdicts. alternative: fuzzy matching;
   deferred because a plausible match is not provenance.
3. display a frozen capture with a visible capture time and source revision.
   alternative: polling; deferred because this slice changes visibility only.
4. show a known-usage cost subtotal and its coverage, separately from local
   reservations. alternative: one “spent” total; rejected because first-attempt
   usage is unknown and account billing was not observed.

accepting this spec accepts those recommendations. no unresolved product choice
is required before acceptance; implementation and independent review remain gates.

## in scope / out of scope

in: optional local queue reader, bounded projection, snapshot format update,
script-free board panel, fictional test fixtures, operational documentation.

out: provider calls; raw model answers, prompts or source text in captures;
retry/cancel/dispatch buttons; leases, recovery or migration; background loops;
account balance lookup; experimental agent changes; remote receipts; automatic
ledger reconciliation, task closure or merge approval.

## read boundary

use a dedicated reader, never instantiate `delegation.Queue`: its constructor
can create and modify state. open the existing database read-only and query-only;
never create a missing database, alter permissions, initialize tables, checkpoint
WAL, vacuum, migrate or repair. reject symlink inputs and unexpected schemas.

read budget, acknowledgments and terminal receipt metadata in one bounded SQLite
read transaction. preserve a consistent local view; github and ledger sources
remain separately timed and are not an atomic distributed snapshot. use a short
busy timeout, bounded query time and a 1,000-job ceiling; fetch one additional
row to detect truncation. cap each encoded packet/receipt read at 96 KiB and
aggregate scanned payload at 8 MiB. oversized/invalid entries produce categorical
diagnostics, not raw exception strings or silently successful empty data.

opening a database with a live writer must not modify source database/WAL content
or create/delete source sidecars. if that cannot be guaranteed for a supported
journal mode, show “worker source unavailable” rather than falling back to a
writer-capable connection. test both rollback-journal and active-WAL cases.

unavailable, not supplied, available-empty and truncated are distinct states.
a worker-source failure must not suppress the ledger/github portions of the board.
no source path is serialized into the capture; a generic source label, read time
and schema/version information identify provenance without exposing private paths.

## projection contract

snapshot v2 adds a `workers` section; no queue schema change. the renderer accepts
existing snapshot v1 with worker evidence “not supplied.” unsupported future
snapshot versions are refused explicitly. private output protections and the
new-directory/no-overwrite rule remain in force for both HTML and JSON.

project only:

- task id, attempt id, worker id and mode (offline/adaption), validated against
  existing bounded identifier rules;
- recorded state (running/completed/failed), packet hash, optional result hash,
  acknowledged/completed timestamps, and source git revision when valid;
- a fixed model label only when it matches the supported model; otherwise unknown;
- nonnegative bounded integer input/output tokens, each independently unknown
  when absent/invalid; boolean values are not integers for this purpose;
- fixed error category/status labels from an allowlist; arbitrary provider
  strings become unknown, never escaped-but-still-disclosed raw text;
- persistent request count and reserved microcredits from the budget row.

never export packet objective, expected deliverable, source label/text, model
answer, raw error, credential, claim token, arbitrary receipt extras or private
filesystem paths. validate identity/hash consistency across job/ack/receipt before
using a terminal result. invalid evidence is labeled invalid, never “completed.”
a hash identifies bytes; it does not prove a finding correct.

running means a persisted nonterminal claim, not a live heartbeat. completed means
accepted transport output, not task correctness, review approval or merged code.
failed is not retryable by a board action. preserve the original evidence rather
than revising a historical outcome based on a later trial.

## accounting and limits

show requests used against the configured trial limit (currently 4), and reserved
credits separately from the reservation ceiling (currently 1). label these limits
as the reader's known harness configuration, not immutable historical fields or
an account quota. if capture cannot establish compatible configuration, show
limits/remaining allowance as unknown. do not publish the owner's account balance.

remaining request allowance is `max(0, limit - used)`; over-limit data is a
diagnostic, not a negative allowance. neither remaining reservations nor credit
balance creates permission for another request. include offline attempts without
charging them to the live request count; surface discrepancies rather than
silently deriving budget counters from displayed rows.

for valid live token pairs, recompute estimates using the explicitly dated model
rate basis already documented in delegation operations. include known usage from
failed receipts. never trust an arbitrary stored cost or floating-point special
value. use decimal arithmetic; label unknown model/rate/usage as unestimated.

show estimated subtotal, known-usage attempts / total live attempts, and unknown
count together. the four-attempt acceptance example has 3/4 known usage and an
estimated subtotal of 0.0016241 credits, excluding the first attempt. actual billed
spend remains unknown. truncation makes any derived subtotal partial and counts
lower bounds; the database budget row is still presented separately if valid.

## implementation sequence

1. implement the isolated read-only boundary and fictional fixtures first;
   prove no source-state changes and no writer/provider invocation.
2. validate and project only the allowed fields; prove hostile canaries cannot
   reach either JSON or HTML and malformed evidence remains visible as invalid.
3. extend snapshot/rendering compatibly; keep ledger/PR and worker claims separate.
4. add accounting with explicit estimate coverage and limit provenance.
5. exercise desktop, 320px, keyboard and local-file/offline behavior; capture the
   existing private trial once without new provider activity, then hand off for
   independent review. no public/private trace copying into the repository.

## acceptance and proof

- fictional fixtures cover two completed/two failed live attempts, an offline
  attempt, unknown usage, missing/locked database, malformed/oversized receipts,
  duplicate/mismatched identities, arbitrary model/error strings and truncation.
- a canary in every excluded field is absent from both exported artifacts.
- before/after hashes, sizes and directory inventories prove no source content
  or sidecar mutation during capture; a concurrent writer can keep operating.
  filesystem access-time updates are not treated as content mutation.
- real local trial capture shows four live requests used, 0.4 reserved credits,
  two completed/two failed live outcomes and 3/4 known-usage coverage. the offline
  proof is counted separately. zero provider calls and zero task transitions.
- absent worker input preserves old-board behavior; snapshot v1 remains readable.
- 320px reflow, keyboard reading, escaped script-free HTML, no external assets,
  no network requests on page open, and no browser storage writes are checked.

planned checks: `python3 -m unittest control_plane.test_observer control_plane.test_delegation control_plane.test_worker_projection -v`, scoped ruff, existing
`node control_plane/browser-check.mjs CAPTURE/index.html` extended for the worker
panel, and atlas freshness. the new test module and reader are proposed, not built.

## change shape

| dimension | changed? | source of truth | proof |
|---|---|---|---|
| user-visible behavior | yes | worker panel in frozen board | rendered fixture/capture checks |
| persisted state or schema | yes | snapshot v2 only; queue unchanged | v1 compatibility and no-write tests |
| external or provider-visible behavior | no | existing github reads only | provider/dispatch invocation traps |
| identifiers, secrets or privacy | yes | strict projection allowlist | hostile canaries in HTML and JSON |
| lifecycle or terminal states | no | existing persisted queue states | no mutation or inferred transitions |
| setup, operation or recovery | yes | explicit optional source flag | missing/locked/old-schema tests |
| normative contract or decision | yes | this draft projection contract | owner acceptance before implementation |
| cross-repository dependency | no | same repo, separate local queue input | no teammate host/transport changes |

## risks and review surface

main risks: exposing private text through convenient JSON passthrough, implying
billing from reservations, interpreting stale claims as live workers, and SQLite
side effects under concurrent access. independent review must examine those
boundaries. the sanitization follow-up may change receipt shape; compatibility
must be tested against the exact version selected for implementation.

[change atlas](worker-receipt-review/index.html) is the full review projection.
a separate attention-aperture companion is omitted: this small read-only
projection has neither a supported append-record trace nor a dense phase map
that would add information beyond the atlas. the spec remains canonical.
