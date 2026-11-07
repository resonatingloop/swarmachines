# swarmachines / status

> continuity role: operational checkpoint
> status: PR #5 (bd-swarmachines-9e5-ring-topology) — ring topology + peer-mute + freight decoupling
> last verified: 2026-11-07 (17/17 tests pass, ruff clean)
> owns: exercised state, active work, gaps, and the next useful action
> update when: a meaningful stopping point changes these facts; replace this checkpoint in place

## verified checkpoint

PR #5 (branch `bd-swarmachines-9e5-ring-topology`) implements the freight-in-the-fog world
from `specs/001-hackathon-plan.md`: 4 agents, 16 turns, topology comparison under mute-one-agent
disruption, python runtime + browser JS replay.

### Features implemented

1. **Bidirectional ring topology**: ring_neighbors two-neighbor map, can_communicate ring branch,
   CLI --topology bidirectional-ring choice, topology-independence test extended to ring.
2. **Send-layer enforcement**: can_communicate checked BEFORE logging message.sent; blocked
   sends do NOT log message.sent — only undelivered-with-reason records.
3. **Turn-gated peer-mute disturbance**: scheduler.active gating, mutes communication but local
   actions continue, disturbance.applied event with peer-mute kind.
4. **Freight decoupling**: delivery_config_sha computed from hub/topology config, not delivery graph.
5. **Undelivered-with-reason records**: relay-loss and peer-mute produce message.delivered with
   status='undelivered' and reason field.
6. **Stale-report message_id validation**: stale-report disturbance validates message_id was in
   circulation (sent, delivered, seen lifecycle entries).
7. **load_events hardening**: per-line char_limit=10000 (10k) + cumulative total_limit=10000000
   (10MB), non-echoing error messages (categorical types only, no raw hostile input).

### Test suite (runtime/test_runner.py): 17/17 pass

- basic run produces valid event log with all required types
- determinism: same seed produces byte-identical output
- relay-loss disturbance applied and logged correctly with undelivered messages
- stale-report disturbance applied and logged correctly with before/after detail
- hub-spoke topology configuration works and delivers messages through hub
- message lifecycle tracking (sent→delivered→seen→acted_on) complete
- topology-independence: non-comm events identical across mesh/hub-spoke
- zero model/network calls in runner
- RNG stream independence: send decisions don't affect acted_on decisions
- delivery_config_sha correctly named and validated
- agent id charset validation
- --turns cap at 100
- stale-report validates message_id exists in circulation
- bidirectional-ring topology restricts communication to neighbors
- peer-mute disturbance mutes communication but local actions continue
- topology-independence with ring: non-comm events identical across mesh/ring
- load_events hardening (10MB cap, non-echoing errors)

### Verification commands

```sh
python3 runtime/test_runner.py
ruff check runtime/runner.py runtime/test_runner.py
ruff format --check runtime/runner.py runtime/test_runner.py
python3 runtime/runner.py --topology bidirectional-ring --turns 2 --agents a,b,c,d --seed 42 --output /tmp/ring-test.jsonl
```

All checks pass. Ring topology reachable via CLI --topology bidirectional-ring.

## working now

- PR #5 ready for gate (sast + verifier review)
- Hackathon research report PDF due Sunday Nov 8, 11:59 PM AoE
- Integration day Sunday — report skeleton starts Saturday

## incomplete or broken

- Adaption access, credit coverage, rates, spend allocation, and model serving
  have not been verified. Langfuse tracing has not been connected or exercised.
- The distributed discord guides do not establish a live connection. No
  project room card, installed adapter, or peer round trip has been verified
  in this work.

## active work

- PR #5 (bd-swarmachines-9e5-ring-topology): ring topology + peer-mute + freight decoupling
  implemented, 17/17 tests pass, ruff clean. Ready for push and gate.
- Hackathon Track 1 (Sandboxes and Testbeds) primary + Track 2 cross-track.
- Deadline: research report PDF (official template, 8 pages max, abstract 150-250 words,
  required Limitations/Dual-Use appendix) by Sunday Nov 8, 11:59 PM AoE.

## next useful action

Push PR #5 to origin/bd-swarmachines-9e5-ring-topology for sast + verifier gate.
Begin report skeleton Saturday for Sunday integration day.

## re-entry notes

- Checkout: `/workspace/swarmachines`.
- Branch: `bd-swarmachines-9e5-ring-topology`.
- Run tests: `python3 runtime/test_runner.py`.
- Ring topology CLI: `python3 runtime/runner.py --topology bidirectional-ring --turns 2 --agents a,b,c,d --seed 42 --output /tmp/ring.jsonl`.
