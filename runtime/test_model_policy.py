"""offline proofs for the model action, budget and experiment apparatus seams."""

import hashlib
import json
import os
import random
import tempfile
import unittest
from pathlib import Path

import jsonschema
from adaption_adapter import AdapterResponse, AdapterUsage
from freight_world import FreightWorld
from model_policy import (
    MAX_OUTPUT_TOKENS,
    OUTPUT_CONTRACT,
    BudgetExhausted,
    BudgetLedger,
    ModelActionPolicy,
    ModelOutputError,
    candidate_actions,
    estimate_microcredits,
    parse_model_output,
)
from route_gossip import Report, select
from runner import TurnSeamRunner, verify_seal

MODEL = "gemma-4-26b-a4b-it"


class FakeAdapter:
    def __init__(self, outputs=None, error=None, status=None, incomplete_reason=None):
        self.outputs = list(outputs or [])
        self.error = error
        self.status = status
        self.incomplete_reason = incomplete_reason
        self.calls = []

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return AdapterResponse(
            model=kwargs["model"],
            output_text=self.outputs.pop(0),
            usage=AdapterUsage(input_tokens=100, output_tokens=20, total_tokens=120),
            latency_ms=12.5,
            raw_response=None,
            status=self.status,
            incomplete_reason=self.incomplete_reason,
        )


class ApparatusTests(unittest.TestCase):
    def test_staggered_jobs_are_not_visible_before_release(self):
        world = FreightWorld(seed=42, release_turns=FreightWorld.RELEASE_TURNS)
        world.observe("a", 8, random.Random(1))
        self.assertNotIn(
            "f-003", [item.item_id for item in world.get_freight_at_location("south")]
        )
        self.assertNotIn(
            "f-004", [item.item_id for item in world.get_freight_at_location("relay-a")]
        )
        world.observe("d", 11, random.Random(1))
        self.assertIn(
            "f-004", [item.item_id for item in world.get_freight_at_location("relay-a")]
        )

    def test_peer_required_route_needs_remote_report_for_path(self):
        world = FreightWorld(seed=42, regime="peer-required")
        observation = world.observe("a", 1, random.Random(1))
        local = select(observation)
        self.assertIsNone(local["next_hop"])
        relay_routes = tuple(
            sorted(
                (key, route.status)
                for key, route in world.routes.items()
                if route.from_loc == "relay-a"
            )
        )
        report = Report("m-d001", "d", 1, relay_routes)
        informed = select(observation, (report,))
        self.assertEqual(informed["next_hop"], "relay-a")
        self.assertTrue(informed["choice_changed"])


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.observation = FreightWorld(seed=42).observe("a", 1, random.Random(1))
        self.candidates = candidate_actions(self.observation)

    def test_accepts_exact_candidate_and_null(self):
        candidate = self.candidates[0]
        parsed = parse_model_output(
            json.dumps({"action": candidate, "reason": "bounded route"}),
            self.candidates,
        )
        self.assertEqual(parsed.action, candidate)
        self.assertIsNone(
            parse_model_output(
                '{"action":null,"reason":"wait"}', self.candidates
            ).action
        )

    def test_accepts_one_solitary_json_fence(self):
        candidate = self.candidates[0]
        text = f"```json\n{json.dumps({'action': candidate, 'reason': 'bounded route'})}\n```"
        self.assertEqual(parse_model_output(text, self.candidates).action, candidate)

    def test_rejects_prose_extra_fences_extra_keys_and_unoffered_actions(self):
        cases = (
            'here you go\n```json\n{"action":null,"reason":"wait"}\n```',
            '```json\n{"action":null,"reason":"wait"}\n```\nmore',
            '```\n{"action":null,"reason":"wait"}\n```',
            '```json\n{"action":null,"reason":"wait"}\n```\n```json\n{}\n```',
            '{"action":null,"reason":"wait","extra":true}',
            '{"action":{"kind":"route_freight","freight_id":"f-999","via":"west->east"},"reason":"invented"}',
        )
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ModelOutputError):
                parse_model_output(text, self.candidates)


class LedgerAndPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.observation = FreightWorld(seed=42).observe("a", 1, random.Random(1))

    def tearDown(self):
        self.temp.cleanup()

    def ledger(self, ceiling=None):
        return BudgetLedger(
            self.root / "ledger.json",
            ceiling or estimate_microcredits(MODEL) * 4,
        )

    def test_reserve_is_fail_closed_and_private(self):
        reservation = estimate_microcredits(MODEL)
        ledger = self.ledger(reservation)
        ledger.reserve(MODEL, {"run_id": "r", "agent_id": "a", "turn": 1})
        with self.assertRaises(BudgetExhausted):
            ledger.reserve(MODEL, {"run_id": "r", "agent_id": "b", "turn": 1})
        self.assertEqual(os.stat(self.root / "ledger.json").st_mode & 0o777, 0o600)
        self.assertEqual(ledger.snapshot()["charged_microcredits"], reservation)

    def test_valid_call_settles_and_writes_private_evidence(self):
        candidate = candidate_actions(self.observation)[0]
        adapter = FakeAdapter(
            [json.dumps({"action": candidate, "reason": "use route"})]
        )
        policy = ModelActionPolicy(
            model=MODEL,
            adapter=adapter,
            ledger=self.ledger(),
            evidence_dir=self.root / "raw",
        )
        decision = policy.decide(self.observation, (), run_id="r", agent_id="a", turn=1)
        self.assertEqual(decision.status, "completed")
        self.assertEqual(decision.action, candidate)
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(MAX_OUTPUT_TOKENS, 2_048)
        self.assertEqual(adapter.calls[0]["max_output_tokens"], 2_048)
        self.assertEqual(decision.cost_basis, "published_rate_estimate")
        self.assertEqual(decision.output_contract, OUTPUT_CONTRACT)
        self.assertEqual(decision.max_output_tokens, 2_048)
        sidecar = self.root / "raw" / f"{decision.attempt_id}.json"
        self.assertEqual(os.stat(sidecar).st_mode & 0o777, 0o600)
        self.assertNotIn("use route", json.dumps(decision.__dict__))

    def test_unpriced_replacement_retains_fixed_conservative_reservation(self):
        model = "qwen3.8-27b"
        reservation = estimate_microcredits(model)
        self.assertEqual(reservation, 1_000_000)
        ledger = BudgetLedger(self.root / "replacement.json", reservation)
        decision = ModelActionPolicy(
            model=model,
            adapter=FakeAdapter(['{"action":null,"reason":"wait"}']),
            ledger=ledger,
            evidence_dir=self.root / "replacement-raw",
        ).decide(self.observation, (), run_id="r", agent_id="a", turn=1)
        self.assertEqual(decision.status, "null")
        self.assertEqual(decision.reserved_microcredits, reservation)
        self.assertEqual(decision.charged_microcredits, reservation)
        self.assertEqual(decision.cost_basis, "fixed_conservative_reservation")
        self.assertEqual(
            ledger.snapshot()["attempts"][0]["cost_basis"],
            "fixed_conservative_reservation",
        )

    def test_malformed_and_provider_failure_remain_visible(self):
        malformed = ModelActionPolicy(
            model=MODEL,
            adapter=FakeAdapter(["not json"]),
            ledger=self.ledger(),
            evidence_dir=self.root / "raw",
        ).decide(self.observation, (), run_id="r", agent_id="a", turn=1)
        self.assertEqual(malformed.status, "malformed")

        failure_root = self.root / "failure"
        failed = ModelActionPolicy(
            model=MODEL,
            adapter=FakeAdapter(error=RuntimeError("provider detail")),
            ledger=BudgetLedger(
                failure_root / "ledger.json", estimate_microcredits(MODEL)
            ),
            evidence_dir=failure_root / "raw",
        ).decide(self.observation, (), run_id="r", agent_id="a", turn=1)
        self.assertEqual(failed.status, "provider_failed")
        self.assertEqual(failed.charged_microcredits, estimate_microcredits(MODEL))
        self.assertNotIn("provider detail", json.dumps(failed.__dict__))

    def test_incomplete_response_is_not_misreported_as_malformed(self):
        decision = ModelActionPolicy(
            model=MODEL,
            adapter=FakeAdapter(
                [""], status="incomplete", incomplete_reason="max_output_tokens"
            ),
            ledger=self.ledger(),
            evidence_dir=self.root / "raw",
        ).decide(self.observation, (), run_id="r", agent_id="a", turn=1)
        self.assertEqual(decision.status, "incomplete")
        self.assertEqual(decision.reason, "max_output_tokens")
        self.assertEqual(decision.provider_status, "incomplete")

    def test_noncompleted_provider_status_never_commits_an_action(self):
        candidate = candidate_actions(self.observation)[0]
        decision = ModelActionPolicy(
            model=MODEL,
            adapter=FakeAdapter(
                [json.dumps({"action": candidate, "reason": "looks valid"})],
                status="failed",
            ),
            ledger=self.ledger(),
            evidence_dir=self.root / "raw",
        ).decide(self.observation, (), run_id="r", agent_id="a", turn=1)
        self.assertEqual(decision.status, "provider_failed")
        self.assertIsNone(decision.action)

    def test_oversized_input_is_rejected_before_reservation(self):
        observation = dict(self.observation)
        observation["known_routes"] = {
            f"west->{'x' * 90}{index}": "open" for index in range(32)
        }
        adapter = FakeAdapter(['{"action":null,"reason":"unused"}'])
        ledger = self.ledger()
        decision = ModelActionPolicy(
            model=MODEL,
            adapter=adapter,
            ledger=ledger,
            evidence_dir=self.root / "raw",
        ).decide(observation, (), run_id="r", agent_id="a", turn=1)
        self.assertEqual(decision.status, "input_rejected")
        self.assertEqual(adapter.calls, [])
        self.assertEqual(ledger.snapshot()["attempts"], [])

    def test_private_evidence_failure_blocks_action_after_call(self):
        candidate = candidate_actions(self.observation)[0]
        blocked_path = self.root / "not-a-directory"
        blocked_path.write_text("fixture")
        decision = ModelActionPolicy(
            model=MODEL,
            adapter=FakeAdapter(
                [json.dumps({"action": candidate, "reason": "looks valid"})],
                status="completed",
            ),
            ledger=self.ledger(),
            evidence_dir=blocked_path,
        ).decide(self.observation, (), run_id="r", agent_id="a", turn=1)
        self.assertEqual(decision.status, "evidence_failed")
        self.assertIsNone(decision.action)

    def test_budget_stop_makes_no_provider_call(self):
        adapter = FakeAdapter(['{"action":null,"reason":"wait"}'])
        ledger = BudgetLedger(self.root / "small.json", estimate_microcredits(MODEL))
        ledger.reserve(MODEL, {"run_id": "prior", "agent_id": "a", "turn": 1})
        decision = ModelActionPolicy(
            model=MODEL,
            adapter=adapter,
            ledger=ledger,
            evidence_dir=self.root / "raw",
        ).decide(self.observation, (), run_id="r", agent_id="a", turn=1)
        self.assertEqual(decision.status, "budget_stopped")
        self.assertEqual(adapter.calls, [])

    def test_runner_records_sealed_model_episode_without_raw_output(self):
        adapter = FakeAdapter(['{"action":null,"reason":"private wait text"}'] * 2)
        policy = ModelActionPolicy(
            model=MODEL,
            adapter=adapter,
            ledger=self.ledger(),
            evidence_dir=self.root / "raw",
        )
        runner = TurnSeamRunner(
            seed=42,
            comm_topology="mesh",
            agents_config=["a"],
            disturbance_schedule={},
            use_freight_world=True,
            policy="model-route-v1",
            model_policy=policy,
            world_regime="peer-required",
            release_turns=FreightWorld.RELEASE_TURNS,
        )
        condition = {
            "model": MODEL,
            "output_contract": OUTPUT_CONTRACT,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "topology": "mesh",
            "disturbance": {},
            "regime": "peer-required",
            "seed": 42,
            "agents": ["a"],
            "release_turns": FreightWorld.RELEASE_TURNS,
        }
        digest = hashlib.sha256(
            json.dumps(condition, sort_keys=True).encode("utf-8")
        ).hexdigest()[:12]
        self.assertEqual(runner.run_id, f"run-model-seed0042-{digest}")
        output = runner.run(2)
        events = [json.loads(line) for line in output.splitlines()]
        schema = json.loads(
            (Path(__file__).parent / "schema" / "events.schema.json").read_text()
        )
        for event in events:
            jsonschema.validate(event, schema)
        verify_seal(events)
        decisions = [event for event in events if event["type"] == "model.decision"]
        self.assertEqual(len(decisions), 2)
        self.assertTrue(
            all(event["payload"]["status"] == "null" for event in decisions)
        )
        self.assertTrue(
            all(
                event["payload"]["output_contract"] == OUTPUT_CONTRACT
                and event["payload"]["max_output_tokens"] == 2_048
                for event in decisions
            )
        )
        self.assertNotIn("private wait text", output)
        initialized = next(
            event for event in events if event["type"] == "jobs.initialized"
        )
        self.assertEqual(
            [job["release_turn"] for job in initialized["payload"]["jobs"]],
            [1, 7, 9, 11],
        )


if __name__ == "__main__":
    unittest.main()
