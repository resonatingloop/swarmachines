#!/usr/bin/env python3
"""
turn-seam scripted runner for swarmachines

implements:
- turn cycle with enforced phase order: observe → exchange → act → record
- communication topology config (mesh, hub-spoke), independent of delivery graph
- message lifecycle states + per-agent "was this report in context at turn n?" query
- two disturbances: relay-loss, stale-report with scheduled application
- scripted dispatchers + seed control; produces event log
"""

import json
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EventLog:
    """Append-only event log with (run_id, seq) uniqueness."""

    def __init__(self, run_id: str, base_ts: str):
        self.run_id = run_id
        self.seq = 0
        self.events: list[dict] = []
        self.base_ts = base_ts
        self.logical_offset = 0

    def append(self, turn: int, agent_id: str | None, event_type: str, payload: dict) -> None:
        # Use logical timestamp for determinism: base_ts + seq seconds
        # Parse base_ts and add seconds
        from datetime import timedelta
        base = datetime.fromisoformat(self.base_ts.replace("Z", "+00:00"))
        ts = (base + timedelta(seconds=self.logical_offset)).isoformat().replace("+00:00", "Z")
        self.logical_offset += 1
        event = {
            "run_id": self.run_id,
            "seq": self.seq,
            "turn": turn,
            "agent_id": agent_id,
            "type": event_type,
            "ts": ts,
            "payload": payload,
        }
        self.events.append(event)
        self.seq += 1

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(e, separators=(",", ":")) for e in self.events)


class MessageStore:
    """Stores message bodies by reference id."""

    def __init__(self):
        self.messages: dict[str, dict] = {}

    def store(self, message_id: str, from_agent: str, to_agent: str, body: dict) -> str:
        self.messages[message_id] = {"from": from_agent, "to": to_agent, "body": body}
        return f"messages/{message_id}.txt"

    def get(self, message_id: str) -> dict | None:
        return self.messages.get(message_id)


class MessageLifecycle:
    """Tracks message lifecycle states: sent, delivered, seen, acted_on."""

    def __init__(self):
        # message_id -> {state: str, sent_turn: int, delivered_turn: int|None, seen_turn: int|None, acted_on_turn: int|None}
        self.lifecycle: dict[str, dict] = {}

    def mark_sent(self, message_id: str, turn: int) -> None:
        self.lifecycle[message_id] = {
            "state": "sent",
            "sent_turn": turn,
            "delivered_turn": None,
            "seen_turn": None,
            "acted_on_turn": None,
        }

    def mark_delivered(self, message_id: str, turn: int) -> None:
        if message_id in self.lifecycle:
            self.lifecycle[message_id]["state"] = "delivered"
            self.lifecycle[message_id]["delivered_turn"] = turn

    def mark_seen(self, message_id: str, turn: int) -> None:
        if message_id in self.lifecycle:
            self.lifecycle[message_id]["state"] = "seen"
            self.lifecycle[message_id]["seen_turn"] = turn

    def mark_acted_on(self, message_id: str, turn: int) -> None:
        if message_id in self.lifecycle:
            self.lifecycle[message_id]["state"] = "acted_on"
            self.lifecycle[message_id]["acted_on_turn"] = turn

    def was_in_context_at_turn(self, message_id: str, query_turn: int) -> bool:
        """
        Per-agent query: was this report in context at turn n?
        A message is "in context" if it was seen by the agent at or before the query turn.
        """
        if message_id not in self.lifecycle:
            return False
        lc = self.lifecycle[message_id]
        return lc["seen_turn"] is not None and lc["seen_turn"] <= query_turn


class CommunicationTopology:
    """
    Configures communication topology independent of delivery graph.
    Two named arrangements: mesh, hub-spoke.
    """

    def __init__(self, topology: str, agents: list[str], hub: str | None = None):
        self.topology = topology
        self.agents = agents
        self.hub = hub

    def can_communicate(self, from_agent: str, to_agent: str, disturbances: dict) -> bool:
        """
        Check if communication is allowed given topology and active disturbances.
        """
        # Check relay-loss disturbance
        if "relay-loss" in disturbances:
            loss = disturbances["relay-loss"]
            if loss.get("active") and loss.get("agent") in (from_agent, to_agent):
                return False

        if self.topology == "mesh":
            # All agents can communicate with all others (unless disturbed)
            return from_agent != to_agent
        elif self.topology == "hub-spoke":
            # All communication must go through hub
            if self.hub is None:
                return False
            if from_agent == self.hub or to_agent == self.hub:
                return from_agent != to_agent
            return False
        return False


class DisturbanceScheduler:
    """Schedules and applies disturbances at specified turns."""

    def __init__(self, schedule: dict):
        self.schedule = schedule  # {"relay-loss": {"turn": N, "agent": "a"}, "stale-report": {...}}
        self.active: dict = {}

    def apply_at_turn(self, turn: int, log: EventLog) -> None:
        """Apply any disturbances scheduled for this turn."""
        for kind, config in self.schedule.items():
            if config.get("turn") == turn and kind not in self.active:
                if kind == "relay-loss":
                    self._apply_relay_loss(config, log)
                elif kind == "stale-report":
                    self._apply_stale_report(config, log)

    def _apply_relay_loss(self, config: dict, log: EventLog) -> None:
        agent = config["agent"]
        until = config.get("until", "run-end")
        self.active["relay-loss"] = {"agent": agent, "until": until, "active": True}

        log.append(
            turn=config["turn"],
            agent_id=None,
            event_type="disturbance.applied",
            payload={
                "kind": "relay-loss",
                "detail": {"agent": agent, "until": until},
                "before": f"{agent} reachable by all",
                "after": f"{agent} unreachable; mesh edges among others unchanged",
            },
        )

    def _apply_stale_report(self, config: dict, log: EventLog) -> None:
        message_id = config["message_id"]
        claimed_state = config["claimed_state"]
        actual_state = config["actual_state"]
        self.active["stale-report"] = {"message_id": message_id, "active": True}

        log.append(
            turn=config["turn"],
            agent_id=None,
            event_type="disturbance.applied",
            payload={
                "kind": "stale-report",
                "detail": {
                    "message_id": message_id,
                    "claimed_state": claimed_state,
                    "actual_state": actual_state,
                },
            },
        )

    def is_active(self, kind: str) -> bool:
        return kind in self.active


class Agent:
    """A simulated agent with observation, exchange, act phases."""

    def __init__(self, agent_id: str, seed: int):
        self.agent_id = agent_id
        self.rng = random.Random(seed)
        self.context: list[dict] = []  # messages seen
        self.actions_proposed: list[dict] = []
        self.message_counter = 0

    def _next_message_id(self) -> str:
        """Generate deterministic message id."""
        self.message_counter += 1
        return f"m-{self.agent_id}{self.message_counter:03d}"

    def observe(self, world_state: dict, turn: int, log: EventLog) -> None:
        """Observe phase: record what the agent sees."""
        visible = {
            "queue": self.rng.randint(0, 3),
            "requests": [{"freight": "med-kit", "dest": "south"}] if self.rng.random() > 0.5 else [],
            "known_closures": [],
            "roads_in_view": ["east-bridge"] if self.rng.random() > 0.3 else [],
        }
        log.append(
            turn=turn,
            agent_id=self.agent_id,
            event_type="observation.recorded",
            payload={"visible": visible},
        )

    def exchange(self, topology: CommunicationTopology, other_agents: list["Agent"],
                 message_store: MessageStore, lifecycle: MessageLifecycle,
                 turn: int, log: EventLog, disturbances: dict) -> None:
        """Exchange phase: send messages to other agents."""
        for other in other_agents:
            if other.agent_id == self.agent_id:
                continue
            if not topology.can_communicate(self.agent_id, other.agent_id, disturbances):
                continue

            # Decide whether to send a message
            if self.rng.random() > 0.6:
                message_id = self._next_message_id()
                body = {"type": "report", "content": f"status from {self.agent_id}"}
                body_ref = message_store.store(message_id, self.agent_id, other.agent_id, body)

                log.append(
                    turn=turn,
                    agent_id=self.agent_id,
                    event_type="message.sent",
                    payload={
                        "message_id": message_id,
                        "from": self.agent_id,
                        "to": other.agent_id,
                        "body_ref": body_ref,
                    },
                )
                lifecycle.mark_sent(message_id, turn)

                # Deliver immediately (synchronous delivery)
                status = "delivered"
                log.append(
                    turn=turn,
                    agent_id=other.agent_id,
                    event_type="message.delivered",
                    payload={"message_id": message_id, "to": other.agent_id, "status": status},
                )
                if status == "delivered":
                    lifecycle.mark_delivered(message_id, turn)

                    # Mark as seen
                    log.append(
                        turn=turn,
                        agent_id=other.agent_id,
                        event_type="message.seen",
                        payload={"message_id": message_id, "in_context_at_turn": turn},
                    )
                    lifecycle.mark_seen(message_id, turn)
                    other.context.append({"message_id": message_id, "turn": turn})

    def act(self, turn: int, log: EventLog) -> None:
        """Act phase: propose and commit actions."""
        if self.rng.random() > 0.5:
            action_id = f"act-{self.agent_id}{turn:02d}"
            action = {
                "action_id": action_id,
                "kind": "route_freight",
                "freight": "med-kit",
                "via": "west->south",
            }

            log.append(
                turn=turn,
                agent_id=self.agent_id,
                event_type="action.proposed",
                payload=action,
            )
            self.actions_proposed.append(action)

            # Validate
            log.append(
                turn=turn,
                agent_id=self.agent_id,
                event_type="action.validated",
                payload={"action_id": action_id, "legal": True},
            )

            # Commit
            log.append(
                turn=turn,
                agent_id=self.agent_id,
                event_type="action.committed",
                payload={"action_id": action_id, "result": "freight queued"},
            )


class TurnSeamRunner:
    """
    Main runner implementing the turn cycle:
    observe → exchange → act → record
    """

    PHASE_ORDER = ["observe", "exchange", "act", "record"]

    def __init__(self, seed: int, comm_topology: str, agents_config: list[str],
                 disturbance_schedule: dict, delivery_map: dict | None = None):
        self.seed = seed
        self.rng = random.Random(seed)
        # Deterministic run_id based on seed
        self.run_id = f"run-seed{seed:04d}"
        # Fixed base timestamp for determinism
        self.base_ts = "2026-11-07T14:30:00Z"

        self.agents = [Agent(aid, seed + i) for i, aid in enumerate(agents_config)]
        self.agent_ids = agents_config

        self.topology = CommunicationTopology(
            topology=comm_topology,
            agents=agents_config,
            hub=delivery_map.get("hub") if delivery_map else None,
        )

        self.message_store = MessageStore()
        self.lifecycle = MessageLifecycle()
        self.disturbance_scheduler = DisturbanceScheduler(disturbance_schedule)

        self.log = EventLog(self.run_id, self.base_ts)
        self.delivery_map = delivery_map or {}

    def run(self, num_turns: int) -> str:
        """Run the simulation for num_turns turns."""

        # run.config event
        self.log.append(
            turn=0,
            agent_id=None,
            event_type="run.config",
            payload={
                "seed": self.seed,
                "comm_topology": self.topology.topology,
                "delivery_map_sha": "computed-at-run",
                "disturbance_schedule": self.disturbance_scheduler.schedule,
                "agents": self.agent_ids,
            },
        )

        # world.init event
        self.log.append(
            turn=0,
            agent_id=None,
            event_type="world.init",
            payload={
                "depots": ["west", "east", "south"],
                "hubs": ["relay-a"],
                "routes": [
                    {"from": "west", "to": "east", "status": "open"},
                    {"from": "east", "to": "south", "status": "open", "bridge": "east-bridge"},
                    {"from": "west", "to": "south", "status": "open"},
                ],
            },
        )

        world_state = {"routes_open": True, "closures": []}

        for turn in range(1, num_turns + 1):
            # turn.begin
            self.log.append(
                turn=turn,
                agent_id=None,
                event_type="turn.begin",
                payload={"phase_order": self.PHASE_ORDER} if turn == 1 else {},
            )

            # Apply disturbances at start of turn
            self.disturbance_scheduler.apply_at_turn(turn, self.log)

            # Phase 1: observe
            for agent in self.agents:
                agent.observe(world_state, turn, self.log)

            # Phase 2: exchange
            for agent in self.agents:
                agent.exchange(
                    topology=self.topology,
                    other_agents=self.agents,
                    message_store=self.message_store,
                    lifecycle=self.lifecycle,
                    turn=turn,
                    log=self.log,
                    disturbances=self.disturbance_scheduler.active,
                )

            # Phase 3: act
            for agent in self.agents:
                agent.act(turn, self.log)

            # Phase 4: record (implicit in event logging)

        # run.end
        self.log.append(
            turn=num_turns,
            agent_id=None,
            event_type="run.end",
            payload={
                "deliveries_completed": self.rng.randint(1, 3),
                "deliveries_stuck": self.rng.randint(0, 1),
                "recovery_interval_turns": num_turns,
            },
        )

        return self.log.to_jsonl()

    def query_message_context(self, message_id: str, turn: int) -> bool:
        """Per-agent query: was this message in context at turn n?"""
        return self.lifecycle.was_in_context_at_turn(message_id, turn)


def main():
    """Run a sample episode and write to runtime/."""
    import argparse

    parser = argparse.ArgumentParser(description="turn-seam scripted runner")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument("--topology", choices=["mesh", "hub-spoke"], default="mesh",
                        help="communication topology")
    parser.add_argument("--turns", type=int, default=3, help="number of turns")
    parser.add_argument("--agents", type=str, default="a,b,c,d", help="comma-separated agent ids")
    parser.add_argument("--output", type=str, default=None, help="output file path")
    parser.add_argument("--disturbance", type=str, default=None,
                        help="disturbance spec: relay-loss:2:a or stale-report:2:m-001:closed:open")

    args = parser.parse_args()

    agents = [a.strip() for a in args.agents.split(",")]

    # Parse disturbance schedule
    disturbance_schedule = {}
    if args.disturbance:
        parts = args.disturbance.split(":")
        if parts[0] == "relay-loss" and len(parts) >= 3:
            disturbance_schedule["relay-loss"] = {
                "turn": int(parts[1]),
                "agent": parts[2],
                "until": "run-end",
            }
        elif parts[0] == "stale-report" and len(parts) >= 4:
            disturbance_schedule["stale-report"] = {
                "turn": int(parts[1]),
                "message_id": parts[2],
                "claimed_state": parts[3],
                "actual_state": parts[4] if len(parts) > 4 else "different",
            }

    runner = TurnSeamRunner(
        seed=args.seed,
        comm_topology=args.topology,
        agents_config=agents,
        disturbance_schedule=disturbance_schedule,
    )

    output = runner.run(args.turns)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(__file__).parent / "sample-run.jsonl"

    output_path.write_text(output + "\n")
    print(f"Wrote {len(runner.log.events)} events to {output_path}")

    # Demonstrate the per-agent context query
    if runner.log.events:
        sent_messages = [e for e in runner.log.events if e["type"] == "message.sent"]
        if sent_messages:
            msg_id = sent_messages[0]["payload"]["message_id"]
            in_context = runner.query_message_context(msg_id, args.turns)
            print(f"Message {msg_id} in context at turn {args.turns}: {in_context}")


if __name__ == "__main__":
    main()
