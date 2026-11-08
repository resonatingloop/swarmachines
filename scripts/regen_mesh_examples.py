#!/usr/bin/env python3
"""
Regenerate 4 MESH example calls for real receipts.
This script makes REAL API calls to Adaption to get proper receipts.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add adaption package location to path
sys.path.insert(0, '/opt/data/profiles/dev/home/.local/lib/python3.14/site-packages')

# Setup paths
REPO = Path('/workspace/clones/t005-gen-4')
os.chdir(REPO)
sys.path.insert(0, str(REPO / 'runtime'))

from adaption_adapter import AdaptionAdapter

DATA = REPO / 'data'
MODEL = "gemma-4-26b-a4b-it"
TS = datetime.now(timezone.utc).isoformat()

# Read original calls to get prompts
with open(DATA / 'runs/gen-full-20261108/logs/calls.jsonl', 'r') as f:
    calls = [json.loads(line) for line in f]

# MESH example calls to regenerate: 31, 33, 35, 37
mesh_call_indices = [30, 32, 34, 36]  # 0-indexed

adapter = AdaptionAdapter()
receipts_dir = DATA / 'runs/gen-full-20261108/receipts'

print("=== Regenerating 4 MESH example calls for real receipts ===\n")

regenerated = []

for idx in mesh_call_indices:
    call = calls[idx]
    call_num = call['call']
    artifact = call['artifact']
    prompt = call['prompt']
    
    print(f"Call {call_num}: {artifact} (topology={call['topology']})")
    
    # Make the API call
    messages = [{"role": "user", "content": prompt}]
    try:
        response = adapter.chat(model=MODEL, messages=messages, max_output_tokens=4096, temperature=0.8)
        
        print(f"  OK: {response.usage.input_tokens}+{response.usage.output_tokens} tokens")
        
        # Save receipt
        receipt_name = artifact.replace('/', '_').replace('.md', '').replace('.json', '')
        if call['topology'] == 'mesh':
            receipt_name += '_mesh'  # Distinguish from ring receipt
        
        receipt = {
            "schema_version": "v1",
            "call_name": f"{receipt_name}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": response.model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
            "item_path": f"data/{artifact}",
            "kind": call['kind'],
            "provenance": f"model-generated: {response.model} @ {TS}",
            "run_id": "gen-full-20261108-mesh-regen"
        }
        
        receipt_path = receipts_dir / f"{receipt_name}.json"
        with open(receipt_path, 'w') as f:
            json.dump(receipt, f, indent=2)
        print(f"  Receipt saved: {receipt_path.name}")
        
        # Update the artifact file with new response
        artifact_path = DATA / artifact
        new_content = response.output_text.rstrip()
        new_content += f"\n\n---\n*Provenance: model-generated narrative ({response.model} @ {TS}, regenerated for receipt).*\n"
        
        with open(artifact_path, 'w') as f:
            f.write(new_content)
        print(f"  Artifact updated: {artifact}")
        
        regenerated.append({
            "call": call_num,
            "artifact": artifact,
            "receipt": receipt_path.name,
            "tokens_out": response.usage.output_tokens
        })
        
    except Exception as e:
        print(f"  FAIL: {e}")
        regenerated.append({
            "call": call_num,
            "artifact": artifact,
            "error": str(e)
        })

print("\n=== Regeneration complete ===")
print(f"Regenerated {len(regenerated)} calls:")
for r in regenerated:
    print(f"  {r}")
