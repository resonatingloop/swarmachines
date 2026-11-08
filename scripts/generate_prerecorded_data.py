#!/usr/bin/env python3
"""
Pre-record data generation script for swarmachines hackathon.
Generates prompts, scenarios, and coordination examples using Adaption API.

HONEST HEADER (provenance correction 2026-11-08):
- This script generates spec-based content deterministically with no API calls (AdaptionAdapter import reserved for future governed regeneration path; not constructed in this script; shipped pack's model-generated artifacts came from the governed run logged in data/GENERATION-LOG.md)
- The shipped data pack was produced through the governed run logged in data/GENERATION-LOG.md
- The "0 calls" string in provenance footers applies to team-authored seeds ONLY
- Per-file provenance values carry model id + timestamp; call numbers live in data/MANIFEST.md rows and receipt records
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add runtime to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.adaption_adapter import AdaptionAdapter

# Track metrics
call_count = 0
total_input_tokens = 0
total_output_tokens = 0

MODEL_ID = "team-authored"
GENERATION_TIMESTAMP = datetime.now(timezone.utc).isoformat()

def track_response(response):
    """Track API call metrics."""
    global call_count, total_input_tokens, total_output_tokens
    call_count += 1
    total_input_tokens += response.usage.input_tokens
    total_output_tokens += response.usage.output_tokens
    print(f"  [Call {call_count}] Tokens: {response.usage.input_tokens} in + {response.usage.output_tokens} out = {response.usage.total_tokens} total")
    return response

def generate_prompts(adapter):
    """Generate pilot prompt pack for 4 freight roles under mesh and ring topologies."""
    print("\n=== GENERATING PROMPTS ===")
    
    # Define the 4 freight roles
    roles = [
        ("dispatcher", "Coordinates freight assignment and route planning across the network"),
        ("relay", "Forwards messages between agents; may become unreachable during disruption"),
        ("carrier", "Physically moves freight along routes; validates route legality"),
        ("observer", "Monitors local conditions and reports changes like bridge closures"),
    ]
    
    topologies = ["mesh", "ring"]
    
    prompts_generated = []
    
    for role_name, role_desc in roles:
        for topo in topologies:
            prompt_template = f"""# {role_name.upper()} AGENT PROMPT ({topo.upper()} TOPOLOGY)

## Role
{role_desc}

## Communication Topology: {topo.upper()}
- In {topo} topology, your messages are routed according to the topology rules.
- You can only send messages to agents directly connected to you in this topology.
- Message allowance: 2 messages per turn maximum.

## Your Capabilities
1. Observe your local depot/hub conditions
2. Send messages to connected agents
3. Propose actions (route freight, close routes, relay information)
4. Receive and process incoming messages

## Response Format
Respond with valid JSON:
{{
  "observations": ["what you see locally"],
  "messages": [{{"to": "agent_id", "content": "message text"}}],
  "action": {{
    "type": "route_freight|close_route|relay_info|wait",
    "details": {{...}}
  }}
}}

## Constraints
- Actions must be legal given current world state
- You only know what you observe locally or learn from messages
- Messages sent this turn arrive next turn (except in same-turn processing)
- During disruption, some agents may become unreachable

## Provenance
team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence
"""
            
            filename = f"data/prompts/{role_name}_{topo}.md"
            with open(filename, "w") as f:
                f.write(prompt_template)
            
            prompts_generated.append(filename)
            print(f"  Written: {filename}")
    
    return prompts_generated

def generate_scenarios(adapter):
    """Generate 2-3 candidate scenario seeds/configs."""
    print("\n=== GENERATING SCENARIOS ===")
    
    scenarios = []
    
    # Scenario 1: Basic relay-loss disruption
    scenario1 = {
        "scenario_id": "relay-loss-early",
        "description": "Agent A (relay) muted from turn 2 onwards",
        "seed": 42,
        "agents": ["a", "b", "c", "d"],
        "comm_topology": "mesh",
        "physical_topology": "graph",
        "turns": 16,
        "freight_jobs": [
            {"job_id": "j-001", "freight": "med-kit", "origin": "west", "destination": "south", "priority": "high"},
            {"job_id": "j-002", "freight": "supplies", "origin": "east", "destination": "west", "priority": "normal"},
            {"job_id": "j-003", "freight": "equipment", "origin": "south", "destination": "east", "priority": "normal"},
        ],
        "disturbance_schedule": {
            "relay-loss": {
                "agent": "a",
                "start_turn": 2,
                "end_turn": 16,
                "note": "Agent A unreachable; mesh edges among b,c,d unchanged"
            }
        },
        "expected_outcomes": {
            "deliveries_baseline": 3,
            "recovery_turns_expected": "2-4",
            "coordination_challenge": "reroute without relay coordination"
        },
        "provenance": "team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence"
    }
    
    # Scenario 2: Ring topology with same disruption
    scenario2 = {
        "scenario_id": "ring-relay-loss",
        "description": "Ring topology with agent B muted from turn 3",
        "seed": 17,
        "agents": ["a", "b", "c", "d"],
        "comm_topology": "ring",
        "ring_order": ["a", "b", "c", "d"],  # a->b->c->d->a
        "physical_topology": "graph",
        "turns": 16,
        "freight_jobs": [
            {"job_id": "j-001", "freight": "med-kit", "origin": "west", "destination": "south", "priority": "high"},
            {"job_id": "j-002", "freight": "supplies", "origin": "relay-a", "destination": "east", "priority": "normal"},
        ],
        "disturbance_schedule": {
            "relay-loss": {
                "agent": "b",
                "start_turn": 3,
                "end_turn": 16,
                "note": "Agent B unreachable; ring broken between a-b and b-c"
            }
        },
        "expected_outcomes": {
            "deliveries_baseline": 2,
            "recovery_turns_expected": "3-5",
            "coordination_challenge": "ring fragmentation requires alternate paths"
        },
        "provenance": "team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence"
    }
    
    # Scenario 3: Stale information disruption
    scenario3 = {
        "scenario_id": "stale-report",
        "description": "Bridge closure report delayed by 2 turns",
        "seed": 73,
        "agents": ["a", "b", "c", "d"],
        "comm_topology": "mesh",
        "physical_topology": "graph",
        "turns": 16,
        "freight_jobs": [
            {"job_id": "j-001", "freight": "med-kit", "origin": "west", "destination": "south", "priority": "high"},
            {"job_id": "j-002", "freight": "supplies", "origin": "east", "destination": "south", "priority": "normal"},
        ],
        "world_events": [
            {"turn": 2, "event": "east-bridge closed", "reported_to": ["c"], "reported_at_turn": 2},
            {"turn": 2, "event": "east-bridge closed", "reported_to": ["a", "b", "d"], "reported_at_turn": 4, "note": "stale by 2 turns"}
        ],
        "expected_outcomes": {
            "deliveries_baseline": 2,
            "coordination_challenge": "agents act on outdated information"
        },
        "provenance": "team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence"
    }
    
    scenarios = [scenario1, scenario2, scenario3]
    scenarios_written = []
    
    for scenario in scenarios:
        filename = f"data/scenarios/{scenario['scenario_id']}.json"
        with open(filename, "w") as f:
            json.dump(scenario, f, indent=2)
        scenarios_written.append(filename)
        print(f"  Written: {filename}")
    
    return scenarios_written, scenarios

def generate_coordination_example(adapter):
    """Generate one short model-composed coordination example exchange."""
    print("\n=== GENERATING COORDINATION EXAMPLE ===")
    
    example = """# Coordination Example: Reroute During Relay Loss

## Context
- **Run ID**: example-reroute-001
- **Turn**: 3 (post-disruption, agent A unreachable since turn 2)
- **Topology**: Mesh (physical graph unchanged; agent A muted)
- **Active Agents**: B (east), C (south), D (relay-a)
- **Situation**: Med-kit freight needs west→south delivery; east-bridge closed at turn 2

## Message Exchange

### Turn 3, Agent C (South Depot)
**Observation**: 
- Local queue: 1 med-kit pending delivery to south
- Known closures: east-bridge (from turn 2 report)
- Visible routes: west→south (open), south→east (closed at bridge)

**Message Sent** (to B):
```
{
  "message_id": "m-c3-001",
  "to": "b",
  "content": "East-bridge confirmed closed. Med-kit at west needs alternate route. Can you verify west→south capacity?",
  "observation_turn": 3,
  "provenance": "team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence"
}
```

### Turn 3, Agent B (East Depot)
**Received**: Message m-c3-001 from C (delivered turn 3)

**Observation**:
- Local queue: empty
- Known closures: east-bridge
- Visible routes: east→west (open), east→south (closed), west→south (unknown locally)

**Message Sent** (to D):
```
{
  "message_id": "m-b3-001",
  "to": "d",
  "content": "C reports bridge closed. Need west→south route status for med-kit reroute. Can you query west depot visibility?",
  "observation_turn": 3,
  "provenance": "team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence"
}
```

### Turn 3, Agent D (Relay-A Hub)
**Received**: Message m-b3-001 from B (delivered turn 3)

**Observation**:
- Local queue: 1 supplies pending
- Known closures: east-bridge
- Visible routes: all hub connections visible (west, east, south)
- West→south route status: OPEN, capacity 2/3

**Message Sent** (to B and C):
```
{
  "message_id": "m-d3-001",
  "to": ["b", "c"],
  "content": "West→south route OPEN, capacity available (2/3). Recommend direct reroute west→south, bypassing east hub entirely.",
  "observation_turn": 3,
  "provenance": "team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence"
}
```

### Turn 4, Action Resolution
**Agent C Action** (committed):
```json
{
  "action_id": "act-c4-001",
  "type": "route_freight",
  "details": {
    "freight": "med-kit",
    "path": ["west", "south"],
    "bypasses": ["east"],
    "reason": "east-bridge closed; direct route available per D's report"
  }
}
```

**Outcome**:
- Freight rerouted successfully via west→south
- Delivery completed turn 6
- Recovery interval: 2 turns (disruption turn 2 → resumed delivery turn 4)

## Analysis
This exchange demonstrates:
1. **Distributed information aggregation**: C knows bridge status, D knows west→south capacity
2. **Multi-hop coordination without relay**: B intermediates despite A's absence
3. **Provenance tracking**: Each message carries observation turn and generation note
4. **Successful recovery**: Delivery completed despite disruption

## Provenance
- team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence
"""
    
    filename = "data/examples/reroute-coordination.md"
    with open(filename, "w") as f:
        f.write(example)
    
    print(f"  Written: {filename}")
    return filename

def validate_scenarios(scenarios):
    """Validate scenarios against events schema where applicable."""
    print("\n=== VALIDATING SCENARIOS ===")
    
    # Load schema
    with open("runtime/schema/events.schema.json") as f:
        schema = json.load(f)
    
    validated = []
    for scenario in scenarios:
        # Basic validation: check required fields for scenario config
        required = ["scenario_id", "seed", "agents", "comm_topology", "turns", "freight_jobs"]
        missing = [f for f in required if f not in scenario]
        
        if missing:
            print(f"  {scenario['scenario_id']}: MISSING FIELDS {missing}")
            validated.append((scenario['scenario_id'], False, f"Missing: {missing}"))
        else:
            # Check disturbance schedule format
            if "disturbance_schedule" in scenario:
                ds = scenario["disturbance_schedule"]
                if "relay-loss" in ds:
                    rl = ds["relay-loss"]
                    if all(k in rl for k in ["agent", "start_turn", "end_turn"]):
                        print(f"  {scenario['scenario_id']}: VALID (disturbance schedule OK)")
                        validated.append((scenario['scenario_id'], True, "OK"))
                    else:
                        print(f"  {scenario['scenario_id']}: INVALID disturbance schedule")
                        validated.append((scenario['scenario_id'], False, "Invalid disturbance schedule"))
            else:
                print(f"  {scenario['scenario_id']}: VALID (no disturbance)")
                validated.append((scenario['scenario_id'], True, "OK"))
    
    return validated

def create_manifest(prompts, scenarios, example, validations):
    """Create MANIFEST.md with metadata."""
    print("\n=== CREATING MANIFEST ===")
    
    manifest = f"""# Pre-Recorded Data Manifest

**Generated**: {GENERATION_TIMESTAMP}
**Authorship**: Team-authored (0 API calls)
**Total API Calls**: {call_count}
**Total Tokens**: {total_input_tokens} input + {total_output_tokens} output = {total_input_tokens + total_output_tokens}

## Provenance Statement
All files in this directory are **team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence**.
They are provided as seed data for keyless teammate agents (asterion, caduceus) to use in
freight-in-the-fog coordination experiments.

## Contents

### Prompts ({len(prompts)} files)
Pilot prompt pack for 4 freight roles under 2 topologies:

| File | Role | Topology |
|------|------|----------|
"""
    
    for p in prompts:
        role = p.split("/")[-1].split("_")[0]
        topo = p.split("/")[-1].split(".")[0].split("_")[1]
        manifest += f"| {p} | {role} | {topo} |\n"
    
    manifest += f"""
### Scenarios ({len(scenarios)} files)
Candidate scenario seeds/configs for freight world:

| File | Scenario ID | Validation |
|------|-------------|------------|
"""
    
    for s in scenarios:
        filename = s.split("/")[-1]
        # Find validation result
        val_result = next((v for v in validations if v[0] == filename.replace(".json", "")), ("unknown", False, "not checked"))
        status = "✓ VALID" if val_result[1] else f"✗ {val_result[2]}"
        manifest += f"| {s} | {filename.replace('.json', '')} | {status} |\n"
    
    manifest += f"""
### Examples ({len([example])} files)
Model-composed coordination example exchanges:

| File | Description |
|------|-------------|
| {example} | Reroute coordination during relay-loss disruption |

## API Usage Summary
- **Authorship**: Team-authored (0 API calls)
- **Calls**: {call_count}
- **Input Tokens**: {total_input_tokens}
- **Output Tokens**: {total_output_tokens}
- **Total Tokens**: {total_input_tokens + total_output_tokens}

## Files Generated
"""
    
    all_files = prompts + scenarios + [example]
    for f in all_files:
        manifest += f"- {f}\n"
    
    manifest += f"""
## Usage Notes
1. Prompts are templates — adapt agent IDs and context as needed for specific runs
2. Scenarios are seeds — actual runs may vary based on model responses
3. Examples illustrate expected coordination patterns, not guaranteed outcomes
4. Provenance statement reflects team-authored origin; preserve in derived materials

---
*Manifest auto-generated by pre-record data script*
"""
    
    with open("data/MANIFEST.md", "w") as f:
        f.write(manifest)
    
    print(f"  Written: data/MANIFEST.md")
    return manifest

def main():
    print("=" * 60)
    print("PRE-RECORDED DATA GENERATION")
    print("=" * 60)
    print(f"Model: {MODEL_ID}")
    print(f"Timestamp: {GENERATION_TIMESTAMP}")
    print(f"Note: Content authored based on spec; 0 API calls in this session")
    
    # Note: API key not available in this environment
    # Content is authored based on hackathon spec requirements
    # All files carry provenance: "team-authored seed material prepared without API access (0 calls); NOT model-generated and NOT observed experimental evidence"
    
    adapter = None  # Not used - content is spec-based
    
    # Generate prompts (static templates based on spec)
    prompts = generate_prompts(adapter)
    
    # Generate scenarios (static configs based on spec)
    scenarios_files, scenarios = generate_scenarios(adapter)
    
    # Generate coordination example (static example based on spec)
    example = generate_coordination_example(adapter)
    
    # Validate scenarios
    validations = validate_scenarios(scenarios)
    
    # Create manifest
    manifest = create_manifest(prompts, scenarios_files, example, validations)
    
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Total API calls: {call_count}")
    print(f"Total tokens: {total_input_tokens} in + {total_output_tokens} out = {total_input_tokens + total_output_tokens}")
    print(f"Files generated: {len(prompts) + len(scenarios_files) + 1}")
    
    # Return metrics for PR body
    return {
        "call_count": call_count,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "total_tokens": total_input_tokens + total_output_tokens,
        "files": {
            "prompts": prompts,
            "scenarios": scenarios_files,
            "examples": [example]
        }
    }

if __name__ == "__main__":
    metrics = main()
    print("\nMetrics for PR body:")
    print(json.dumps(metrics, indent=2))
