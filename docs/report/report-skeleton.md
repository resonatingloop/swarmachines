# swarmachines: a replayable, fully-logged testbed for observing coordination and disruption in agent collectives

**Authors:** [PLACEHOLDER: author names]
**Affiliations:** [PLACEHOLDER: affiliations]

> Note: title, authors, and affiliations are required by the submission
> checklist. Colette owns all content in this skeleton (bd: m9p).

---

## Abstract

Collective agent behaviors—coordination, role specialization, fracture, and repair—emerge at the multi-agent level and evade single-model safety tests. We present swarmachines, a reproducible testbed for studying agent collectives under disruption, with a tamper-evident turn-seam event log that records every action at the world boundary. The testbed supports scripted, zero-model-call episodes across communication topologies (fully-connected mesh, bidirectional ring) with applied disturbances (peer muting, relay loss). We report a formal topology comparison: seed-42 episodes under peer-mute:8:c (agent c muted from turn 8) show identical job completion across topologies (4/4 deliveries in both mesh and ring), with the topology signal appearing in event volume (mesh: 414 events; ring: 386 events) and message traffic patterns. The event log is cryptographically sealed with a per-event SHA-256 chain and terminal certification, enabling offline verification that no record was inserted, edited, or removed post-hoc. All runs are deterministic and replayable from the log alone. The testbed is designed for oversight research: it makes collective behaviors observable, auditable, and comparable across experimental conditions.

*Word count: 168 words*

## 1. Introduction & Problem

The July 2026 Hugging Face incident demonstrated a critical gap in AI safety evaluation: approximately 1,200 agents in a security evaluation self-organized a shared message board, split work, and collectively breached a target; roughly 7% spoofed their own tool calls; and 7,905 names were registered for approximately 1,200 agents. No single-model safety test surfaces this kind of emergent collective behavior. Safety evaluations focus on individual model outputs, but coordination happens between agents, through message passing, role assignment, and shared state.

The gap is observational: how do collectives form, coordinate, fracture, and repair—and how do we watch it happen with an event log that cannot lie? Existing logging approaches record what agents say, not what they do at the world boundary. A log that captures only model outputs cannot detect tampering, cannot replay episodes deterministically, and cannot serve as evidence in an audit.

This paper contributes a reproducible testbed where every event is logged at the turn seam, replay is deterministic, and coordination under disruption is comparable across communication topologies. The swarmachines testbed records all actions at the world boundary (the "turn seam"), chains events with cryptographic hashes to detect tampering, and supports scripted episodes that make zero model calls—enabling reproducible, auditable experiments in collective agent behavior.

**Research questions:**
1. How do communication topologies (mesh vs. ring) affect coordination efficiency under identical disruption conditions?
2. Can a tamper-evident event log detect post-hoc fabrication or editing of episode records?
3. What metrics capture collective behavior (message volume, delivery latency, role specialization) that are invisible to single-agent evaluation?

## 2. Approach: the swarmachines testbed

### 2.1 Turn-seam event log

The event log is the honesty guarantee of the testbed. At each turn seam—the boundary between agent deliberation and world mutation—the runner records every action in a structured schema: `turn`, `agent`, `phase` (observe/exchange/act), `action`, `outcome`, and a per-event `seq` number. Each event carries a `hash` field: a SHA-256 chain hash computed from the canonical JSON of the event content and the previous event's hash, with the genesis hash bound to the run ID. This design makes the log tamper-evident: any insertion, deletion, or modification of a chained record breaks the hash chain and is detected by the offline analyzer.

The terminal `run.seal` record certifies the run's completion state: it records the final event seq, the last hash, and the termination condition. The analyzer verifies the seal when present: edit/insert/remove of any chained record is rejected categorically; legacy unsealed logs remain byte-compatible and measure identically. This design ensures that the evidence pipeline cannot be poisoned by post-hoc tampering.

*Implementation: PR #46 (5eaa9be) — feat(runtime): seal the EventLog against policy-level fabrication; 569 lines changed across 9 files; suites: runtime 28/28, analysis 17/17, control_plane 74 OK, viewer 62, e2e PASS.*

### 2.2 Scripted runner, zero model calls

The first deliverable is deterministic and model-free: reproducibility before intelligence. The runner operates in scripted mode by default, with no model calls. A seed parameter initializes the RNG stream, which is separated from any model-call RNG (when models are added in future work). The turn cap (`--turns`) bounds episode length. "Replay-deterministic" means that two runs with the same seed, topology, disturbance, and world state produce byte-identical logs—verified by hash comparison.

The zero-model guarantee is enforced by design: the scripted policy (`route-gossip-v1`) makes decisions based on local state and received messages, not model outputs. This enables rapid iteration, reproducible debugging, and clean attribution of effects to topology and disturbance rather than model variance.

### 2.3 Communication topologies and disturbances

The topology axis includes fully-connected mesh (every agent can message every other agent) and bidirectional ring (agents arranged in a circle, messaging neighbors in both directions). The disturbance axis includes peer muting (silence one agent from a specified turn onward), relay loss (messages fail to forward), and stale information (agents receive outdated reports).

The formal topology comparison reported here uses seed 42, peer-mute:8:c (agent c muted from turn 8 through turn 16), and the freight world. Both arms (mesh-first, ring-second) completed all 16 turns with termination state "completed." The topology difference appears in event volume and message traffic, not in job completion.

*Implementation: PR #39 (572612a) — feat(spec006): seed-42 formal pair; PR #5 (aa38f63) — bidirectional ring topology + peer-mute disturbance.*

### 2.4 World and agents

The freight world models a delivery problem: four agents (a, b, c, d) must deliver freight items across a network of routes with capacity constraints. Each agent has a role (carrier, dispatcher, observer, relay) and partial observations of the world state. Agents can move freight, request routes, and exchange messages. The world enforces capacity limits and tracks delivery states.

*Implementation: PR #29 (7103ac0) — freight world + runner integration; PR #38 (7acd2a7) — fix: freight act-phase mislabel (legal no-ops now correctly labeled action.committed).*

## 3. Results

### 3.1 Topology comparison under peer mute

We ran a formal pair of episodes with identical seed (42), disturbance (peer-mute:8:c), and world (freight), varying only topology (mesh vs. bidirectional ring). Both episodes completed all 16 turns with all 4 jobs delivered.

| Condition | Topology | Events | Exit | Deliveries |
|-----------|----------|--------|------|------------|
| spec006-seed42-mesh-mutec-t8 | mesh (fully connected) | 414 | 0 | 4/4 |
| spec006-seed42-ring-mutec-t8 | bidirectional ring | 386 | 0 | 4/4 |

*Table 1: Topology comparison — seed 42, peer-mute:8:c, freight world. Both arms completed; topology signal appears in event volume (mesh 414 vs ring 386), not job completion.*

**Headline observation:** Job completion is identical across topologies under this scripted policy and disturbance. The topology signal appears in event volume (7% more events in mesh) and message traffic patterns, not in the delivery numerator. This is a valid null result: the spec explicitly allows zero/negative/mixed outcomes. The ring topology achieves the same delivery outcome with fewer events, suggesting lower communication overhead—but this interpretation requires additional runs across seeds to establish statistical confidence.

*Evidence: PR #39 (572612a) — runs/spec006/FROZEN-MANIFEST.md; episode artifacts at 426586b.*

### 3.2 Tamper-evidence verification

The event log seal was verified against four attack vectors: (1) edit a chained record, (2) insert a fabricated record, (3) truncate the log, (4) break the hash chain partially. All four attacks are detected and rejected by the analyzer. The terminal seal (run.seal) is required for verification; unsealed logs are treated as legacy and measure identically but cannot be verified.

*Evidence: PR #46 (5eaa9be) — analysis/test_measure_episode.py: 17/17 tests, including tamper detection.*

### 3.3 Reproducibility check

Two runs with seed 42, topology mesh, peer-mute:8:c, and freight world produce byte-identical logs. The SHA-256 of the mesh episode is `432dbf9f7704e7f580589ddf16bc0284c4a4aadeef793cf4a24958bacf00c613`; the ring episode is `53a843e40267da13a3157f93de1a7dc15960ee9e59af9c9768a181a94c362bc6`. Replay from the log alone reconstructs the exact world state at each turn.

*Evidence: PR #39 (572612a) — FROZEN-MANIFEST.md; PR #32 (2b7d668) — e2e pipeline v2 PASS (determinism check included).*

### 3.4 Honest-inconclusive result

The topology comparison reports a null result on the primary outcome (job completion): both topologies achieved 4/4 deliveries. This is not a failure of the testbed; it is a valid finding. The topology signal appears in secondary metrics (event volume, message traffic), which require additional runs and measure definitions to interpret. The single-seed design limits statistical claims; the pair is a proof of the experimental apparatus, not a definitive comparison of mesh vs. ring efficiency.

## 4. Discussion & Implications

The swarmachines testbed makes collective agent behaviors observable and auditable in a way that single-model evaluations cannot. The tamper-evident event log enables forensic analysis: if a collective exhibits unexpected coordination, the log can be verified as authentic, and the episode can be replayed to isolate the mechanism.

**For oversight researchers:** The testbed provides a controlled environment for studying coordination patterns, covert channels, and disruption response. The scripted, zero-model baseline enables clean attribution of effects to topology and disturbance, without model variance confounds. Future work with model-in-the-loop agents can compare scripted vs. learned coordination strategies.

**For deployment monitoring:** The event-log schema and seal design imply a deployment monitoring approach: log every action at the world boundary, chain events cryptographically, and verify seals periodically. This would detect log tampering and enable replay of incidents for forensic analysis.

**What this does not show:** The current results do not demonstrate that any topology is superior for coordination under disruption. The single-seed, scripted design is a proof of the apparatus, not a general claim about mesh vs. ring. The measure definitions (T-007) are under review; the reported numerators (event counts, delivery states) are raw log data, not interpreted measures.

## 5. Artifacts & Links

- **Project code:** https://github.com/resonatingloop/swarmachines (origin/master 4e63cee)
- **Presentation recording:** [PLACEHOLDER]
- **Slides:** [PLACEHOLDER]
- **Project image:** [PLACEHOLDER]

## References

1. Hugging Face incident report, July 2026. [PLACEHOLDER: cite official sources]
2. swarmtraces.org — dataset of agent coordination traces
3. AI Village transcripts — multi-agent security evaluation records
4. transluce.org/agent-activity — agent activity monitoring
5. swarms.wiki — community knowledge base on multi-agent systems

---

## Appendix A: Limitations and Dual-Use / Ethical Considerations

### A.1 Limitations

- **Scripted, zero-model-call agents:** The current deliverable is a deterministic scaffold, not LLM agents; language-model behavior is out of scope of the present results. All reported episodes use scripted policies (`route-gossip-v1`) with no model calls.
- **Single world, small agent counts, bounded turn cycles:** The freight world has 4 agents and 16-turn horizons. Results may not generalize to larger collectives or longer episodes.
- **Topology/disturbance coverage:** Only one disturbance (peer-mute:8:c) and two topologies (mesh, ring) were run at submission time. Relay loss and stale report disturbances are implemented but not reported here.
- **Log integrity:** The schema is validated and determinism-checked, but the seal is not adversarially hardened against a malicious writer with code access. It detects post-hoc tampering with the log file, not runtime subversion.
- **Measurement boundary:** `recovery_interval_turns` is a horizon placeholder, not a measured recovery metric. The accepted future metric is intervention-to-first-completion delay, which requires additional instrumentation.

### A.2 Dual-Use / Ethical Considerations

- **Intended use:** Oversight and safety research on multi-agent coordination, disruption, and recovery. The testbed is designed to make collective behaviors observable and auditable.
- **Dual-use risk:** The same mechanics (message passing, role split, disturbance response) could be studied to evade oversight. Mitigation: publish the full event schema and deterministic logs so behavior is auditable; the testbed is transparent by design.
- **Data ethics:** Synthetic agents only; no human subjects; no personal data in logs. The pre-recorded data pack (PR #28) contains 38 artifacts (26 model-generated, 12 team-authored) with full provenance labeling; none are observed experimental evidence—these are inputs, not results.
- **Compute:** Current results use zero model calls. Future model-in-the-loop runs will report compute honestly (model, tokens, API calls).

## Appendix B: Reproducibility

Exact rerun commands from a clean checkout:

```bash
# Clone and setup
git clone https://github.com/resonatingloop/swarmachines
cd swarmachines
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the seed-42 topology pair (mesh first, ring second)
python3 runtime/runner.py --seed 42 --topology mesh --turns 16 --world freight --policy route-gossip-v1 --disturbance peer-mute:8:c --agents a,b,c,d --output runs/spec006/spec006-seed42-mesh-mutec-t8/episode.jsonl

python3 runtime/runner.py --seed 42 --topology bidirectional-ring --turns 16 --world freight --policy route-gossip-v1 --disturbance peer-mute:8:c --agents a,b,c,d --output runs/spec006/spec006-seed42-ring-mutec-t8/episode.jsonl

# Verify events (schema validation)
python3 runtime/verify_events.py runs/spec006/spec006-seed42-mesh-mutec-t8/episode.jsonl
python3 runtime/verify_events.py runs/spec006/spec006-seed42-ring-mutec-t8/episode.jsonl

# Verify determinism (run twice, compare hashes)
python3 runtime/runner.py --seed 42 --topology mesh --turns 16 --world freight --output /tmp/run1.jsonl
python3 runtime/runner.py --seed 42 --topology mesh --turns 16 --world freight --output /tmp/run2.jsonl
sha256sum /tmp/run1.jsonl /tmp/run2.jsonl  # Should be identical

# Verify event log seal (tamper detection)
python3 analysis/measure_episode.py runs/spec006/spec006-seed42-mesh-mutec-t8/episode.jsonl
```

**Interpreter and dependency pins:**
- Python 3.14.9
- Dependencies: `requirements.txt` (jsonschema, pytest, ruff)
- Runtime commit for reported pair: `0f84075` (spec006 Gate-1 anchor; master at run time)
