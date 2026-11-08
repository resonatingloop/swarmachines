# control plane / prepare, inspect, submit

status: draft

owner: colette · proposed implementation: asterion

## owner view

- change: replace hand-authored task JSON and ad hoc launch commands with a small explicit submission workflow around the existing delegation runner.
- before: packet preparation, exact-source selection, execution and board capture are separate manual operations.
- after: prepare a pinned-source packet and private review artifact, submit exactly that packet under an identified authorized session, and capture the resulting receipt on the frozen board.
- authority: owner requested this spec after the receipt-board slice. implementation is not yet accepted. no new provider requests or budget are authorized by drafting or accepting the implementation spec alone.

## current ground and scope

base: `c5899d8`, merged pr #24. 48 observer/delegation/projection tests and scoped
ruff pass at that landed revision. the original four-request trial is exhausted;
its queue and receipts remain intact. [spec008](008-delegation-roundtrip.md)
owns execution; [spec009](009-worker-receipt-board.md) owns read-only projection.

in: explicit CLI preparation, private review artifacts, hash-bound submission,
a named session manifest, existing worker execution and best-effort post-run board
capture. one local investigator, one attempt per task, existing fixed model and
bounds. no browser write server is needed.

out: autonomous loops, web forms, remote transport, concurrent workers, shell or
file-edit tools for models, approval inferred from Discord, model/rate changes,
output-cap increases, automatic retries, queue resets, account-wide spending
controls or automatic aggregate views across trial sessions.

## recommended decisions

1. use a CLI wrapper, not a button in static HTML. the existing board remains
   script-free and read-only. alternative: a local authenticated HTTP service;
   defer until there is a concrete need for a browser mutation surface.
2. preserve the exhausted first queue. a new session may be created only after
   explicit owner authorization naming its scope and bounds. alternative: reset
   counters or edit the old database; rejected because that destroys accounting.
3. propose a second session of at most four requests and one reserved-credit
   ceiling, retaining 0.1 credits reserved per claim, one worker and no automatic
   retries. this matches the existing runner. accepting this spec approves
   implementation only; the owner separately authorizes that named paid session.
4. require the reviewed packet fingerprint for every explicit live submission.
   this is a content-integrity check, not an authentication system or a demand for
   another owner confirmation when the task already falls within approved scope.

## workflow and invariants

### prepare without executing

proposed command: `python3 -m control_plane.submit prepare` with explicit repository,
full commit SHA, repository-relative source path, optional inclusive line range,
task/attempt ids, objective, expected deliverable and a new private output directory.

resolve content from the named git object, never from the working file or `.env`.
initial supported source is tracked regular Python files under `runtime/` or
`control_plane/`. reject symlinks, submodules, traversal, absolute paths, denied
secret names and other file types. git arguments are fixed argv, never shell text.
check blob size before reading and retain existing packet-size limits. malformed
or oversized inputs refuse before any queue creation or provider access.

an excerpt's label records the source path and exact inclusive line range;
`source.revision` records the commit and `source.sha256` hashes the supplied text.
a packet hash covers the complete existing v1 envelope using the agreed canonical
encoding. ids and emitted time are stable after preparation; no regeneration at
submission. task text supplied by the operator remains distinct from untrusted
source text. reject empty or out-of-range excerpts rather than silently clipping.

write only a new owner-private directory containing packet JSON and a readable
review file: exact objective, deliverable, source/excerpt, hashes, worker, fixed
bounds and advisory-output caveat. these artifacts contain source and are private;
never put them in the public board or commit them as real fixtures. terminal output
contains metadata and paths only, never source or credentials. preparation makes
zero provider calls and creates no worker claim.

### identify an authorized session

a session manifest records a bounded session id, schema version, explicit owner-
authorization reference, allowed task purpose, worker/model, fixed limits and the
selected runner source fingerprint. the manifest contains no key. its purpose is
a durable record of already-supplied authority, not proof that an arbitrary JSON
file grants authority. the coding agent must check the owner's actual instruction.

an explicit session initialization command creates a new private session directory
with an immutable manifest and its one queue. missing authorization, conflicting
identity or existing destination is a refusal. partial initialization is reported
and retained for operator inspection; do not retry by inventing another directory.
never reset, copy or migrate the original trial queue. all tasks in the session
share this one database and the existing transactionally enforced counters.

place the manifest beside a `queue/` subdirectory, not in the SQLite schema, so
the strict spec009 reader remains compatible. each new capture is labeled with
the validated session id and manifest hash. session limits are local and are not
an account balance. a second session is not silently created when limits are hit.

### submit one exact packet

proposed command: `python3 -m control_plane.submit run` with explicit session,
packet and expected packet SHA-256. offline execution is the default; `--live`
is required for provider access. read and hash the bounded packet once, validate
it, then pass that same in-memory object to the runner: do not hash one version
and reread another. reject fingerprint/mode/worker/configuration mismatch before
claim or provider call. offline proof uses distinct task ids from a live task.

live credentials continue to come only from the existing launcher-injected
`ADAPTION_API_KEY`. no key picker, credential copy, `.env` read or secret-bearing
command argument is introduced. there is no provider fallback or retry. reuse
`delegation.execute`; do not create a second scheduler or SDK integration.

persist the receipt through the existing queue first. identical repeated packets
return the same terminal receipt without execution; conflicting ids or active
claims refuse. incomplete provider output is failed evidence, not successful task
completion. no model text becomes code, a command, a gate verdict or a new task.

### capture after execution

after a terminal outcome or cached replay, attempt one new private board capture
using that session's queue and the existing observer. capture includes sanitized
metadata only. session identity must be visible so two different trial budgets
cannot be confused. the previous session's capture remains available separately;
no cumulative/account-wide cost total is claimed.

receipt persistence and capture success are separate outcomes. if git/gh, rendering
or output-directory creation fails, print a categorical capture warning and the
receipt status. do not rerun the task or discard its receipt. the operator may
repeat capture independently. CLI exit codes: 0 for completed worker plus successful capture; 1 for a failed
worker, regardless of capture outcome; 2 for refused/blocked submission or invalid
input; 3 for completed worker with unavailable capture. categorical capture
status is always reported separately. cover this precedence with tests.

## implementation order

1. source extraction and packet preparation, with hostile path/range/size fixtures.
2. session manifest validation and one-directory initialization; preserve existing
   state and prove interruption/refusal behavior without calling providers.
3. hash-bound submission through the existing runner; trap SDK access on every
   invalid/preparation path and prove replay does not double-execute.
4. post-run capture and session labels; inject capture failures and show the
   terminal receipt and budget remain unchanged.
5. update operations, exercise the CLI end to end with fictional offline tasks,
   and obtain independent review. paid proof requires a separately authorized
   named session and concrete task within its approved scope.

## acceptance and proof

- preparation from a pinned commit ignores dirty working-tree edits, rejects
  disallowed paths and preserves exact excerpt bytes and revision provenance.
- tampering with any reviewed field refuses submission before claim; ids, limits,
  worker and model cannot be switched through untrusted source/model output.
- existing session or queue files are never overwritten; simulated interruptions
  cannot silently create a second budget or erase history.
- offline happy path produces one claim, one receipt and one labeled capture;
  repeat submission produces the same receipt and no extra execution/reservation.
- exhausted sessions refuse even if a board capture fails. capture-only replay
  has no SDK invocation. unavailable sources never become invented zero totals.
- no key/raw source/model answer leaks into terminal diagnostics or board output;
  private review files are explicit and mode 0600 inside a mode-0700 directory.
- all existing observer, projection, delegation and browser checks remain green.

planned checks: `python3 -m unittest control_plane.test_submission control_plane.test_delegation control_plane.test_observer control_plane.test_worker_projection -v`, scoped ruff, CLI subprocess checks with fake SDK/network traps, and the existing board browser harness. new submission module/tests are proposed, not implemented.

## change shape

| dimension | changed? | source of truth | proof |
|---|---|---|---|
| user-visible behavior | yes | explicit prepare/run CLI and session label | offline CLI and browser checks |
| persisted state or schema | yes | private manifest/review files; unchanged queue schema | interruption/no-overwrite tests |
| external or provider-visible behavior | yes | explicit live wrapper around existing worker | invocation traps; separately authorized paid proof |
| identifiers, secrets or privacy | yes | hash-bound packet and private source extraction | tampering/path/canary tests |
| lifecycle or terminal states | no | existing queue states | replay/conflict/capture-failure tests |
| setup, operation or recovery | yes | session initialization and separate recapture | error-path CLI checks |
| normative contract or decision | yes | draft submission and authorization boundary | owner acceptance before implementation |
| cross-repository dependency | no | local repo and existing git/gh observer | no teammate transport changes |

## risks and review

review private-source handling, packet read/hash/use consistency, manifest spoofing
assumptions, duplicate initialization and partial-failure reporting. the local owner
can deliberately bypass this wrapper; it is not a security boundary against that
owner. neither a manifest nor a remaining counter establishes spending authority.

provider-response sanitization remains a separate follow-up. pin the actual runner
revision selected for implementation, retain its diagnostics, and account for any
new source fingerprint in the board's configuration registry only after inspection.

[change atlas](task-submission-review/index.html) is the full owner review surface.
no separate companion is needed for this short explicit sequence; the static atlas
keeps its gates visible without inventing an append-record demonstration.
