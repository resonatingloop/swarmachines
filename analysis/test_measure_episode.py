"""Fictional contract fixtures and real runtime instrumentation checks."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analysis.measure_episode import analyze_bytes, main


def fixture(completed=None, empty=False):
    events = []

    def emit(turn, kind, payload, agent=None):
        events.append(
            {
                "run_id": "fixture",
                "seq": len(events),
                "turn": turn,
                "agent_id": agent,
                "type": kind,
                "ts": "2026-11-07T14:30:00Z",
                "payload": payload,
            }
        )

    emit(
        0,
        "run.config",
        {
            "policy": "route-gossip-v1",
            "world": "freight",
            "job_evidence_version": 1,
            "horizon_turns": 16,
            "disturbance_schedule": {"peer-mute": {"turn": 8, "agent": "c"}},
        },
    )
    row = {
        "job_id": "actual-job",
        "freight_id": "f-1",
        "origin": "a",
        "destination": "b",
        "release_turn": 0,
        "state": "pending",
    }
    emit(0, "jobs.initialized", {"jobs": [] if empty else [row]})
    for turn in range(1, 17):
        emit(turn, "turn.begin", {})
        if turn == 8:
            emit(
                turn,
                "disturbance.applied",
                {"kind": "peer-mute", "detail": {"agent": "c"}},
            )
        if turn == completed:
            emit(
                turn,
                "action.proposed",
                {"action_id": "act-1", "freight_id": "f-1"},
                "a",
            )
            emit(turn, "action.validated", {"action_id": "act-1", "legal": True}, "a")
            emit(
                turn,
                "action.committed",
                {"action_id": "act-1", "freight_id": "f-1", "new_state": "delivered"},
                "a",
            )
            emit(
                turn,
                "job.completed",
                {"action_id": "act-1", "job_id": "actual-job", "freight_id": "f-1"},
                "a",
            )
    final = {
        "job_id": "actual-job",
        "freight_id": "f-1",
        "state": "delivered" if completed else "pending",
    }
    emit(
        16,
        "run.end",
        {
            "jobs": [] if empty else [final],
            "termination": "completed",
            "horizon_turns": 16,
            "recovery_interval_turns": 9,
        },
    )
    return events


def raw(events):
    return ("\n".join(json.dumps(e) for e in events) + "\n").encode()


class MeasureTests(unittest.TestCase):
    def test_completion_and_zero_delay(self):
        r = analyze_bytes(raw(fixture(8)))
        self.assertEqual(r["status"], "valid")
        self.assertEqual(
            (
                r["completion"]["numerator"],
                r["completion"]["denominator"],
                r["completion"]["value"],
            ),
            (1, 1, 1),
        )
        self.assertEqual(r["resumption"]["value"], 0)
        self.assertEqual(r["resumption"]["job_ids"], ["actual-job"])

    def test_pre_intervention_last_turn_and_censoring(self):
        for completed, status, value in [
            (7, "right_censored", None),
            (16, "available", 8),
            (None, "right_censored", None),
        ]:
            r = analyze_bytes(raw(fixture(completed)))
            self.assertEqual(r["resumption"]["status"], status)
            self.assertEqual(r["resumption"]["value"], value)

    def test_zero_roster_undefined(self):
        r = analyze_bytes(raw(fixture(empty=True)))
        self.assertEqual(r["completion"]["status"], "undefined")
        self.assertEqual(r["completion"]["denominator"], 0)
        self.assertIsNone(r["completion"]["value"])

    def test_partial_is_not_censored(self):
        r = analyze_bytes(raw(fixture(8)[:-1]))
        self.assertEqual(r["completion"]["status"], "unavailable")
        self.assertEqual(r["resumption"]["status"], "unavailable")

    def test_bad_line_is_invalid_not_dropped(self):
        self.assertEqual(
            analyze_bytes(raw(fixture()) + b"not json\n")["status"], "invalid"
        )
        self.assertEqual(analyze_bytes(b'{"x":1,"x":2}\n')["status"], "invalid")
        self.assertEqual(analyze_bytes(b"\xff")["status"], "invalid")

    def test_identity_and_state_contradictions(self):
        for mutation in [
            "unknown",
            "duplicate",
            "freight",
            "failed",
            "terminal",
            "after",
            "missingcommit",
            "turngap",
            "terminal_identity",
            "duplicate_roster",
            "missingcompletion",
        ]:
            e = fixture(8)
            completion = next(x for x in e if x["type"] == "job.completed")
            if mutation == "unknown":
                completion["payload"]["job_id"] = "other"
            elif mutation == "duplicate":
                e.insert(e.index(completion) + 1, copy.deepcopy(completion))
            elif mutation == "freight":
                completion["payload"]["freight_id"] = "other"
            elif mutation == "failed":
                next(x for x in e if x["type"] == "action.validated")["payload"][
                    "legal"
                ] = False
            elif mutation == "terminal":
                e[-1]["payload"]["jobs"][0]["state"] = "pending"
            elif mutation == "after":
                e.append(copy.deepcopy(e[-1]))
            elif mutation == "missingcommit":
                e = [x for x in e if x["type"] != "action.committed"]
            elif mutation == "terminal_identity":
                e[-1]["payload"]["jobs"][0]["job_id"] = "other"
            elif mutation == "duplicate_roster":
                e[1]["payload"]["jobs"].append(
                    copy.deepcopy(e[1]["payload"]["jobs"][0])
                )
            elif mutation == "missingcompletion":
                e = [x for x in e if x["type"] != "job.completed"]
                e[-1]["payload"]["jobs"][0]["state"] = "pending"
            else:
                e = [x for x in e if not (x["type"] == "turn.begin" and x["turn"] == 4)]
            for seq, event in enumerate(e):
                event["seq"] = seq
            self.assertEqual(analyze_bytes(raw(e))["status"], "invalid", mutation)

    def test_wrong_intervention_does_not_discard_primary(self):
        e = fixture(8)
        next(x for x in e if x["type"] == "disturbance.applied")["payload"]["detail"][
            "agent"
        ] = "b"
        r = analyze_bytes(raw(e))
        self.assertEqual(r["completion"]["status"], "available")
        self.assertEqual(r["resumption"]["status"], "unavailable")

    def test_legacy_is_not_inferred(self):
        e = fixture()
        e[0]["payload"] = {}
        e = [x for x in e if x["type"] != "jobs.initialized"]
        e[-1]["payload"] = {}
        r = analyze_bytes(raw(e))
        self.assertEqual(r["completion"]["status"], "unavailable")

    def test_cli_exclusive_private_output_and_no_network(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "episode.jsonl"
            target = Path(directory) / "result.json"
            source.write_bytes(raw(fixture(8)))
            with patch(
                "socket.socket", side_effect=AssertionError("network forbidden")
            ):
                self.assertEqual(main([str(source), "--output", str(target)]), 0)
            before = target.read_bytes()
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(main([str(source), "--output", str(target)]), 2)
            self.assertEqual(before, target.read_bytes())

    def test_real_runtime_roundtrip(self):
        import sys

        sys.path.insert(0, str(Path(__file__).parents[1] / "runtime"))
        from runner import TurnSeamRunner

        runner = TurnSeamRunner(
            42,
            "mesh",
            ["a", "b", "c", "d"],
            {"peer-mute": {"turn": 8, "agent": "c"}},
            use_freight_world=True,
            policy="route-gossip-v1",
        )
        r = analyze_bytes((runner.run(16) + "\n").encode())
        self.assertEqual(r["status"], "valid", r)
        self.assertEqual(
            r["completion"]["denominator"], len(runner.freight_world.delivery_jobs)
        )
        self.assertEqual(
            r["completion"]["numerator"],
            runner.freight_world.get_delivery_stats()["delivered"],
        )


def _seal_records(events):
    """Independent seal-contract oracle: chain fixture events and append run.seal."""
    genesis = hashlib.sha256(
        ("swarmachines/eventlog-seal-v1|" + events[0]["run_id"]).encode()
    ).hexdigest()
    prev = genesis
    chained = []
    for event in events:
        record = dict(event)
        stripped = {k: v for k, v in record.items() if k != "chain"}
        canonical = json.dumps(stripped, sort_keys=True, separators=(",", ":"))
        record["chain"] = hashlib.sha256((prev + "|" + canonical).encode()).hexdigest()
        prev = record["chain"]
        chained.append(record)
    seal = {
        "run_id": events[0]["run_id"],
        "seq": len(events),
        "turn": events[-1]["turn"],
        "agent_id": None,
        "type": "run.seal",
        "ts": "2026-11-07T14:30:01Z",
        "payload": {
            "chain": prev,
            "events": len(events),
            "alg": "eventlog-seal-v1",
        },
    }
    return chained + [seal]


class SealTests(unittest.TestCase):
    def test_honest_seal_is_valid_and_measures_identically(self):
        sealed = analyze_bytes(raw(_seal_records(fixture(8))))
        self.assertEqual(sealed["status"], "valid")
        legacy = analyze_bytes(raw(fixture(8)))
        self.assertEqual(legacy["status"], "valid")
        without_provenance = lambda r: {k: v for k, v in r.items() if k != "sha256"}
        self.assertEqual(without_provenance(sealed), without_provenance(legacy))

    def test_tampered_event_is_invalid(self):
        records = _seal_records(fixture(8))
        records[5]["payload"]["detail"] = "fabricated"
        self.assertEqual(analyze_bytes(raw(records))["status"], "invalid")

    def test_inserted_event_is_invalid(self):
        records = _seal_records(fixture(8))
        forged = dict(records[5])
        forged["payload"] = {"fabricated": True}
        records.insert(6, forged)
        self.assertEqual(analyze_bytes(raw(records))["status"], "invalid")

    def test_truncated_event_is_invalid(self):
        records = _seal_records(fixture(8))
        del records[7]
        self.assertEqual(analyze_bytes(raw(records))["status"], "invalid")

    def test_partial_chain_is_invalid(self):
        records = _seal_records(fixture(8))
        del records[3]["chain"]
        self.assertEqual(analyze_bytes(raw(records))["status"], "invalid")

    def test_chain_without_seal_is_invalid(self):
        records = _seal_records(fixture(8))[:-1]
        self.assertEqual(analyze_bytes(raw(records))["status"], "invalid")

    def test_seal_not_last_is_invalid(self):
        records = _seal_records(fixture(8))
        trailing = dict(records[-1])
        trailing["seq"] = records[-1]["seq"] + 1
        trailing["type"] = "observation.recorded"
        trailing["payload"] = {}
        self.assertEqual(analyze_bytes(raw(records + [trailing]))["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
