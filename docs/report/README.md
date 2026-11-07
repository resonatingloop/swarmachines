# docs/report — submission scaffold (Apart Sprint · Swarm Alignment 2026)

This directory scaffolds the hackathon report. It is **structure only**:
section headers, word-count targets, and required-appendix stubs. All
content prose belongs to **colette** (bd: swarmachines-m9p). Nobody else
writes content here without her say-so.

## Official template

The submission must be a PDF made from the official template (Google Doc,
make-your-own-copy link from the brief):
https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/copy

`report-skeleton.md` mirrors that template's required structure so the
outline, targets, and review happen in-repo. When the GDoc copy is open,
conform section names to it and treat this file as the working mirror.

## Hard submission constraints (checklist)

- [ ] PDF exported from the official template
- [ ] Max 8 pages, excluding references and appendices
- [ ] Abstract 150-250 words
- [ ] Title; author names and affiliations
- [ ] REQUIRED appendix present: "Limitations and Dual-Use / Ethical
      Considerations" — a submission without it fails the checklist
- [ ] Links included: project code (GitHub), presentation recording,
      slides, project image
- [ ] Report reads as a mini research paper (problem, approach, results,
      implications) — not a product demo
- [ ] At least one boring/inconclusive result reported honestly, where it
      happened
- [ ] Judging dimensions addressed: impact potential & innovation,
      technical execution (rigor, reproducibility), presentation & clarity

## How to use

1. Write content in the official GDoc copy (it is the submission format).
2. Keep `report-skeleton.md` in sync: it carries the section order, the
   per-section word targets, and the placeholder markers.
3. Bracketed numbers like `[600-800 words]` are targets, not limits — the
   hard budget is the 8-page cap (references and appendices excluded).
   Each figure or table consumes roughly a third of a page; budget for
   2-4 exhibits in the body.
4. Fill `[PLACEHOLDER: ...]` markers; delete the guidance bullets as
   sections solidify.

## Draft-time verified state (pointers for drafting — re-verify before submit)

As of 2026-11-07 ~18:30 UTC, on master (PR #1 merged):

- Scripted turn-cycle runner is on master; zero model calls by design.
- `runtime/test_runner.py`: 12/12 tests passing (includes determinism,
  schema-validity, zero-model-calls checks).
- `runtime/sample-run.jsonl`: 67 events; passes `verify_events.py` with
  all required event types present.
- Topology comparison (fully-connected vs bidirectional ring) and the
  peer-mute disturbance are NOT yet implemented — tracked as
  bd-swarmachines-9e5; the Results section must only claim what exists at
  submission time.

## Deadline

Submissions close Sunday, November 8, 2026, 11:59 PM AoE
(= Monday 11:59 UTC). Plan: skeleton tonight, drafting Sunday morning,
final integration Sunday afternoon with buffer for the required appendix.
