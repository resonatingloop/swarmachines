"""Route-gossip transport, provenance, world-boundary and replay checks."""

import contextlib
import copy
import io
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import jsonschema
from freight_world import FreightWorld
from route_gossip import POLICY, make_report
from runner import (
    Agent,
    CommunicationTopology,
    EventLog,
    MessageLifecycle,
    MessageStore,
    TurnSeamRunner,
)


class IntegrationTests(unittest.TestCase):
    def runner(self, topology="mesh", mute=True):
        return TurnSeamRunner(
            42,
            topology,
            ["a", "b", "c", "d"],
            {"peer-mute": {"turn": 8, "agent": "c"}} if mute else {},
            use_freight_world=True,
            policy=POLICY,
        )

    def test_provenance_schema_and_replay(self):
        first = self.runner()
        data = first.run(16)
        self.assertEqual(data, self.runner().run(16))
        schema = json.loads(
            (Path(__file__).parent / "schema/events.schema.json").read_text()
        )
        validator = jsonschema.Draft202012Validator(schema)
        events = first.log.events
        by_seq = {e["seq"]: e for e in events}
        delivered = {
            e["payload"]["message_id"]: e
            for e in events
            if e["type"] == "message.delivered"
            and e["payload"]["status"] == "delivered"
        }
        reports = {
            e["payload"]["message_id"]: e
            for e in events
            if e["type"] == "policy.report" and e["payload"]["admitted"]
        }
        proposed = {
            e["payload"]["action_id"]: e
            for e in events
            if e["type"] == "action.proposed"
        }
        for event in events:
            validator.validate(event)
            if event["type"] == "policy.report":
                delivery = delivered[event["payload"]["message_id"]]
                self.assertLess(delivery["seq"], event["seq"])
                self.assertEqual(delivery["agent_id"], event["agent_id"])
                sender_view = next(
                    e["payload"]["visible"]
                    for e in events
                    if e["type"] == "observation.recorded"
                    and e["agent_id"] == event["payload"]["sender"]
                    and e["turn"] == event["turn"]
                )
                self.assertEqual(
                    event["payload"]["routes"], sender_view["known_routes"]
                )
            if event["type"] == "policy.decision":
                decision = event["payload"]
                observation = by_seq[decision["observation_seq"]]
                self.assertEqual(
                    (observation["type"], observation["agent_id"], observation["turn"]),
                    ("observation.recorded", event["agent_id"], event["turn"]),
                )
                for mid in decision["consumed_message_ids"]:
                    self.assertEqual(reports[mid]["turn"], event["turn"])
                    self.assertEqual(reports[mid]["agent_id"], event["agent_id"])
                if decision["action_id"]:
                    self.assertIn(decision["action_id"], proposed)
        self.assertEqual(len([e for e in events if e["type"] == "policy.decision"]), 64)
        self.assertFalse(any(e["type"] == "message.acted_on" for e in events))

    def test_mute_ring_and_opportunity_noninterference(self):
        runs = [
            self.runner("mesh", False),
            self.runner("mesh"),
            self.runner("bidirectional-ring"),
        ]
        for runner in runs:
            runner.run(16)
        opportunities = [
            [
                (e["agent_id"], e["turn"], e["payload"]["opportunity"])
                for e in r.log.events
                if e["type"] == "policy.decision"
            ]
            for r in runs
        ]
        self.assertEqual(opportunities[0], opportunities[1])
        self.assertEqual(opportunities[1], opportunities[2])

        def mids(r):
            return {
                e["payload"]["message_id"]
                for e in r.log.events
                if e["type"] == "policy.report"
            }

        self.assertNotEqual(mids(runs[0]), mids(runs[1]))
        self.assertNotEqual(mids(runs[1]), mids(runs[2]))
        for runner in runs[1:]:
            for e in runner.log.events:
                if e["type"] == "policy.report" and e["turn"] >= 8:
                    self.assertNotEqual(e["agent_id"], "c")
                    self.assertNotEqual(e["payload"]["sender"], "c")
            self.assertEqual(
                len(
                    [
                        e
                        for e in runner.log.events
                        if e["type"] == "policy.decision" and e["agent_id"] == "c"
                    ]
                ),
                16,
            )

    def setup_agent(self):
        world = FreightWorld(42)
        world.freight_items["f-001"].destination = "relay-a"
        world.routes["west->relay-a"].status = "closed"
        agent = Agent("a", 42, 0, POLICY)
        agent.act_rng = random.Random(0)  # identical positive opportunity
        log = EventLog("fixture", "2026-11-07T14:30:00Z")
        agent.observe({}, 8, log, world)
        return world, agent, log

    def test_actual_world_validates_both_report_selected_hops(self):
        paths = []
        for east, south in [("open", "closed"), ("closed", "open")]:
            world, agent, log = self.setup_agent()
            # Synthetic current reports: only these inputs change, not the world.
            for sender, location, state in [("b", "east", east), ("c", "south", south)]:
                body = make_report(
                    {
                        "current_location": location,
                        "turn": 8,
                        "known_routes": {f"{location}->relay-a": state},
                    },
                    sender,
                )
                peer = Agent(sender, 42, 1, POLICY)
                peer.observation = {
                    "current_location": location,
                    "turn": 8,
                    "known_routes": body["routes"],
                }
                peer.exchange_send_rng = random.Random(0)
                peer.exchange(
                    CommunicationTopology("mesh", ["a", sender]),
                    [agent],
                    MessageStore(),
                    MessageLifecycle(),
                    8,
                    log,
                    {},
                )
            before = copy.deepcopy(world.freight_items)
            # Proposal selection cannot query live world getters.
            with (
                patch.object(
                    world, "get_freight_at_location", side_effect=AssertionError
                ),
                patch.object(
                    world, "get_adjacent_locations", side_effect=AssertionError
                ),
            ):
                agent.act(8, log, freight_world=world)
            decision = next(
                e["payload"] for e in log.events if e["type"] == "policy.decision"
            )
            paths.append(decision["next_hop"])
            validated = next(
                e["payload"] for e in log.events if e["type"] == "action.validated"
            )
            self.assertTrue(validated["legal"])
            self.assertTrue(any(e["type"] == "action.committed" for e in log.events))
            self.assertNotEqual(before, world.freight_items)
        self.assertEqual(paths, ["east", "south"])

    def test_refused_reports_and_turn_reset(self):
        world, agent, log = self.setup_agent()
        body = make_report(
            {
                "current_location": "east",
                "turn": 7,
                "known_routes": {"east->relay-a": "open"},
            },
            "b",
        )
        agent.receive_report(body, "b", "m-b", 8, log)
        self.assertEqual(agent.inbox, [])
        self.assertFalse(log.events[-1]["payload"]["admitted"])
        body["turn"] = 8
        agent.receive_report(body, "b", "m-b2", 8, log)
        self.assertEqual(len(agent.inbox), 1)
        agent.observe({}, 9, log, world)
        self.assertEqual(agent.inbox, [])

    def test_noop_and_application_rejection(self):
        world, agent, log = self.setup_agent()
        agent.observation["visible_freight"] = []
        agent.act(8, log, freight_world=world)
        self.assertFalse(any(e["type"].startswith("action.") for e in log.events))
        world, agent, log = self.setup_agent()
        agent.observation["visible_freight"][0]["destination"] = "east"
        with patch.object(
            world, "apply_action", return_value=(False, "capacity", None)
        ):
            agent.act(8, log, freight_world=world)
        self.assertTrue(any(e["type"] == "action.rejected" for e in log.events))
        self.assertFalse(any(e["type"] == "action.committed" for e in log.events))

    def test_validation_rejection_is_not_committed(self):
        world, agent, log = self.setup_agent()
        agent.observation["visible_freight"][0]["destination"] = "east"
        with (
            patch.object(world, "validate_action", return_value=(False, "closed")),
            patch.object(world, "apply_action", side_effect=AssertionError),
        ):
            agent.act(8, log, freight_world=world)
        self.assertTrue(any(e["type"] == "action.rejected" for e in log.events))
        self.assertFalse(any(e["type"] == "action.committed" for e in log.events))

    def test_decision_schema_rejects_missing_provenance(self):
        runner = self.runner()
        runner.run(1)
        event = copy.deepcopy(
            next(e for e in runner.log.events if e["type"] == "policy.decision")
        )
        del event["payload"]["observation_seq"]
        schema = json.loads(
            (Path(__file__).parent / "schema/events.schema.json").read_text()
        )
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(event)

    def test_verifier_rejects_partial_policy_file(self):
        import verify_events

        data = self.runner().run(1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "episode.jsonl"
            path.write_text(data + "\n{}\n")
            with (
                patch.object(sys, "argv", ["verify_events.py", str(path)]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(verify_events.main(), 1)

    def test_verifier_accepts_policy_without_influence_markers(self):
        import verify_events

        data = self.runner().run(1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "episode.jsonl"
            path.write_text(data + "\n")
            with (
                patch.object(sys, "argv", ["verify_events.py", str(path)]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(verify_events.main(), 0)

    def test_explicit_mode_boundary(self):
        with self.assertRaises(ValueError):
            TurnSeamRunner(42, "mesh", ["a"], {}, policy=POLICY)
        for agents in (["a", "a"], ["a" * 41], []):
            with self.assertRaises(ValueError):
                TurnSeamRunner(
                    42, "mesh", agents, {}, use_freight_world=True, policy=POLICY
                )


if __name__ == "__main__":
    unittest.main()
