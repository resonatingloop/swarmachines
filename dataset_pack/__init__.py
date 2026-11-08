"""
dataset_pack — HF dataset packager for swarmachines freight-in-the-fog swarm runs

Modules:
- configs: 15 versioned task-instance configs with deterministic replay
- run: governed run glue (prepare → submit → capture)
- extract: post-run artifact extraction from persisted logs
- package: MANIFEST reconciliation, HF dataset card, records/runs tables
- upload: HF upload script (env-only credentials)
- tests: provenance and packaging tests
"""

__version__ = "0.1.0"
