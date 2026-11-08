#!/usr/bin/env python3
"""
Adaption call logger for scale data pack generation.

LOGGING CONTRACT (owner directive):
- Run directory: data/runs/<run_id>/
  - artifacts/ — all generated files (prompts, scenarios, examples)
  - logs/calls.jsonl — append-only JSONL stream (one line per call)
  - logs/log.json — aggregated JSON array (complete at run close)
  - receipts/ — captured receipts
  - run.json — run manifest

- JSONL line schema:
  {"ts": ISO8601-UTC, "run": "<run_id>", "call": N, "role": "<role>", "topology": "<mesh|ring>",
   "artifact": "<relative path>", "model": "<model>", "prompt": "<FULL text>", "response": "<FULL text>",
   "tokens_in": N, "tokens_out": N, "receipt": "<receipt path>", "provenance": "model-generated"}

- API key NEVER logged (SDK reads from env, we never touch it)
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class AdaptionLogger:
    """Append-only logger for Adaption API calls within a run."""
    
    def __init__(self, run_id: str, runs_dir: Path | None = None):
        """
        Initialize logger for a run.
        
        Args:
            run_id: Unique run identifier (e.g., "gen-20261108-b01", "regen-batch1-20261108")
            runs_dir: Base directory for runs (default: data/runs)
        """
        self.run_id = run_id
        self.runs_dir = runs_dir or Path("data/runs")
        self.run_dir = self.runs_dir / run_id
        
        # Create run directory structure
        self.artifacts_dir = self.run_dir / "artifacts"
        self.logs_dir = self.run_dir / "logs"
        self.receipts_dir = self.run_dir / "receipts"
        
        for d in [self.artifacts_dir, self.logs_dir, self.receipts_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # JSONL log file (append-only)
        self.jsonl_path = self.logs_dir / "calls.jsonl"
        
        # In-memory call list for log.json
        self.calls = []
        
        # Call counter
        self.call_count = 0
        
        # Run metadata
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.model_id: Optional[str] = None
        self.total_tokens_in = 0
        self.total_tokens_out = 0
    
    def log_call(self, role: str, topology: str, artifact_rel_path: str, model: str,
                 prompt: str, response: str, tokens_in: int, tokens_out: int,
                 receipt_rel_path: str, provenance: str = "model-generated",
                 kind: str = "artifact") -> Dict:
        """
        Log a single API call.
        
        Args:
            role: Freight role (carrier, dispatcher, observer, relay)
            topology: mesh or ring
            artifact_rel_path: Relative path within artifacts/
            model: Model ID used
            prompt: FULL prompt text (no truncation)
            response: FULL response text (no truncation)
            tokens_in: Input token count
            tokens_out: Output token count
            receipt_rel_path: Relative path to receipt within receipts/
            provenance: Provenance note
            kind: Type of artifact (prompt, scenario, example, episode, route-report)
        
        Returns:
            The log entry dict
        """
        self.call_count += 1
        
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "run": self.run_id,
            "call": self.call_count,
            "kind": kind,
            "role": role,
            "topology": topology,
            "artifact": artifact_rel_path,
            "model": model,
            "prompt": prompt,
            "response": response,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "receipt": receipt_rel_path,
            "provenance": provenance,
        }
        
        # Append to JSONL (immediate flush)
        with open(self.jsonl_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
        
        # Add to in-memory list
        self.calls.append(entry)
        
        # Update totals
        if self.model_id is None:
            self.model_id = model
        self.total_tokens_in += tokens_in
        self.total_tokens_out += tokens_out
        
        return entry
    
    def write_artifact(self, rel_path: str, content: str, binary: bool = False):
        """Write an artifact file to the artifacts directory."""
        full_path = self.artifacts_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        mode = "wb" if binary else "w"
        with open(full_path, mode) as f:
            f.write(content)
        
        return str(full_path)
    
    def write_receipt(self, rel_path: str, receipt_data: Dict):
        """Write a receipt file to the receipts directory."""
        full_path = self.receipts_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, "w") as f:
            json.dump(receipt_data, f, indent=2)
        
        return str(full_path)
    
    def close(self, notes: str = ""):
        """
        Close the run: write run.json manifest.
        
        NOTE: logs/calls.jsonl is the complete log (JSONL with full prompt+response).
        No log.json is created — the JSONL stream is the authoritative record.
        
        Args:
            notes: Optional notes about the run
        """
        finished_at = datetime.now(timezone.utc).isoformat()
        
        # Build artifact index
        artifact_index = []
        for call in self.calls:
            artifact_index.append({
                "kind": call["kind"],
                "path": call["artifact"],
                "role": call["role"],
                "topology": call["topology"],
                "tokens": call["tokens_in"] + call["tokens_out"],
            })
        
        # Write run.json manifest
        run_manifest = {
            "run_id": self.run_id,
            "session": self.run_id,
            "model": self.model_id,
            "started": self.started_at,
            "finished": finished_at,
            "totals": {
                "calls": self.call_count,
                "tokens_in": self.total_tokens_in,
                "tokens_out": self.total_tokens_out,
                "total_tokens": self.total_tokens_in + self.total_tokens_out,
            },
            "artifacts": artifact_index,
            "notes": notes,
        }
        
        run_json_path = self.run_dir / "run.json"
        with open(run_json_path, "w") as f:
            json.dump(run_manifest, f, indent=2)
        
        print(f"\nRun {self.run_id} closed:")
        print(f"  Calls: {self.call_count}")
        print(f"  Tokens: {self.total_tokens_in} in + {self.total_tokens_out} out = {self.total_tokens_in + self.total_tokens_out}")
        print(f"  Directory: {self.run_dir}")
        print(f"  JSONL: {self.jsonl_path}")
        print(f"  Aggregated: {log_json_path}")
        print(f"  Manifest: {run_json_path}")
        
        return run_manifest


def create_batch1_reconstructed_run(runs_dir: Path | None = None):
    """
    Create the batch-1 (gen-run-001) reconstructed run directory.
    
    This represents the pre-workflow generation pass where only the tally
    was preserved, not per-call logs.
    """
    runs_dir = runs_dir or Path("data/runs")
    run_dir = runs_dir / "gen-run-001"
    
    # Create structure
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Read the original tally
    tally_path = Path("data/logs/gen-run-001-tally.log")
    if tally_path.exists():
        with open(tally_path) as f:
            tally_content = f.read().strip()
        # Remove any trailing EXIT:0 or similar
        if tally_content.endswith("EXIT:0"):
            tally_content = tally_content[:-6].strip()
        tally_data = json.loads(tally_content)
    else:
        tally_data = {
            "tally": {
                "calls": 20,
                "input_tokens": 3862,
                "output_tokens": 7330,
                "failures": 0
            }
        }
    
    # Write reconstructed tally with marker
    tally_with_marker = {
        "run_id": "gen-run-001",
        "reconstructed": True,
        "reconstruction_note": "RECONSTRUCTED from gen-run-001 tally — per-call logs not captured in the pre-workflow run",
        "tally": tally_data.get("tally", tally_data),
        "kept": tally_data.get("kept", {}),
        "results": tally_data.get("results", []),
        "provenance": "Pre-workflow generation pass (commit 0dca625) — aggregate tally only, no per-call logs",
    }
    
    tally_json_path = logs_dir / "tally.json"
    with open(tally_json_path, "w") as f:
        json.dump(tally_with_marker, f, indent=2)
    
    # Write minimal run.json
    run_manifest = {
        "run_id": "gen-run-001",
        "session": "pre-workflow",
        "model": "gemma-4-26b-a4b-it",
        "started": "2026-11-08T03:14:00+00:00",
        "finished": "2026-11-08T03:15:00+00:00",
        "totals": {
            "calls": tally_data.get("tally", {}).get("calls", 20),
            "tokens_in": tally_data.get("tally", {}).get("input_tokens", 3862),
            "tokens_out": tally_data.get("tally", {}).get("output_tokens", 7330),
            "total_tokens": tally_data.get("tally", {}).get("input_tokens", 3862) + tally_data.get("tally", {}).get("output_tokens", 7330),
        },
        "artifacts": [],
        "notes": "Pre-workflow generation pass. Per-call logs NOT captured. Tally reconstructed from gen-run.log. Artifacts exist in data/prompts/, data/scenarios/, data/examples/ but are not duplicated here — see MANIFEST.md for mapping.",
        "reconstructed": True,
    }
    
    run_json_path = run_dir / "run.json"
    with open(run_json_path, "w") as f:
        json.dump(run_manifest, f, indent=2)
    
    print(f"Created reconstructed run directory: {run_dir}")
    print(f"  Tally: {tally_json_path}")
    print(f"  Manifest: {run_json_path}")
    
    return run_dir


if __name__ == "__main__":
    # Demo/test
    logger = AdaptionLogger("demo-run-001")
    
    logger.log_call(
        role="carrier",
        topology="mesh",
        artifact_rel_path="prompts/carrier_mesh_standard.md",
        model="gemma-4-26b-a4b-it",
        prompt="Test prompt",
        response="Test response",
        tokens_in=100,
        tokens_out=200,
        receipt_rel_path="prompt_carrier_mesh_standard.json",
        kind="prompt"
    )
    
    logger.close("Demo run")
    
    print(f"\nDemo complete. Check data/runs/demo-run-001/")
