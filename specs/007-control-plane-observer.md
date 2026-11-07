# control plane / observation before dispatch

status: accepted

owner: colette · implementation: asterion · dispatcher integration: pug

## owner view

- change: expose existing task claims and github artifact facts in one offline view.
- before: room reports and branch-local ledgers require manual reconciliation.
- after: a pinned ledger capture sits beside timestamped github metadata, with missing evidence and possible disagreements visible.
- authority: colette approved the orchestration/control-plane proposal and explicitly cleared its first observation-only implementation on 2026-11-07. this records that bounded slice, not acceptance of a future dispatch schema.

## scope

in: read-only git/gh collector, snapshot v1, static local task board, source receipts, diagnostic coverage, repeatable offline and browser checks.

out: scheduling, leases, heartbeat collection, task mutation, provider calls, secret provisioning, merge execution, automated retries, experimental swarm changes. adaption-backed builders/verifiers remain in the approved rollout, with their executable interface and spend allocation still to be pinned before dispatch.

## invariants

1. resolve the ledger ref once; read TASKS.md from that exact commit, never the mutable working tree.
2. preserve reported states and owners as claims. github's merged state is an artifact fact, not task completion or successful review.
3. unsupported rows, duplicate ids, missing timestamps, source failures and potentially truncated PR lists remain visible.
4. collection timestamps and source update timestamps are distinct; no atomic distributed snapshot or remote-ref freshness claim.
5. output is a new private directory with escaped script-free HTML and JSON. no source writes, credential reads, background loops or automatic authority transitions.
6. a PR number extracted from prose is only a mention. reconciliation hints do not establish dependency, assignment or review correctness.

## change shape

| dimension | changed? | source of truth | proof |
|---|---|---|---|
| user-visible behavior | yes | control_plane/board.html | rendered reflow and keyboard checks |
| persisted state or schema | yes | snapshot v1 from observer.py | private output/no-overwrite tests |
| external or provider-visible behavior | yes | read-only gh query | command-boundary tests; zero provider invocation |
| identifiers, secrets or privacy | yes | existing task ids; private captures | duplicate handling, escaping, mode tests |
| lifecycle or terminal states | no | source ledger | no automatic transition test |
| setup, operation or recovery | yes | control_plane/README.md | live capture and clean source status |
| normative contract or decision | yes | this bounded observer slice | owner acceptance; claims/facts separation tests |
| cross-repository dependency | no | same repo and existing gh access | no alternate dispatcher installed |

## validation and acceptance

run `python3 -m unittest control_plane.test_observer -v`, `ruff check control_plane`,
and the browser command in [observer operations](../control_plane/README.md).
verify a real pinned ledger and github capture, then unavailable/hostile fixtures
without contacting providers. acceptance does not mean dispatch is ready.

## next boundary

pug supplies the dispatcher task/receipt interface and confirms ledger ownership.
then one accepted task can exercise assignment → acknowledgment → artifact
receipt → independent review. no new workers start from this observer.

## review surface

[change atlas](control-plane-review/index.html) is a complete static projection.
no additional anatomy companion is needed: the implemented board itself exposes
the bounded claims/facts relationship; no dispatch event schema is invented here.
