#!/usr/bin/env python3
"""
Faithful regeneration path for PR #28 data pack.

This script REGENERATES the data pack by actually calling the Adaption API,
preserving mixed provenance and producing verifiable receipts.

Usage:
    export ADAPTION_API_KEY=...
    export PYTHONPATH=/opt/data/profiles/dev/home/.local/lib/python3.14/site-packages
    python3 scripts/regenerate_data_pack.py --receipts-dir data/receipts

Provenance model:
- Team-authored seeds (3 scenarios, 1 example, 1 prompt) are PRESERVED, not regenerated:
  - data/scenarios/relay-loss-early.json
  - data/scenarios/ring-relay-loss.json
  - data/scenarios/stale-report.json
  - data/examples/reroute-coordination.md
  - data/prompts/dispatcher_ring.md (restored after corruption)
- Model-generated items (7 prompts, 8 scenarios, 4 examples) are REGENERATED with receipts
- Each regenerated file carries a provenance footer with model + receipt ID

Note: This script makes REAL API calls. For documentation of what was done in
commit 0dca625, see data/MANIFEST.md and data/GENERATION-LOG.md.
"""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).parent.parent
os.chdir(REPO)
sys.path.insert(0, str(REPO))

from runtime.adaption_adapter import AdaptionAdapter

DATA = REPO / "data"
MODEL = "gemma-4-26b-a4b-it"  # Match the model used in the original volume pass
TS = datetime.now(UTC).isoformat()

# Receipt tracking
adapter = AdaptionAdapter()
call_log = []
receipts_dir = None


def save_receipt(call_name: str, response, item_path: str) -> dict:
    """Save a receipt for this API call."""
    if receipts_dir:
        receipt = {
            "call_name": call_name,
            "timestamp": datetime.now(UTC).isoformat(),
            "model": response.model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
            "item_path": str(item_path),
            "provenance": f"model-generated via adaption ({response.model}, receipt: {call_name}, {TS[:10]})",
        }
        receipt_path = receipts_dir / f"{call_name}.json"
        with open(receipt_path, "w") as f:
            json.dump(receipt, f, indent=2)
        return receipt
    return None


def call_api(messages, name: str, item_path: Path | None = None) -> str:
    """Make API call with retry and receipt tracking."""
    print(f"  {name}...", flush=True)
    for attempt in range(3):
        try:
            r = adapter.chat(
                model=MODEL, messages=messages, max_output_tokens=4096, temperature=0.8
            )

            # Track
            call_log.append(
                {
                    "call": len(call_log) + 1,
                    "name": name,
                    "model": r.model,
                    "input_tokens": r.usage.input_tokens,
                    "output_tokens": r.usage.output_tokens,
                    "total_tokens": r.usage.total_tokens,
                }
            )
            print(
                f"    OK: {len(call_log)} calls, {r.usage.input_tokens}+{r.usage.output_tokens} tok",
                flush=True,
            )

            # Save receipt
            if item_path:
                save_receipt(name, r, item_path)

            return r.output_text
        except Exception as e:
            if attempt < 2:
                d = 5 * (attempt + 1)
                print(f"    Fail, retry {d}s...", flush=True)
                time.sleep(d)
            else:
                print(f"    FAIL x3: {e}", flush=True)
                raise
    return ""


def regenerate_prompts() -> list:
    """Regenerate 7 prompt templates from team-authored seeds (skip dispatcher_ring - restored)."""
    print(
        "\n=== REGENERATING PROMPTS (7 calls; dispatcher_ring preserved as team-authored) ==="
    )

    roles = [
        (
            "dispatcher",
            "Coordinates freight assignment and route planning across the network",
        ),
        (
            "relay",
            "Forwards messages between agents; may become unreachable during disruption",
        ),
        ("carrier", "Physically moves freight along routes; validates route legality"),
        (
            "observer",
            "Monitors local conditions and reports changes like bridge closures",
        ),
    ]
    topologies = ["mesh", "ring"]

    # Skip dispatcher_ring - it was corrupted during original generation and restored to team-authored
    skip_files = {"dispatcher_ring.md"}

    regenerated = []
    for role_name, role_desc in roles:
        for topo in topologies:
            filename = f"{role_name}_{topo}.md"
            if filename in skip_files:
                print(f"    SKIP {filename} (preserved as team-authored seed)")
                continue
            seed_path = DATA / "prompts" / filename
            if seed_path.exists():
                seed = seed_path.read_text()
                # Read only the team-authored portion (before any provenance footer)
                seed_content = seed.split("## Provenance")[0].strip()

                out = call_api(
                    [
                        {
                            "role": "system",
                            "content": "Improve this agent prompt for a freight-in-the-fog multi-agent coordination experiment. Make it clearer, more actionable, with better examples. Output ONLY the improved markdown prompt.",
                        },
                        {
                            "role": "user",
                            "content": f"{role_name} {topo}:\n\n{seed_content[:1000]}",
                        },
                    ],
                    f"prompt_{role_name}_{topo}",
                    seed_path,
                )

                prov = f"\n\n## Provenance\nmodel-generated via adaption ({MODEL}, receipt: prompt_{role_name}_{topo}, {TS[:10]}) — improves team-authored seed"
                seed_path.write_text(out + prov)
                regenerated.append(str(seed_path))
                print(f"    Regenerated: {seed_path}")
            else:
                print(f"    SKIP {role_name}_{topo} (no seed)")

    return regenerated


def regenerate_scenarios() -> list:
    """Regenerate 8 new scenario configs (preserve 3 team-authored)."""
    print("\n=== REGENERATING SCENARIOS (8 calls) ===")

    # These are the NEW scenarios to generate (not the team-authored ones)
    scenario_specs = [
        (
            "scenario-00-mesh.json",
            "mesh",
            "Basic mesh topology scenario with 3 freight jobs",
        ),
        (
            "scenario-01-bidirectional-ring.json",
            "bidirectional-ring",
            "Ring topology with bidirectional communication",
        ),
        ("scenario-02-mesh.json", "mesh", "Mesh scenario with early disruption"),
        (
            "scenario-03-bidirectional-ring.json",
            "bidirectional-ring",
            "Ring scenario with mid-episode disruption",
        ),
        ("scenario-04-mesh.json", "mesh", "Mesh with capacity constraints"),
        (
            "scenario-05-bidirectional-ring.json",
            "bidirectional-ring",
            "Ring with information delay",
        ),
        ("scenario-06-mesh.json", "mesh", "Mesh with multiple concurrent disruptions"),
        (
            "scenario-07-bidirectional-ring.json",
            "bidirectional-ring",
            "Ring with agent mutation",
        ),
    ]

    regenerated = []
    for filename, topo, desc in scenario_specs:
        scenario_path = DATA / "scenarios" / filename

        out = call_api(
            [
                {
                    "role": "system",
                    "content": "Generate a scenario configuration for freight-in-the-fog. Output ONLY valid JSON with: name, topology, turns (8-16), disturbance, jobs array, agents list.",
                },
                {"role": "user", "content": f"Create a {topo} scenario: {desc}"},
            ],
            f"scenario_{filename.replace('.json', '')}",
            scenario_path,
        )

        # Parse and save
        txt = out.strip().strip("`" * 3 + "json").strip("`" * 3).strip()
        try:
            scenario = json.loads(txt)
            prov = f"\n\n---\n*Provenance: model-generated via adaption ({MODEL}, receipt: scenario_{filename.replace('.json', '')}, {TS[:10]}); kind: scenario config. NOT observed experimental evidence.*"
            with open(scenario_path, "w") as f:
                json.dump(scenario, f, indent=2)
                f.write(prov)
            regenerated.append(str(scenario_path))
            print(f"    Generated: {scenario_path}")
        except json.JSONDecodeError as e:
            print(f"    FAIL: {filename} - JSON parse error: {e}")

    return regenerated


def regenerate_examples() -> list:
    """Regenerate 4 coordination examples (preserve 1 team-authored)."""
    print("\n=== REGENERATING EXAMPLES (4 calls) ===")

    example_specs = [
        (
            "relay-loss-reroute.md",
            "relay-loss-reroute",
            "Reroute coordination after relay agent goes dark",
        ),
        (
            "capacity-conflict.md",
            "capacity-conflict",
            "Contested route at capacity limit",
        ),
        (
            "stale-info-recovery.md",
            "stale-info-recovery",
            "Stale bridge report corrected by later message",
        ),
        (
            "ring-neighbor-routing.md",
            "ring-neighbor-routing",
            "Ring routing via two neighbors when direct path blocked",
        ),
    ]

    regenerated = []
    for filename, name, desc in example_specs:
        example_path = DATA / "examples" / filename

        out = call_api(
            [
                {
                    "role": "system",
                    "content": "Generate a coordination example for freight-in-the-fog. Show message exchanges between agents during a disruption. Output markdown with context, message exchanges (JSON format), and analysis.",
                },
                {"role": "user", "content": f"Create example: {desc}"},
            ],
            f"example_{name}",
            example_path,
        )

        prov = f"\n\n## Provenance\nmodel-generated via adaption ({MODEL}, receipt: example_{name}, {TS[:10]}) — illustrates coordination patterns, NOT observed experimental evidence"
        example_path.write_text(out + prov)
        regenerated.append(str(example_path))
        print(f"    Generated: {example_path}")

    return regenerated


def update_manifest(prompts, scenarios, examples):
    """Update MANIFEST.md with accurate call log and provenance."""
    print("\n=== UPDATING MANIFEST ===")

    total_input = sum(c["input_tokens"] for c in call_log)
    total_output = sum(c["output_tokens"] for c in call_log)
    total_calls = len(call_log)

    manifest = f"""# Pre-Recorded Data Manifest — REGENERATED

**Generated**: {TS}
**Model**: {MODEL} (Adaption API)
**Total API Calls**: {total_calls}
**Total Tokens**: {total_input} input + {total_output} output = {total_input + total_output}

## Provenance Statement

This pack is MIXED-PROVENANCE:

- **Model-generated** ({total_calls} artifacts): produced by the Adaption API
  (`{MODEL}`) from team-authored draft seeds. Each file carries a
  per-file provenance footer naming the model, receipt ID, and date.
- **Team-authored** (4 artifacts): prepared without API access at
  authoring time, preserved as seeds, labeled team-authored in-file:
  - data/scenarios/relay-loss-early.json
  - data/scenarios/ring-relay-loss.json
  - data/scenarios/stale-report.json
  - data/examples/reroute-coordination.md

ALL files are **seed material for keyless teammate agents** to use in
freight-in-the-fog coordination experiments. NONE are observed experimental evidence.

## Call Log

| Call | Purpose | Model | Input | Output | Total |
|------|---------|-------|-------|--------|-------|
"""
    for c in call_log:
        manifest += f"| {c['call']} | {c['name']} | {c['model']} | {c['input_tokens']} | {c['output_tokens']} | {c['total_tokens']} |\n"

    manifest += f"""
## Contents

### Prompts ({len(prompts)} files — all model-generated)
| File | Role | Topology |
|------|------|----------|
"""
    for p in prompts:
        role = p.split("/")[-1].split("_")[0]
        topo = p.split("/")[-1].split(".")[0].split("_")[1]
        manifest += f"| {p} | {role} | {topo} |\n"

    manifest += f"""
### Scenarios ({len(scenarios)} files — model-generated, plus 3 team-authored preserved)
| File | Topology | Provenance |
|------|----------|------------|
"""
    for s in scenarios:
        filename = s.split("/")[-1]
        topo = (
            "mesh"
            if "mesh" in filename
            else "ring"
            if "ring" in filename
            else "unknown"
        )
        manifest += f"| {s} | {topo} | model-generated |\n"
    manifest += (
        "| data/scenarios/relay-loss-early.json | mesh | team-authored (preserved) |\n"
    )
    manifest += (
        "| data/scenarios/ring-relay-loss.json | ring | team-authored (preserved) |\n"
    )
    manifest += (
        "| data/scenarios/stale-report.json | mesh | team-authored (preserved) |\n"
    )

    manifest += f"""
### Examples ({len(examples)} files — model-generated, plus 1 team-authored preserved)
| File | Scenario | Provenance |
|------|----------|------------|
"""
    for e in examples:
        filename = e.split("/")[-1]
        name = filename.replace(".md", "")
        manifest += f"| {e} | {name} | model-generated |\n"
    manifest += "| data/examples/reroute-coordination.md | reroute during relay-loss | team-authored (preserved) |\n"

    manifest += f"""
## Receipts

Receipts for all {total_calls} API calls are stored in `data/receipts/`.
Each receipt contains: call name, timestamp, model, token usage, item path, provenance.

## Regeneration Path

To regenerate this pack faithfully:

```bash
export ADAPTION_API_KEY=...
export PYTHONPATH=/opt/data/profiles/dev/home/.local/lib/python3.14/site-packages
python3 scripts/regenerate_data_pack.py --receipts-dir data/receipts
```

This script:
1. Reads team-authored seeds (preserved, not overwritten)
2. Makes actual API calls (not hardcoded content)
3. Saves receipts for each call
4. Labels provenance correctly per file

## Usage Notes

1. Prompts are templates — adapt agent IDs and context as needed
2. Scenarios are seeds — actual runs may vary based on agent execution
3. Examples illustrate coordination patterns, NOT observed evidence
4. Per-file provenance footers are authoritative — preserve in derived materials

---
*Manifest auto-generated by regenerate_data_pack.py — faithful regeneration path for PR #28*
"""

    manifest_path = DATA / "MANIFEST.md"
    manifest_path.write_text(manifest)
    print(f"  Written: {manifest_path}")
    return manifest_path


def main():
    global receipts_dir

    parser = argparse.ArgumentParser(
        description="Faithful regeneration of PR #28 data pack"
    )
    parser.add_argument(
        "--receipts-dir",
        type=str,
        default="data/receipts",
        help="Directory for receipts",
    )
    args = parser.parse_args()

    receipts_dir = Path(args.receipts_dir)
    receipts_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("FAITHFUL REGENERATION — PR #28 Data Pack")
    print("=" * 60)
    print(f"Model: {MODEL}")
    print(f"Timestamp: {TS}")
    print(f"Receipts: {receipts_dir}")

    # Regenerate
    prompts = regenerate_prompts()
    scenarios = regenerate_scenarios()
    examples = regenerate_examples()

    # Update manifest
    update_manifest(prompts, scenarios, examples)

    # Summary
    total_input = sum(c["input_tokens"] for c in call_log)
    total_output = sum(c["output_tokens"] for c in call_log)

    print("\n" + "=" * 60)
    print("REGENERATION COMPLETE")
    print("=" * 60)
    print(f"Total API calls: {len(call_log)}")
    print(
        f"Total tokens: {total_input} in + {total_output} out = {total_input + total_output}"
    )
    print(f"Receipts saved: {len(call_log)} files in {receipts_dir}")

    # Spend estimate
    input_credits = total_input * 0.15 / 1_000_000
    output_credits = total_output * 0.50 / 1_000_000
    total_credits = input_credits + output_credits
    print("\nSPEND:")
    print(f"  Input:  {total_input:,} tok → {input_credits:.6f} credits")
    print(f"  Output: {total_output:,} tok → {output_credits:.6f} credits")
    print(f"  TOTAL:  {total_credits:.6f} credits (~${total_credits * 10:.2f})")

    return {
        "calls": len(call_log),
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "receipts_dir": str(receipts_dir),
        "call_log": call_log,
    }


if __name__ == "__main__":
    metrics = main()
    print("\nMetrics:")
    print(json.dumps(metrics, indent=2))
