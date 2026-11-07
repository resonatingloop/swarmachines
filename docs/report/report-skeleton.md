# [TITLE — PLACEHOLDER: name the testbed and the study, e.g. "swarmachines:
# a replayable, fully-logged testbed for observing coordination and
# disruption in agent collectives"]

**Authors:** [PLACEHOLDER: author names]
**Affiliations:** [PLACEHOLDER: affiliations]

> Note: title, authors, and affiliations are required by the submission
> checklist. Colette owns all content in this skeleton (bd: m9p).

---

## Abstract [150-250 words — hard constraint]

[PLACEHOLDER: one paragraph. Cover: the problem (collectives form,
coordinate, fracture, and repair, and single-model safety tests do not
catch this), the artifact (a reproducible, fully-logged, replayable
agent-collective testbed with a tamper-evident turn-seam event log),
what was run (scripted, zero-model-call episodes across communication
topologies with applied disruptions), and what a reader takes away.]

*Target the full 150-250 range; under 150 fails the template check.*

## 1. Introduction & Problem [600-800 words]

[PLACEHOLDER: the problem statement.]

- Frame from the July 2026 Hugging Face incident (per the brief): ~1,200
  agents in a security evaluation self-organized a shared message board,
  split work, and collectively breached a target; ~7% spoofed their own
  tool calls; 7,905 names for ~1,200 agents. No single-model safety test
  surfaces this behavior.
- State the gap: how do collectives form, coordinate, fracture, and
  repair — and how do we watch it happen with an event log that cannot
  lie?
- State the contribution in one sentence: a reproducible testbed where
  every event is logged at the turn seam, replay is deterministic, and
  coordination under disruption is comparable across communication
  topologies.
- [PLACEHOLDER: list the concrete research questions the runs answer.]

## 2. Approach: the swarmachines testbed [900-1200 words]

[PLACEHOLDER: design section — what the testbed is and why it is built
this way.]

### 2.1 Turn-seam event log

[PLACEHOLDER: the event schema, what is recorded at each seam, message
lifecycle (sent / delivered / seen), provenance, and why the log is the
honesty guarantee. Reference the openspec change.]

### 2.2 Scripted runner, zero model calls

[PLACEHOLDER: why the first deliverable is deterministic and
model-free: reproducibility before intelligence. Seeds, RNG stream
separation, turn cap, and what "replay-deterministic" is verified to
mean.]

### 2.3 Communication topologies and disturbances

[PLACEHOLDER: the topology axis (e.g. fully-connected mesh,
hub-and-spoke, bidirectional ring as implemented at submission time) and
the disturbance axis (relay loss, stale information, muting one agent).
State exactly which combinations were run.]

### 2.4 World and agents

[PLACEHOLDER: the freight world (agents, delivery graph, capacity,
partial observations) — describe what is implemented, not what is
planned.]

## 3. Results [900-1200 words]

[PLACEHOLDER: findings, ordered so each claim maps to a logged episode
or a check that another team can rerun.]

- [PLACEHOLDER: episode-level results — what a recorded episode shows.]
- [PLACEHOLDER: topology comparison — only if implemented at submission;
  otherwise report the single-topology baseline and say the comparison
  is future work.]
- [PLACEHOLDER: disruption effects — relay loss / stale report / mute,
  as implemented.]
- **Honest-inconclusive slot (required by the brief):** [PLACEHOLDER:
  report at least one boring, null, or inconclusive result exactly as it
  happened.]

*Figure/table slots (each ≈ 1/3 page, budget within the 8-page cap):*

- Figure 1 [PLACEHOLDER: episode timeline or world view]
- Figure 2 [PLACEHOLDER: topology comparison table — counts of
  message/delivery events per topology, from the logs]
- Table 1 [PLACEHOLDER: reproducibility checks — seed, event counts,
  determinism verification]

## 4. Discussion & Implications [500-700 words]

[PLACEHOLDER: what this testbed makes possible that was not possible
before.]

- What Track 1 teams and oversight researchers can build on it.
- What the event-log view implies for detecting coordination, covert
  channels, and log tampering in real deployments (connect to Track 2/4
  framing from the brief).
- [PLACEHOLDER: honest statement of what the current results do NOT yet
  show.]

## 5. Artifacts & Links [~100 words]

[PLACEHOLDER: required links — project code (GitHub), presentation
recording, slides, project image. One line each.]

## References

[Excluded from the 8-page budget. Placeholder: cite the HF incident
sources, the brief's referenced datasets if used (swarmtraces.org, AI
Village transcripts, transluce.org/agent-activity, swarms.wiki), and any
methods citations.]

---

## Appendix A: Limitations and Dual-Use / Ethical Considerations
[REQUIRED APPENDIX — a submission without it fails the checklist.
Excluded from the 8-page budget.]

### A.1 Limitations

[PLACEHOLDER: state plainly —]

- Scripted, zero-model-call agents: the current deliverable is a
  deterministic scaffold, not LLM agents; language-model behavior is
  out of scope of the present results.
- Single world, small agent counts, bounded turn cycles.
- [PLACEHOLDER: topology/disturbance coverage as actually implemented.]
- Log integrity: schema-validated and determinism-checked, but not
  adversarially hardened against a malicious writer.

### A.2 Dual-Use / Ethical Considerations

[PLACEHOLDER: state plainly —]

- Intended use: oversight and safety research on multi-agent
  coordination, disruption, and recovery.
- Dual-use risk: the same mechanics (message passing, role split,
  disturbance response) could be studied to evade oversight; mitigate by
  publishing the full event schema and deterministic logs so behavior is
  auditable.
- Data ethics: synthetic agents only; no human subjects; no personal
  data in logs.
- Compute: current results use zero model calls; [PLACEHOLDER: state
  compute honestly if model-in-the-loop runs are added].

## Appendix B: Reproducibility [optional, excluded from page budget]

[PLACEHOLDER: exact rerun commands from a clean checkout — verifier,
test suite, and runner invocation with seed/topology/disturbance flags;
state the interpreter and dependency pins.]
