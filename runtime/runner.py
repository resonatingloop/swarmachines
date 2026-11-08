#!/usr/bin/env python3
"""
turn-seam scripted runner for swarmachines

implements:
- turn cycle with enforced phase order: observe → exchange → act → record
- communication topology config (mesh, hub-spoke), independent of delivery graph
- message lifecycle states + per-agent "was this report in context at turn n?" query
- two disturbances: relay-loss, stale-report with scheduled application
- scripted dispatchers + seed control; produces event log
- freight-in-the-fog world integration (optional, via --world freight)
"""

import hashlib
import json
import random
import re
import sys
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar

from freight_world import FreightWorld
from job_evidence import roster
from route_gossip import MAX_REPORTS, POLICY, admit_report, make_report, select

try:  # package mode: runtime/ is importable as a package
    from .tracer import RunStatus, TraceConfig, Tracer, create_tracer  # type: ignore
except ImportError:  # script mode: python3 runtime/runner.py
    try:
        from tracer import (  # type: ignore
            RunStatus,
            TraceConfig,
            Tracer,
            create_tracer,
        )
    except ImportError:  # tracer module missing: tracing unavailable
        RunStatus = TraceConfig = Tracer = create_tracer = None  # type: ignore


class EventLog:
    """Append-only event log with (run_id, seq) uniqueness."""

    def __init__(self, run_id: str, base_ts: str):
        self.run_id = run_id
        self.seq = 0
        self.events: list[dict] = []
        self.base_ts = base_ts
        # Separate counters for comm vs non-comm to ensure topology-independence
        self.comm_seq = 0
        self.non_comm_seq = 0

    def append(
        self, turn: int, agent_id: str | None, event_type: str, payload: dict
    ) -> None:
        # Use logical timestamp for determinism: base_ts + seq seconds
        # Non-communication events use non_comm_seq for topology-independence
        comm_types = {
            "message.sent",
            "message.delivered",
            "message.seen",
            "message.acted_on",
        }
        is_comm = event_type in comm_types

        if is_comm:
            seq = self.comm_seq
            self.comm_seq += 1
        else:
            seq = self.non_comm_seq
            self.non_comm_seq += 1

        base = datetime.fromisoformat(self.base_ts)
        ts = (base + timedelta(seconds=seq)).isoformat().replace("+00:00", "Z")

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

    def can_communicate(
        self, from_agent: str, to_agent: str, disturbances: dict
    ) -> tuple[bool, str]:
        """
        Check if communication is allowed given topology and active disturbances.
        Returns (allowed, reason) tuple.
        """
        # Check peer-mute disturbance: muted agent cannot send or receive messages
        # but can still perform local actions (observe, act)
        if "peer-mute" in disturbances:
            mute = disturbances["peer-mute"]
            if mute.get("active") and mute.get("agent") in (from_agent, to_agent):
                return False, "agent communication muted"

        # Check relay-loss disturbance
        if "relay-loss" in disturbances:
            loss = disturbances["relay-loss"]
            if loss.get("active") and loss.get("agent") in (from_agent, to_agent):
                return False, "agent unreachable"

        if self.topology == "mesh":
            # All agents can communicate with all others (unless disturbed)
            if from_agent != to_agent:
                return True, ""
            return False, "self-communication not allowed"
        elif self.topology == "hub-spoke":
            # All communication must go through hub
            if self.hub is None:
                return False, "hub not configured"
            if (
                from_agent == self.hub or to_agent == self.hub
            ) and from_agent != to_agent:
                return True, ""
            return False, "hub-spoke requires hub involvement"
        elif self.topology == "bidirectional-ring":
            # Each agent can only communicate with immediate neighbors (left/right, wraparound)
            # For [a,b,c,d]: a↔b, b↔c, c↔d, d↔a
            if from_agent == to_agent:
                return False, "self-communication not allowed"
            try:
                from_idx = self.agents.index(from_agent)
                to_idx = self.agents.index(to_agent)
            except ValueError:
                return False, "unknown agent"

            n = len(self.agents)
            left_neighbor = (from_idx - 1) % n
            right_neighbor = (from_idx + 1) % n

            if to_idx == left_neighbor or to_idx == right_neighbor:
                return True, ""
            return False, "bidirectional-ring: agents not neighbors"

        return False, "unknown topology"


class DisturbanceScheduler:
    """Schedules and applies disturbances at specified turns."""

    def __init__(self, schedule: dict):
        self.schedule = (
            schedule  # {"relay-loss": {"turn": N, "agent": "a"}, "stale-report": {...}}
        )
        self.active: dict = {}

    def apply_at_turn(
        self,
        turn: int,
        log: EventLog,
        topology: str,
        hub: str | None = None,
        lifecycle: MessageLifecycle | None = None,
    ) -> None:
        """Apply any disturbances scheduled for this turn."""
        for kind, config in self.schedule.items():
            if config.get("turn") == turn and kind not in self.active:
                if kind == "relay-loss":
                    self._apply_relay_loss(config, log, topology, hub)
                elif kind == "stale-report":
                    self._apply_stale_report(config, log, lifecycle)
                elif kind == "peer-mute":
                    self._apply_peer_mute(config, log)

    def _apply_relay_loss(
        self, config: dict, log: EventLog, topology: str, hub: str | None = None
    ) -> None:
        agent = config["agent"]
        until = config.get("until", "run-end")
        self.active["relay-loss"] = {"agent": agent, "until": until, "active": True}

        # Describe unaffected edges based on actual topology
        if topology == "mesh":
            edge_desc = "mesh edges among others unchanged"
        elif topology == "hub-spoke":
            hub_ref = f"via {hub}" if hub else "through hub"
            edge_desc = f"hub-spoke edges {hub_ref} among others unchanged"
        elif topology == "bidirectional-ring":
            edge_desc = "ring edges among others unchanged"
        else:
            edge_desc = f"{topology} edges among others unchanged"

        log.append(
            turn=config["turn"],
            agent_id=None,
            event_type="disturbance.applied",
            payload={
                "kind": "relay-loss",
                "detail": {"agent": agent, "until": until},
                "before": f"{agent} reachable by all",
                "after": f"{agent} unreachable; {edge_desc}",
            },
        )

    def _apply_stale_report(
        self, config: dict, log: EventLog, lifecycle: MessageLifecycle | None = None
    ) -> None:
        """Apply stale-report disturbance: claim a message state different from reality.

        Validation: the message_id must have been actually SENT (exist in lifecycle).
        Raises ValueError if the message was never sent (prevents injection of fake message ids).
        """
        message_id = config["message_id"]
        claimed_state = config["claimed_state"]
        actual_state = config["actual_state"]

        # Validate: message must have been sent (exist in lifecycle)
        if lifecycle is not None and message_id not in lifecycle.lifecycle:
            raise ValueError(
                f"stale-report message_id {message_id} was never sent (not in message lifecycle)"
            )

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
                "before": f"message {message_id} claimed {claimed_state}",
                "after": f"message {message_id} actually {actual_state}",
            },
        )

    def _apply_peer_mute(self, config: dict, log: EventLog) -> None:
        """Apply peer-mute disturbance: mute a fixed agent's communication while local actions continue."""
        agent = config["agent"]
        self.active["peer-mute"] = {"agent": agent, "active": True}

        log.append(
            turn=config["turn"],
            agent_id=None,
            event_type="disturbance.applied",
            payload={
                "kind": "peer-mute",
                "detail": {"agent": agent},
                "before": f"{agent} can send and receive messages",
                "after": f"{agent} communication muted; local actions (observe, act) continue",
            },
        )

    def is_active(self, kind: str) -> bool:
        return kind in self.active


class Agent:
    """A simulated agent with observation, exchange, act phases."""

    def __init__(
        self, agent_id: str, base_seed: int, agent_index: int, policy: str = "legacy"
    ):
        self.agent_id = agent_id
        self.policy = policy
        self.observation = None
        self.observation_seq = None
        self.inbox = []
        # Separate RNG streams for topology-independent non-comm events
        # Each stream is seeded uniquely per agent to ensure determinism
        # exchange_send_rng and exchange_acted_rng are split to prevent entanglement:
        # send decisions (topology-dependent) don't affect acted_on decisions (non-comm)
        self.observe_rng = random.Random(base_seed + agent_index * 10)
        self.act_rng = random.Random(base_seed + agent_index * 10 + 1)
        self.exchange_send_rng = random.Random(base_seed + agent_index * 10 + 2)
        self.exchange_acted_rng = random.Random(base_seed + agent_index * 10 + 3)
        self.context: list[dict] = []  # messages seen
        self.actions_proposed: list[dict] = []
        self.message_counter = 0

    def _next_message_id(self) -> str:
        """Generate deterministic message id."""
        self.message_counter += 1
        return f"m-{self.agent_id}{self.message_counter:03d}"

    def observe(
        self,
        world_state: dict,
        turn: int,
        log: EventLog,
        freight_world: FreightWorld | None = None,
    ) -> None:
        """Observe phase: record what the agent sees."""
        if freight_world is not None:
            # Use freight world for partial observations
            visible = freight_world.observe(self.agent_id, turn, self.observe_rng)
        else:
            # Fallback to scripted observations
            visible = {
                "queue": self.observe_rng.randint(0, 3),
                "requests": [{"freight": "med-kit", "dest": "south"}]
                if self.observe_rng.random() > 0.5
                else [],
                "known_closures": [],
                "roads_in_view": ["east-bridge"]
                if self.observe_rng.random() > 0.3
                else [],
            }
        if self.policy == POLICY:
            self.observation = deepcopy(visible)
            self.observation_seq = log.seq
            self.inbox = []  # only reports delivered after this turn's observation
        log.append(
            turn=turn,
            agent_id=self.agent_id,
            event_type="observation.recorded",
            payload={"visible": visible},
        )

    def exchange(
        self,
        topology: CommunicationTopology,
        other_agents: list["Agent"],
        message_store: MessageStore,
        lifecycle: MessageLifecycle,
        turn: int,
        log: EventLog,
        disturbances: dict,
    ) -> None:
        """Exchange phase: send messages to other agents."""
        for other in other_agents:
            if other.agent_id == self.agent_id:
                continue

            allowed, reason = topology.can_communicate(
                self.agent_id, other.agent_id, disturbances
            )

            # Decide whether to send a message (using exchange_send_rng for topology-independence)
            if self.exchange_send_rng.random() > 0.6:
                message_id = self._next_message_id()
                body = {"type": "report", "content": f"status from {self.agent_id}"}
                if self.policy == POLICY:
                    body = make_report(self.observation, self.agent_id)
                body_ref = message_store.store(
                    message_id, self.agent_id, other.agent_id, body
                )

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

                # Attempt delivery
                if allowed:
                    status = "delivered"
                    log.append(
                        turn=turn,
                        agent_id=other.agent_id,
                        event_type="message.delivered",
                        payload={
                            "message_id": message_id,
                            "to": other.agent_id,
                            "status": status,
                        },
                    )
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

                    # Emit message.acted_on immediately after seen (deterministic based on exchange_acted_rng)
                    # Uses separate stream from send decision to prevent RNG entanglement
                    if self.policy == POLICY:
                        other.receive_report(body, self.agent_id, message_id, turn, log)
                    elif self.exchange_acted_rng.random() > 0.5:
                        lifecycle.mark_acted_on(message_id, turn)
                        log.append(
                            turn=turn,
                            agent_id=other.agent_id,
                            event_type="message.acted_on",
                            payload={
                                "message_id": message_id,
                                "relation": "informed",
                            },
                        )
                else:
                    # Emit undelivered with reason (relay-loss or topology block)
                    log.append(
                        turn=turn,
                        agent_id=other.agent_id,
                        event_type="message.delivered",
                        payload={
                            "message_id": message_id,
                            "to": other.agent_id,
                            "status": "undelivered",
                            "reason": reason,
                        },
                    )

    def receive_report(self, body, sender, message_id, turn, log):
        """Admit a report only when called by successful message delivery.

        Args:
            body: Bounded report body from the message store.
            sender: Transport-owned sender identity.
            message_id: Delivered message identity.
            turn: Current logical turn.
            log: Episode event sink.
        """
        report, reason = admit_report(
            body, sender=sender, message_id=message_id, turn=turn
        )
        if report is not None and (
            self.observation is None or self.observation["turn"] != turn
        ):
            report, reason = None, "no_current_observation"
        if report is not None and (
            len(self.inbox) >= MAX_REPORTS
            or any(r.message_id == message_id for r in self.inbox)
        ):
            report, reason = None, "inbox_limit_or_duplicate"
        if report is not None:
            self.inbox.append(report)
        log.append(
            turn,
            self.agent_id,
            "policy.report",
            {
                "message_id": message_id,
                "sender": sender,
                "admitted": report is not None,
                "reason": reason,
                "observed_turn": report.turn if report else None,
                "routes": dict(report.routes) if report else {},
            },
        )

    def _act_gossip(self, turn, log, freight_world):
        """Select from local evidence; pass only the resulting action to the world."""
        if self.observation is None or self.observation["turn"] != turn:
            raise ValueError("missing current policy observation")
        opportunity = self.act_rng.random() > 0.5
        decision = select(self.observation, tuple(self.inbox))
        if not opportunity:
            decision.update(
                path=[],
                next_hop=None,
                local_only_next_hop=None,
                choice_changed=False,
                consumed_message_ids=[],
                reason="no_action_opportunity",
            )
        action_id = f"act-{self.agent_id}{turn:02d}" if decision["next_hop"] else None
        decision.update(
            decision_id=f"decision-{self.agent_id}-{turn}",
            observation_seq=self.observation_seq,
            action_id=action_id,
            opportunity=opportunity,
        )
        log.append(turn, self.agent_id, "policy.decision", decision)
        if action_id is None:
            return
        action = {
            "action_id": action_id,
            "kind": "route_freight",
            "freight_id": decision["freight_id"],
            "via": f"{self.observation['current_location']}->{decision['next_hop']}",
        }
        self._commit_proposal(action, turn, log, freight_world)

    def act(
        self,
        turn: int,
        log: EventLog,
        message_lifecycle: MessageLifecycle | None = None,
        freight_world: FreightWorld | None = None,
    ) -> None:
        """Act phase: propose and commit actions."""
        if self.policy == POLICY:
            self._act_gossip(turn, log, freight_world)
            return
        if self.act_rng.random() > 0.5:
            action_id = f"act-{self.agent_id}{turn:02d}"

            # Build action using freight world if available
            if freight_world is not None:
                # Get agent's current location from freight_world's agent_depots mapping
                assigned_depots = freight_world.agent_depots.get(
                    self.agent_id, ["west"]
                )
                current_location = assigned_depots[0]

                # Get freight items at this agent's location
                freight_items = freight_world.get_freight_at_location(current_location)
                if not freight_items:
                    # No freight to route - emit no-op action
                    action = {
                        "action_id": action_id,
                        "kind": "route_freight",
                        "freight_id": "none",
                    }
                else:
                    # Get adjacent locations for routing
                    adjacent = freight_world.get_adjacent_locations(current_location)
                    if not adjacent:
                        return  # No routes from this location

                    # Pick first freight item and route it
                    item = freight_items[0]
                    via_path = f"{current_location}->{adjacent[0]}"
                    action = {
                        "action_id": action_id,
                        "kind": "route_freight",
                        "freight_id": item.item_id,
                        "freight_type": item.freight_type,
                        "via": via_path,
                    }
            else:
                # Fallback to generic action
                action = {
                    "action_id": action_id,
                    "kind": "route_freight",
                    "freight": "med-kit",
                    "via": "west->south",
                }

            self._commit_proposal(action, turn, log, freight_world)

    def _commit_proposal(self, action, turn, log, freight_world):
        """Validate and apply a proposal through the existing world boundary."""
        action_id = action["action_id"]
        log.append(
            turn=turn,
            agent_id=self.agent_id,
            event_type="action.proposed",
            payload=action,
        )
        self.actions_proposed.append(action)

        # Validate against freight world if available
        if freight_world is not None:
            legal, reason = freight_world.validate_action(action)
        else:
            # Fallback to stochastic validation
            legal = self.act_rng.random() > 0.2
            reason = "route validation failed" if not legal else ""

        log.append(
            turn=turn,
            agent_id=self.agent_id,
            event_type="action.validated",
            payload={"action_id": action_id, "legal": legal},
        )

        if legal:
            # Commit action and update freight world
            if freight_world is not None:
                prior_jobs = roster(freight_world) if self.policy == POLICY else []
                success, commit_reason, event_payload = freight_world.apply_action(
                    action, self.agent_id
                )
                if success:
                    # Legal action committed - may be a no-op (event_payload=None) or state change
                    log.append(
                        turn=turn,
                        agent_id=self.agent_id,
                        event_type="action.committed",
                        payload={
                            "action_id": action_id,
                            **(event_payload or {"result": "no-op"}),
                        },
                    )
                    if self.policy == POLICY:
                        previous = {row["job_id"]: row["state"] for row in prior_jobs}
                        for row in roster(freight_world):
                            if (
                                row["freight_id"] == action["freight_id"]
                                and row["state"] == "delivered"
                                and previous[row["job_id"]] != "delivered"
                            ):
                                log.append(
                                    turn,
                                    self.agent_id,
                                    "job.completed",
                                    {
                                        "job_id": row["job_id"],
                                        "freight_id": row["freight_id"],
                                        "action_id": action_id,
                                    },
                                )
                    # Emit world.changed event only when state actually changed
                    if event_payload:
                        log.append(
                            turn=turn,
                            agent_id=self.agent_id,
                            event_type="world.changed",
                            payload={
                                "what": f"freight {action.get('freight_id', 'unknown')} moved",
                                "effect": event_payload.get("result", "freight routed"),
                                "visibility": "all agents",
                            },
                        )
                else:
                    # Apply-stage failure - action rejected with real reason
                    log.append(
                        turn=turn,
                        agent_id=self.agent_id,
                        event_type="action.rejected",
                        payload={
                            "action_id": action_id,
                            "reason": commit_reason or "apply failed",
                        },
                    )
            else:
                log.append(
                    turn=turn,
                    agent_id=self.agent_id,
                    event_type="action.committed",
                    payload={"action_id": action_id, "result": "freight queued"},
                )
        else:
            # Reject
            log.append(
                turn=turn,
                agent_id=self.agent_id,
                event_type="action.rejected",
                payload={"action_id": action_id, "reason": reason},
            )


class TurnSeamRunner:
    """
    Main runner implementing the turn cycle:
    observe → exchange → act → record
    """

    PHASE_ORDER: ClassVar[list[str]] = ["observe", "exchange", "act", "record"]

    def __init__(
        self,
        seed: int,
        comm_topology: str,
        agents_config: list[str],
        disturbance_schedule: dict,
        delivery_map: dict | None = None,
        use_freight_world: bool = False,
        policy: str = "legacy",
        tracer: object | None = None,
    ):
        if policy not in ("legacy", POLICY) or (
            policy == POLICY and not use_freight_world
        ):
            raise ValueError("route-gossip-v1 requires freight world")
        if policy == POLICY and (
            not 1 <= len(agents_config) <= MAX_REPORTS
            or len(set(agents_config)) != len(agents_config)
            or any(
                not isinstance(aid, str) or not re.fullmatch(r"[a-zA-Z0-9-]{1,40}", aid)
                for aid in agents_config
            )
        ):
            raise ValueError("route gossip requires unique bounded agent identities")
        self.policy = policy
        self.seed = seed
        self.rng = random.Random(seed)
        # Deterministic run_id based on seed
        self.run_id = f"run-seed{seed:04d}"
        # Fixed base timestamp for determinism
        self.base_ts = "2026-11-07T14:30:00Z"

        self.agents = [
            Agent(aid, seed, i, policy) for i, aid in enumerate(agents_config)
        ]
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

        # Initialize freight world if requested
        self.use_freight_world = use_freight_world
        self.freight_world: FreightWorld | None = None
        # Optional execution tracer (spec: langfuse-compatible, offline no-op)
        self.tracer: Any = tracer
        if use_freight_world:
            self.freight_world = FreightWorld(seed=seed)

    def _run_phase(
        self,
        turn: int,
        phase: str,
        trace_id: str | None,
        world_state: dict | None = None,
    ) -> None:
        """Run a single phase (observe/exchange/act) for all agents with optional tracing.

        Args:
            turn: Current turn number
            phase: Phase name (\"observe\", \"exchange\", or \"act\")
            trace_id: Parent trace id for span nesting (None if tracing disabled)
            world_state: Optional world state dict (used only for observe phase)
        """
        for agent in self.agents:
            if self.tracer is not None:
                with self.tracer.turn_span(
                    turn, phase, agent.agent_id, parent_id=trace_id
                ):
                    self._invoke_phase(agent, phase, turn, world_state)
            else:
                self._invoke_phase(agent, phase, turn, world_state)

    def _invoke_phase(
        self,
        agent: Agent,
        phase: str,
        turn: int,
        world_state: dict | None = None,
    ) -> None:
        """Invoke a phase method on an agent with the correct arguments.

        Args:
            agent: Agent instance
            phase: Phase name ("observe", "exchange", or "act")
            turn: Current turn number
            world_state: Optional world state dict (used only for observe phase)
        """
        if phase == "observe":
            agent.observe(
                world_state if world_state is not None else {},
                turn,
                self.log,
                self.freight_world,
            )
        elif phase == "exchange":
            agent.exchange(
                topology=self.topology,
                other_agents=self.agents,
                message_store=self.message_store,
                lifecycle=self.lifecycle,
                turn=turn,
                log=self.log,
                disturbances=self.disturbance_scheduler.active,
            )
        elif phase == "act":
            agent.act(turn, self.log, self.lifecycle, self.freight_world)

    def run(self, num_turns: int) -> str:
        """Run the simulation for num_turns turns."""

        # Compute delivery_config_sha (hash of delivery configuration, not delivery graph)
        # Named delivery_config_sha to clarify it hashes the hub/topology config,
        # not a graph of message deliveries (which is tracked separately in MessageLifecycle)
        delivery_map_json = json.dumps(self.delivery_map, sort_keys=True)
        delivery_config_sha = hashlib.sha256(delivery_map_json.encode()).hexdigest()[
            :16
        ]

        # run.config event
        self.log.append(
            turn=0,
            agent_id=None,
            event_type="run.config",
            payload={
                "seed": self.seed,
                "comm_topology": self.topology.topology,
                "delivery_config_sha": delivery_config_sha,
                "disturbance_schedule": self.disturbance_scheduler.schedule,
                "agents": self.agent_ids,
                **(
                    {
                        "policy": POLICY,
                        "world": "freight",
                        "job_evidence_version": 1,
                        "horizon_turns": num_turns,
                    }
                    if self.policy == POLICY
                    else {}
                ),
            },
        )

        if self.policy == POLICY:
            self.log.append(
                0,
                None,
                "jobs.initialized",
                {"jobs": roster(self.freight_world, initial=True)},
            )

        # world.init event - reflect the real route set from freight_world
        if self.freight_world is not None:
            routes_payload = [
                {"from": r.from_loc, "to": r.to_loc, "status": r.status}
                | ({"bridge": r.bridge} if r.bridge else {})
                for r in self.freight_world.routes.values()
            ]
            depots = self.freight_world.depots
            hubs = self.freight_world.hubs
        else:
            routes_payload = [
                {"from": "west", "to": "east", "status": "open"},
                {
                    "from": "east",
                    "to": "south",
                    "status": "open",
                    "bridge": "east-bridge",
                },
                {"from": "west", "to": "south", "status": "open"},
            ]
            depots = ["west", "east", "south"]
            hubs = ["relay-a"]

        self.log.append(
            turn=0,
            agent_id=None,
            event_type="world.init",
            payload={
                "depots": depots,
                "hubs": hubs,
                "routes": routes_payload,
            },
        )

        # Emit world.changed for initial state
        self.log.append(
            turn=0,
            agent_id=None,
            event_type="world.changed",
            payload={
                "what": "initial world state",
                "effect": "all routes open",
                "visibility": "all agents",
            },
        )

        world_state = {"routes_open": True, "closures": []}

        # Start execution trace (no-op when tracing unconfigured)
        trace_id: str | None = None
        if self.tracer is not None:
            self.tracer.start_trace(
                run_id=self.run_id,
                condition=self.delivery_map.get("condition"),
                seed=self.seed,
            )
            trace_id = self.tracer.current_trace_id

        run_error: BaseException | None = None
        try:
            for turn in range(1, num_turns + 1):
                # turn.begin
                self.log.append(
                    turn=turn,
                    agent_id=None,
                    event_type="turn.begin",
                    payload={"phase_order": self.PHASE_ORDER} if turn == 1 else {},
                )

                # Apply disturbances at start of turn
                self.disturbance_scheduler.apply_at_turn(
                    turn,
                    self.log,
                    self.topology.topology,
                    self.topology.hub,
                    self.lifecycle,
                )

                # Phase 1: observe - ALL agents observe before any exchange
                self._run_phase(turn, "observe", trace_id, world_state)

                # Phase 2: exchange - ALL agents exchange before any act
                self._run_phase(turn, "exchange", trace_id)

                # Phase 3: act - ALL agents act before moving to next turn
                self._run_phase(turn, "act", trace_id)

                # Phase 4: record (implicit in event logging)
        except BaseException as exc:
            run_error = exc
            raise
        finally:
            if self.tracer is not None:
                status = RunStatus.FAILED if run_error else RunStatus.COMPLETED
                self.tracer.end_trace(
                    status=status,
                    reason=repr(run_error) if run_error else None,
                )

        # run.end - omit fabricated delivery stats entirely (absent is better than lying)
        self.log.append(
            turn=num_turns,
            agent_id=None,
            event_type="run.end",
            payload={
                "recovery_interval_turns": num_turns,
                **(
                    {
                        "jobs": roster(self.freight_world),
                        "termination": "completed",
                        "horizon_turns": num_turns,
                    }
                    if self.policy == POLICY
                    else {}
                ),
            },
        )

        # End tracing if configured
        return self.log.to_jsonl()

    def query_message_context(self, message_id: str, turn: int) -> bool:
        """Per-agent query: was this message in context at turn n?"""
        return self.lifecycle.was_in_context_at_turn(message_id, turn)


def load_events(
    path: str, line_char_limit: int = 10000, total_char_limit: int = 10000000
) -> list[dict]:
    """
    Load events from a JSONL file with per-line size cap (10k default) and cumulative total cap (10MB default).

    Security: error messages use categorical types only — raw hostile input (model/attacker-
    controlled JSON) is never echoed into logs or the episode. This prevents log injection
    and ensures the episode remains a trustworthy audit trail.

    Each line is validated against the events schema before being trusted.
    Returns a list of valid events; invalid lines are logged but not returned.
    """
    import jsonschema

    schema_path = Path(__file__).parent / "schema" / "events.schema.json"
    with open(schema_path) as f:
        schema = json.load(f)

    events = []
    errors = []
    total_chars = 0

    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            # Per-line size cap (10k default)
            if len(line) > line_char_limit:
                errors.append(f"Line {line_num}: line_exceeds_size_limit")
                continue

            # Cumulative total cap (10MB default)
            total_chars += len(line)
            if total_chars > total_char_limit:
                errors.append(f"Line {line_num}: total_size_exceeded")
                break

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                # Non-echoing: do not include raw hostile JSON in error message
                errors.append(f"Line {line_num}: invalid_json")
                continue

            # Validate against schema
            try:
                jsonschema.validate(event, schema)
                events.append(event)
            except jsonschema.ValidationError:
                # Non-echoing: do not include raw hostile data from event in error message
                errors.append(f"Line {line_num}: schema_validation_failed")

    if errors:
        print(f"load_events: {len(errors)} errors loading {path}")
        for err in errors[:5]:
            print(f"  {err}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")

    return events


def main():
    """Run a sample episode and write to runtime/."""
    import argparse

    parser = argparse.ArgumentParser(description="turn-seam scripted runner")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument(
        "--topology",
        choices=["mesh", "hub-spoke", "bidirectional-ring"],
        default="mesh",
        help="communication topology",
    )
    parser.add_argument(
        "--turns", type=int, default=3, help="number of turns (max 100)"
    )
    parser.add_argument(
        "--agents",
        type=str,
        default="a,b,c,d",
        help="comma-separated agent ids (alphanumeric + hyphen only)",
    )
    parser.add_argument("--output", type=str, default=None, help="output file path")
    parser.add_argument(
        "--disturbance",
        type=str,
        default=None,
        help="disturbance spec: relay-loss:2:a or stale-report:2:m-001:closed:open",
    )
    parser.add_argument(
        "--hub", type=str, default=None, help="hub agent id for hub-spoke topology"
    )
    parser.add_argument(
        "--delivery-map", type=str, default=None, help="path to delivery map JSON file"
    )
    parser.add_argument(
        "--world",
        choices=["scripted", "freight"],
        default="scripted",
        help="world mode: scripted (default, backward-compatible) or freight (freight-in-the-fog world)",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        default=False,
        help="enable execution tracing (spans exported when LANGFUSE_* env configured; no-op otherwise)",
    )

    parser.add_argument(
        "--policy",
        choices=["legacy", POLICY],
        default="legacy",
        help="explicit scripted action policy; route gossip requires freight",
    )
    args = parser.parse_args()
    if args.policy == POLICY and args.world != "freight":
        parser.error("route-gossip-v1 requires --world freight")

    # Validate agent ids (alphanumeric + hyphen only)
    agents = [a.strip() for a in args.agents.split(",")]
    agent_pattern = re.compile(r"^[a-zA-Z0-9-]+\Z")
    for agent in agents:
        if not agent_pattern.match(agent):
            print(f"Error: invalid agent id '{agent}' (must be alphanumeric + hyphen)")
            sys.exit(1)

    # Cap turns
    if args.turns > 100:
        print(f"Error: --turns capped at 100, got {args.turns}")
        sys.exit(1)
    if args.turns < 1:
        print(f"Error: --turns must be >= 1, got {args.turns}")
        sys.exit(1)

    # Build delivery map
    delivery_map = {}
    if args.hub:
        delivery_map["hub"] = args.hub
    if args.delivery_map:
        with open(args.delivery_map) as f:
            delivery_map.update(json.load(f))

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
        elif parts[0] == "peer-mute" and len(parts) >= 3:
            disturbance_schedule["peer-mute"] = {
                "turn": int(parts[1]),
                "agent": parts[2],
            }

    tracer = None
    if create_tracer is not None and getattr(args, "trace", False):
        import os

        os.environ["TRACE_ENABLED"] = "true"
        tracer, _trace_exporter = create_tracer(
            run_id=f"run-seed{args.seed:04d}",
            condition=(delivery_map or {}).get("condition"),
            seed=args.seed,
        )

    runner = TurnSeamRunner(
        seed=args.seed,
        comm_topology=args.topology,
        agents_config=agents,
        disturbance_schedule=disturbance_schedule,
        delivery_map=delivery_map if delivery_map else None,
        use_freight_world=args.world == "freight",
        policy=args.policy,
        tracer=tracer,
    )

    output = runner.run(args.turns)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(__file__).parent / "sample-run.jsonl"

    output_path.write_text(output + "\n")
    print(f"Wrote {len(runner.log.events)} events to {output_path}")

    # Flush trace data if tracing was enabled
    if tracer is not None:
        tracer.flush()

    # Demonstrate the per-agent context query
    if runner.log.events:
        sent_messages = [e for e in runner.log.events if e["type"] == "message.sent"]
        if sent_messages:
            msg_id = sent_messages[0]["payload"]["message_id"]
            in_context = runner.query_message_context(msg_id, args.turns)
            print(f"Message {msg_id} in context at turn {args.turns}: {in_context}")


if __name__ == "__main__":
    import sys

    main()
