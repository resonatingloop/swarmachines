# swarmachines

> continuity role: operational front door
> status: proposal phase
> last verified: 2026-11-07
> owns: the way in, present maturity, and the documentation authority map
> update when: primary use, location, or documentation ownership changes

a hackathon project taking shape around one question: what forms of relation
make an agent collective more capable without flattening distinction,
provenance, dissent, or recoverability?

**task submission:** [prepare, inspect and submit](control_plane/SUBMISSION.md)
wraps the existing worker with exact fingerprints, named session bounds and
a separate receipt-board capture.

**worker receipts:** the [switchboard capture](control_plane/README.md#worker-receipt-capture-snapshot-v2)
can optionally include sanitized local attempts, usage coverage and reservations.
all captures remain frozen and private.

**bounded delegation:** [local investigator protocol](control_plane/DELEGATION.md)
implements private task receipts and duplicate-safe replay. offline and bounded
live transport proofs pass; independent review remains pending.

**paired inspection:** open the [paired viewer](viewer/compare.html) to compare
two local episodes at a shared logical turn; matching logged settings do not
certify an experimental match.

**episode inspection:** open the [local viewer](viewer/index.html); operation and
verification live in [viewer notes](viewer/README.md). the merged scripted runner
now supplies a sample; older proposal-phase statements below predate that merge.

**original proposal:** an interactive, self-contained
[visual team proposal](plans/index.html). it explains the candidate experiment,
four swim lanes, an illustrative network disruption, a workload calculator,
and a two-day rhythm. the swarm runtime is not implemented.

start with [the current checkpoint](STATUS.md) if returning after a break,
or [the project brief](PROJECT_BRIEF.md) for the purpose and open choices.

**message-sensitive scripted policy:** [route-gossip operations](runtime/ROUTE_GOSSIP.md) describe the explicit freight-only mode, decision provenance and capability proof. independent review remains pending; no formal coordination outcome is claimed.

**job evidence:** [offline measurements](analysis/README.md) reconcile versioned roster, completion and terminal records. unsupported measures remain explicit; independent review is pending.

## generate an episode (60 seconds)

episodes are deterministic, self-contained event logs — every message body
is inline, so the log alone is the complete record. python 3.10+ required
(`SyntaxError` during pytest means your `python3` is older — use 3.10+).

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q                 # expect: all passed
.venv/bin/python -m runtime.runner --seed 42 --topology mesh --turns 16 \
    --world freight --policy route-gossip-v1 \
    --disturbance "peer-mute:8:c" --output episode.jsonl
```

expected output:

```
Wrote 415 events to episode.jsonl

=== Episode summary ===
run run-seed0042 | seed 42 | topology mesh | policy route-gossip-v1
turns: 16 | agents: a, b, c, d | events: 415
messages: 71 sent | 51 delivered | 20 undelivered | 51 seen | 0 acted on
actions: 4 committed | 0 rejected
seal: 29f74bdedbed36b7… (run.seal)
output: episode.jsonl
verify: python -m runtime.verify_events episode.jsonl
```

message bodies are inline and observation-derived (route-gossip-v1) or
sender-deterministic status reports (legacy policy):

```json
{"message_id": "m-a001", "from": "a", "to": "d",
 "body": {"type": "route_report", "sender": "a", "turn": 1,
          "location": "west", "routes": {"west->east": "open", "west->south": "open"}}}
```

- same seed + config → byte-identical log (verified by checksum)
- `message.sent` events carry the full `body` inline — no external store
- tamper with any event and `runtime.verify_events` reports `chain_mismatch`
- open `viewer/index.html` to replay the episode turn by turn

note (macOS): the control-plane path checks refuse symlinked journal files,
not symlinked *ancestors* — macOS `/var` -> `/private/var` tempdirs work.

## first successful use

you need a modern browser. for the local http path below, also have python 3
available. no packages, accounts, credentials, or background services need to
be configured.

1. enter this checkout on the owner's machine; in a different checkout, use
   its repository root instead:

   ```sh
   cd /home/resonatingloop/.organocybernetics/swarmachines
   ```

2. confirm python is available. expect a python 3 version; 3.12.3 was used here:

   ```sh
   python3 --version
   ```

3. start a local preview of the presentation directory:

   ```sh
   python3 -m http.server 8765 --bind 127.0.0.1 --directory plans
   ```

4. open [http://127.0.0.1:8765/](http://127.0.0.1:8765/) in your browser. expect
   “what shape does a swarm take under pressure?”. choose a swim lane and see
   its dossier change; the initial workload is 768 planned agent calls.

stop the preview with ctrl+c. alternatively, open `plans/index.html` directly
in a browser: the file includes its styling, illustrations, and behavior.

for the written spec, open the [attention-aperture review](plans/spec-review/index.html)
directly, or visit `/spec-review/` on the same preview server. it preserves all
twelve steps, fifteen working choices, four lanes, and twenty-one source
passages. select a step, follow its supporting wording, or mark choices for
discussion. marks disappear on refresh and accept no decisions. keep the
files in `plans/spec-review/` together.

## where to go next

the [written two-day plan](specs/001-hackathon-plan.md) gives the team a
provisional step-by-step route from setup to a recorded experiment and demo.
review its defaults, choose the world and lane owners, and accept the first
bounded implementation slice. agent context handoffs come after those choices;
nobody is assigned by clicking a lane on the page.

the owner reported a $500 / 1,500-credit adaption grant and wants to use the
platform substantially. a separate coding-agent listener has verified one
hosted model and its published rates; see [discord setup](docs/DISCORD.md).
the grant balance and experimental-run costs remain unverified. the page's
calculator counts calls, not credits or dollars.

## construction control plane

[the switchboard observer](control_plane/README.md) captures reported task state
and github pr facts into a private offline board. it is observation-only; no
workers, dispatch or provider calls are started. see the accepted
[observer slice](specs/007-control-plane-observer.md).

## documentation authority

| document | role | owns |
|---|---|---|
| [README.md](README.md) | operational | entry point, maturity, and this map |
| [STATUS.md](STATUS.md) | operational checkpoint | exercised state, gaps, and the next useful action |
| [AGENTS.md](AGENTS.md) | behavioral | repository working rules and agent continuity |
| [PROJECT_BRIEF.md](PROJECT_BRIEF.md) | durable intent | purpose, audience, constraints, and exploratory direction |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | operational procedure | preview, validation, state, and recovery |
| [docs/DISCORD.md](docs/DISCORD.md) | operational procedure | local agent connection, room identities, and communication proof |
| [plans/index.html](plans/index.html) | planning / discussion draft | the detailed visual proposal for the team |
| [spec review](plans/spec-review/index.html) | generated reference | navigable projection of the written draft; no decision authority |
| [review data](plans/spec-review-data.json) | authored projection input | phase/choice correspondence and exact source excerpts; checked against the draft hash |
| [specs/001-hackathon-plan.md](specs/001-hackathon-plan.md) | planning / draft | proposed sequence, defaults, integration points, and future acceptance evidence |

the html is authored source, not a generated projection of an accepted spec.
there are no runtime contracts, accepted implementation specs, or implemented
architecture documents yet. add them when their facts or proposed transitions
exist. decide disagreements by ownership of the disputed fact, not filename.

## configuration and data

the proposal reads no environment configuration and makes no provider calls.
its controls do not persist state; reload resets them. documentation links
leave the page only when followed. print/save creates a browser-managed export.

an unrelated `.env` exists in the checkout and is outside agent read access.
do not read, source, copy, stage, or serve it. use the `plans` preview directory
above. no deployment or remote publishing workflow is established here.

the [development guide](docs/DEVELOPMENT.md) contains the repeatable browser
checks and documentation-check command, including the checker's known
lowercase-heading warnings.
