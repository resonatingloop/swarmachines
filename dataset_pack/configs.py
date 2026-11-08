"""
dataset_pack/configs.py — versioned task-instance configs for HF dataset pack

Defines exactly 5 seeded task instances for the freight-in-the-fog world.
Each config carries: seed, graph, job set, agent roster, topology, disturbance schedule.
No two instances share both seed and job set.
At least one instance uses the mute-one-agent (peer-mute) disturbance.
Supports deterministic replay from seed (byte-identical re-run).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TaskInstanceConfig:
    """
    A versioned task instance configuration for dataset generation.

    Attributes:
        instance_id: Unique identifier for this task instance (e.g., "task-001").
        seed: Random seed for deterministic world state and agent behavior.
        graph: Graph configuration (depots, hubs, routes).
        job_set: List of delivery jobs (freight_id, origin, destination, freight_type).
        agent_roster: List of agent IDs participating in this instance.
        topology: Communication topology ("mesh", "hub-spoke", "bidirectional-ring").
        hub: Hub agent ID for hub-spoke topology (None if not applicable).
        disturbance_schedule: Dict mapping disturbance kind to schedule config.
        turns: Number of turns to run this instance.
        policy: Agent policy ("legacy" or "route-gossip-v1").
    """

    instance_id: str
    seed: int
    graph: dict[str, Any]
    job_set: list[dict[str, str]]
    agent_roster: list[str]
    topology: str
    hub: str | None = None
    disturbance_schedule: dict[str, Any] = field(default_factory=dict)
    turns: int = 16
    policy: str = "route-gossip-v1"

    def config_hash(self) -> str:
        """Compute a deterministic hash of this config for provenance tracking."""
        config_dict = {
            "instance_id": self.instance_id,
            "seed": self.seed,
            "graph": self.graph,
            "job_set": self.job_set,
            "agent_roster": self.agent_roster,
            "topology": self.topology,
            "hub": self.hub,
            "disturbance_schedule": self.disturbance_schedule,
            "turns": self.turns,
            "policy": self.policy,
        }
        config_json = json.dumps(config_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(config_json.encode("utf-8")).hexdigest()[:16]

    def to_runner_args(self) -> dict[str, Any]:
        """Convert this config to arguments for the TurnSeamRunner."""
        return {
            "seed": self.seed,
            "comm_topology": self.topology,
            "agents_config": self.agent_roster,
            "disturbance_schedule": self.disturbance_schedule,
            "delivery_map": {"hub": self.hub} if self.hub else {},
            "use_freight_world": True,
            "policy": self.policy,
        }


def get_task_configs() -> list[TaskInstanceConfig]:
    """
    Return the 5 versioned task-instance configs for the dataset pack.

    Requirements:
    - Exactly 5 configs
    - No two share both seed AND job_set
    - At least one uses peer-mute disturbance
    - Vary topology across instances for comparison
    """
    # Common graph structure (freight-in-the-fog world)
    base_graph = {
        "depots": ["west", "east", "south"],
        "hubs": ["relay-a"],
        "routes": [
            {"from": "west", "to": "east", "status": "open"},
            {"from": "east", "to": "west", "status": "open"},
            {"from": "east", "to": "south", "status": "open", "bridge": "east-bridge"},
            {"from": "south", "to": "east", "status": "open", "bridge": "east-bridge"},
            {"from": "west", "to": "south", "status": "open"},
            {"from": "south", "to": "west", "status": "open"},
        ],
    }

    # Define 5 distinct job sets
    job_sets = [
        # Job set 1: standard distribution
        [
            {
                "freight_id": "f-001",
                "origin": "west",
                "destination": "south",
                "freight_type": "med-kit",
            },
            {
                "freight_id": "f-002",
                "origin": "east",
                "destination": "west",
                "freight_type": "supplies",
            },
            {
                "freight_id": "f-003",
                "origin": "south",
                "destination": "east",
                "freight_type": "equipment",
            },
            {
                "freight_id": "f-004",
                "origin": "relay-a",
                "destination": "west",
                "freight_type": "med-kit",
            },
        ],
        # Job set 2: reversed routes
        [
            {
                "freight_id": "f-001",
                "origin": "south",
                "destination": "west",
                "freight_type": "supplies",
            },
            {
                "freight_id": "f-002",
                "origin": "west",
                "destination": "east",
                "freight_type": "equipment",
            },
            {
                "freight_id": "f-003",
                "origin": "east",
                "destination": "south",
                "freight_type": "med-kit",
            },
            {
                "freight_id": "f-004",
                "origin": "relay-a",
                "destination": "south",
                "freight_type": "supplies",
            },
        ],
        # Job set 3: hub-focused
        [
            {
                "freight_id": "f-001",
                "origin": "west",
                "destination": "relay-a",
                "freight_type": "equipment",
            },
            {
                "freight_id": "f-002",
                "origin": "east",
                "destination": "relay-a",
                "freight_type": "med-kit",
            },
            {
                "freight_id": "f-003",
                "origin": "south",
                "destination": "relay-a",
                "freight_type": "supplies",
            },
            {
                "freight_id": "f-004",
                "origin": "relay-a",
                "destination": "east",
                "freight_type": "equipment",
            },
        ],
        # Job set 4: cross-depot
        [
            {
                "freight_id": "f-001",
                "origin": "west",
                "destination": "east",
                "freight_type": "med-kit",
            },
            {
                "freight_id": "f-002",
                "origin": "east",
                "destination": "south",
                "freight_type": "supplies",
            },
            {
                "freight_id": "f-003",
                "origin": "south",
                "destination": "west",
                "freight_type": "equipment",
            },
            {
                "freight_id": "f-004",
                "origin": "west",
                "destination": "relay-a",
                "freight_type": "med-kit",
            },
        ],
        # Job set 5: mixed priority
        [
            {
                "freight_id": "f-001",
                "origin": "relay-a",
                "destination": "south",
                "freight_type": "med-kit",
            },
            {
                "freight_id": "f-002",
                "origin": "west",
                "destination": "relay-a",
                "freight_type": "supplies",
            },
            {
                "freight_id": "f-003",
                "origin": "east",
                "destination": "west",
                "freight_type": "equipment",
            },
            {
                "freight_id": "f-004",
                "origin": "south",
                "destination": "relay-a",
                "freight_type": "med-kit",
            },
        ],
    ]

    # Define 5 task instances with varied seeds, topologies, and disturbances
    configs = [
        TaskInstanceConfig(
            instance_id="task-001",
            seed=42,
            graph=base_graph,
            job_set=job_sets[0],
            agent_roster=["a", "b", "c", "d"],
            topology="mesh",
            hub=None,
            disturbance_schedule={},  # No disturbance - baseline
            turns=16,
            policy="route-gossip-v1",
        ),
        TaskInstanceConfig(
            instance_id="task-002",
            seed=137,
            graph=base_graph,
            job_set=job_sets[1],
            agent_roster=["a", "b", "c", "d"],
            topology="bidirectional-ring",
            hub=None,
            disturbance_schedule={
                "peer-mute": {"turn": 5, "agent": "c"},  # Mute agent c from turn 5
            },
            turns=16,
            policy="route-gossip-v1",
        ),
        TaskInstanceConfig(
            instance_id="task-003",
            seed=299,
            graph=base_graph,
            job_set=job_sets[2],
            agent_roster=["a", "b", "c", "d"],
            topology="hub-spoke",
            hub="relay-a",
            disturbance_schedule={
                "relay-loss": {"turn": 8, "agent": "b", "until": "run-end"},
            },
            turns=16,
            policy="route-gossip-v1",
        ),
        TaskInstanceConfig(
            instance_id="task-004",
            seed=413,
            graph=base_graph,
            job_set=job_sets[3],
            agent_roster=["a", "b", "c", "d"],
            topology="mesh",
            hub=None,
            disturbance_schedule={
                "stale-report": {
                    "turn": 6,
                    "message_id": "m-a001",
                    "claimed_state": "delivered",
                    "actual_state": "undelivered",
                },
            },
            turns=16,
            policy="route-gossip-v1",
        ),
        TaskInstanceConfig(
            instance_id="task-005",
            seed=571,
            graph=base_graph,
            job_set=job_sets[4],
            agent_roster=["a", "b", "c", "d"],
            topology="bidirectional-ring",
            hub=None,
            disturbance_schedule={
                "peer-mute": {"turn": 3, "agent": "a"},  # Mute agent a from turn 3
            },
            turns=16,
            policy="route-gossip-v1",
        ),
    ]

    return configs


def validate_configs(configs: list[TaskInstanceConfig]) -> list[str]:
    """
    Validate the task configs meet requirements.

    Returns:
        List of validation errors (empty if all valid).
    """
    errors = []

    # Check: exactly 5 configs
    if len(configs) != 5:
        errors.append(f"Expected exactly 5 configs, got {len(configs)}")

    # Check: no two share both seed AND job_set
    seed_job_pairs = set()
    for cfg in configs:
        job_set_key = json.dumps(cfg.job_set, sort_keys=True)
        pair = (cfg.seed, job_set_key)
        if pair in seed_job_pairs:
            errors.append(f"Duplicate seed+job_set pair found for {cfg.instance_id}")
        seed_job_pairs.add(pair)

    # Check: at least one uses peer-mute disturbance
    has_peer_mute = any("peer-mute" in cfg.disturbance_schedule for cfg in configs)
    if not has_peer_mute:
        errors.append("At least one config must use peer-mute disturbance")

    # Check: all required fields present
    for cfg in configs:
        if not cfg.instance_id:
            errors.append("Config missing instance_id")
        if not cfg.agent_roster or len(cfg.agent_roster) != 4:
            errors.append(f"Config {cfg.instance_id} must have 4 agents")
        if cfg.topology not in ("mesh", "hub-spoke", "bidirectional-ring"):
            errors.append(
                f"Config {cfg.instance_id} has invalid topology: {cfg.topology}"
            )

    return errors


def test_deterministic_replay() -> bool:
    """
    Test that configs replay deterministically from seed.

    Returns:
        True if replay is deterministic, False otherwise.
    """
    from runtime.freight_world import FreightWorld

    configs = get_task_configs()
    for cfg in configs:
        # Create world from seed twice
        world1 = FreightWorld(seed=cfg.seed)
        world2 = FreightWorld(seed=cfg.seed)

        # Check initial state is identical
        if world1.event_seq != world2.event_seq:
            return False

        # Check freight items are identical
        for fid in world1.freight_items:
            item1 = world1.freight_items[fid]
            item2 = world2.freight_items[fid]
            if (
                item1.item_id != item2.item_id
                or item1.current_location != item2.current_location
                or item1.state != item2.state
            ):
                return False

    return True


def save_configs_to_file(output_path: str) -> None:
    """Save configs to a JSON file for persistence."""
    configs = get_task_configs()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    config_data = []
    for cfg in configs:
        config_data.append(
            {
                "instance_id": cfg.instance_id,
                "seed": cfg.seed,
                "graph": cfg.graph,
                "job_set": cfg.job_set,
                "agent_roster": cfg.agent_roster,
                "topology": cfg.topology,
                "hub": cfg.hub,
                "disturbance_schedule": cfg.disturbance_schedule,
                "turns": cfg.turns,
                "policy": cfg.policy,
                "config_hash": cfg.config_hash(),
            }
        )

    with open(output, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys

    configs = get_task_configs()
    errors = validate_configs(configs)

    if errors:
        print("Config validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print(f"Config validation PASSED: {len(configs)} configs")
    for cfg in configs:
        print(
            f"  {cfg.instance_id}: seed={cfg.seed}, topology={cfg.topology}, "
            f"disturbances={list(cfg.disturbance_schedule.keys())}"
        )

    # Test deterministic replay
    if test_deterministic_replay():
        print("Deterministic replay test: PASSED")
    else:
        print("Deterministic replay test: FAILED", file=sys.stderr)
        sys.exit(1)
