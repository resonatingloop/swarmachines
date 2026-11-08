"""Validate complete episode bytes and compute evidence-bound offline measures."""

import argparse
import hashlib
import json
import os
import stat
from collections import Counter
from pathlib import Path

import jsonschema

MAX_BYTES = 10_000_000
MAX_EVENTS = 20_000
SCHEMA = Path(__file__).resolve().parents[1] / "runtime/schema/events.schema.json"


class EvidenceError(ValueError):
    """Categorical evidence failure; never includes source text."""


def require(condition, reason):
    """Reject a failed evidence invariant with a categorical reason."""
    if not condition:
        raise EvidenceError(reason)


def unique_object(pairs):
    """Reject ambiguous JSON objects containing duplicate keys."""
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def unavailable(reason):
    """Represent an unsupported measure without substituting a value."""
    return {"status": "unavailable", "value": None, "reason": reason}


def _load(raw):
    require(len(raw) <= MAX_BYTES, "input_limit")
    text = raw.decode("utf-8", errors="strict")
    schema = json.loads(SCHEMA.read_text())
    validator = jsonschema.Draft202012Validator(schema)
    events = []
    for line in text.splitlines():
        if not line.strip():
            continue
        require(len(line) <= 10_000, "line_limit")
        event = json.loads(
            line,
            object_pairs_hook=unique_object,
            parse_constant=lambda _: (_ for _ in ()).throw(
                EvidenceError("nonfinite_json")
            ),
        )
        validator.validate(event)
        events.append(event)
        require(len(events) <= MAX_EVENTS, "event_limit")
    require(bool(events), "empty_episode")
    run_id = events[0]["run_id"]
    previous_seq, previous_turn = -1, -1
    ended = False
    for event in events:
        require(not ended, "event_after_terminal")
        require(event["run_id"] == run_id, "mixed_runs")
        require(event["seq"] > previous_seq, "sequence_order")
        require(event["turn"] >= previous_turn, "turn_order")
        previous_seq, previous_turn = event["seq"], event["turn"]
        ended = event["type"] == "run.end"
    configs = [e for e in events if e["type"] == "run.config"]
    require(
        len(configs) == 1 and configs[0] is events[0] and configs[0]["turn"] == 0,
        "configuration_envelope",
    )
    return events, configs[0]


def _identities(events):
    proposals, validations, commits, rejected, sent, deliveries = {}, {}, {}, {}, {}, {}
    traffic = {"before": {}, "after": {}}
    for event in events:
        kind, p = event["type"], event["payload"]
        if kind.startswith("action."):
            aid = p.get("action_id")
            require(isinstance(aid, str) and bool(aid), "action_identity")
            if kind == "action.proposed":
                require(aid not in proposals, "duplicate_proposal")
                proposals[aid] = event
            else:
                require(aid in proposals, "unknown_action")
                require(
                    (event["agent_id"], event["turn"])
                    == (proposals[aid]["agent_id"], proposals[aid]["turn"]),
                    "action_context",
                )
                if kind == "action.validated":
                    require(
                        aid not in validations and type(p.get("legal")) is bool,
                        "validation_record",
                    )
                    validations[aid] = event
                elif kind in ("action.committed", "action.rejected"):
                    require(
                        aid in validations
                        and aid not in commits
                        and aid not in rejected,
                        "action_terminal",
                    )
                    if kind == "action.committed":
                        require(validations[aid]["payload"]["legal"], "illegal_commit")
                        if (
                            "freight_id" in p
                            and "freight_id" in proposals[aid]["payload"]
                        ):
                            require(
                                p["freight_id"]
                                == proposals[aid]["payload"]["freight_id"],
                                "commit_freight_mismatch",
                            )
                        commits[aid] = event
                    else:
                        rejected[aid] = event
        if kind == "message.sent":
            mid = p["message_id"]
            require(
                mid not in sent and p["from"] == event["agent_id"], "message_identity"
            )
            sent[mid] = event
        if kind == "message.delivered":
            mid = p["message_id"]
            require(mid in sent and mid not in deliveries, "delivery_identity")
            source = sent[mid]["payload"]
            require(p["to"] == source["to"] == event["agent_id"], "delivery_recipient")
            deliveries[mid] = event
        if kind in ("message.seen", "message.acted_on"):
            mid = p.get("message_id")
            require(
                mid in deliveries
                and deliveries[mid]["payload"]["status"] == "delivered",
                "message_use_without_delivery",
            )
            require(
                event["agent_id"] == deliveries[mid]["agent_id"],
                "message_use_recipient",
            )
        if kind in ("message.sent", "message.delivered") and 1 <= event["turn"] <= 16:
            window = "before" if event["turn"] < 8 else "after"
            who = event["agent_id"]
            bucket = traffic[window].setdefault(
                who, {"sent": 0, "delivered": 0, "undelivered": 0, "sequences": []}
            )
            bucket["sent" if kind == "message.sent" else p["status"]] += 1
            bucket["sequences"].append(event["seq"])
    if (
        events[0]["payload"].get("job_evidence_version") == 1
        and events[-1]["type"] == "run.end"
    ):
        require(
            set(proposals) == set(validations) == (set(commits) | set(rejected)),
            "incomplete_action_lifecycle",
        )
    counts = {
        "proposed": len(proposals),
        "validated": len(validations),
        "committed": len(commits),
        "rejected": len(rejected),
        "validation_rejected": sum(
            not validations[a]["payload"]["legal"] for a in rejected
        ),
        "apply_rejected": sum(validations[a]["payload"]["legal"] for a in rejected),
        "reasons": dict(Counter(e["payload"]["reason"] for e in rejected.values())),
        "sequences": [e["seq"] for e in events if e["type"].startswith("action.")],
    }
    for name, low, high in (("before", 1, 7), ("after", 8, 16)):
        traffic[name] = {
            "turn_window": [low, high],
            "expected_exposure_turns": high - low + 1,
            "observed_turns": sorted(
                {
                    e["turn"]
                    for e in events
                    if e["type"] == "turn.begin" and low <= e["turn"] <= high
                }
            ),
            "agents": traffic[name],
        }
    return commits, counts, traffic


def _jobs(events, config, commits):
    p = config["payload"]
    initial = [e for e in events if e["type"] == "jobs.initialized"]
    completions = [e for e in events if e["type"] == "job.completed"]
    terminal = events[-1] if events[-1]["type"] == "run.end" else None
    if p.get("job_evidence_version") != 1:
        require(not initial and not completions, "unversioned_job_records")
        return unavailable("missing_job_evidence_version"), unavailable(
            "missing_job_evidence_version"
        )
    require(type(p["job_evidence_version"]) is int, "evidence_version_type")
    require(
        p.get("policy") == "route-gossip-v1" and p.get("world") == "freight",
        "evidence_mode",
    )
    horizon = p.get("horizon_turns")
    require(type(horizon) is int and 1 <= horizon <= 100, "horizon")
    require(all(e["turn"] <= horizon for e in events), "event_beyond_horizon")
    require(len(initial) <= 1, "duplicate_roster")
    if not initial:
        require(
            not completions
            and not any(e["type"].startswith("action.") for e in events),
            "missing_initial_roster",
        )
        require(terminal is None, "missing_initial_roster")
        return unavailable("incomplete_episode"), unavailable("incomplete_episode")
    init = initial[0]
    require(init["turn"] == 0 and init["agent_id"] is None, "initial_roster_context")
    require(
        not any(
            e["seq"] < init["seq"] and e["type"].startswith("action.") for e in events
        ),
        "action_before_roster",
    )
    rows = init["payload"]["jobs"]
    roster = {r["job_id"]: r for r in rows}
    require(
        len(roster) == len(rows) and len({r["freight_id"] for r in rows}) == len(rows),
        "duplicate_job_identity",
    )
    done, used_actions = {}, set()
    for event in completions:
        row = event["payload"]
        jid, aid = row["job_id"], row["action_id"]
        require(
            jid in roster and jid not in done and aid not in used_actions,
            "completion_identity",
        )
        require(row["freight_id"] == roster[jid]["freight_id"], "completion_freight")
        require(aid in commits, "completion_without_commit")
        commit = commits[aid]
        require(
            commit["seq"] < event["seq"]
            and commit["turn"] == event["turn"]
            and commit["agent_id"] == event["agent_id"],
            "completion_order",
        )
        require(
            commit["payload"].get("freight_id") == row["freight_id"]
            and commit["payload"].get("new_state") == "delivered",
            "completion_transition",
        )
        require(
            event["turn"] >= roster[jid]["release_turn"], "completion_before_release"
        )
        done[jid] = event
        used_actions.add(aid)
    delivered_commits = {
        aid
        for aid, e in commits.items()
        if e["payload"].get("new_state") == "delivered"
    }
    if terminal is not None:
        require(delivered_commits == used_actions, "unreconciled_delivered_commit")
    if terminal is None:
        return unavailable("incomplete_episode"), unavailable("incomplete_episode")
    end = terminal["payload"]
    require(
        terminal["turn"] == horizon
        and terminal["agent_id"] is None
        and end.get("termination") == "completed"
        and type(end.get("horizon_turns")) is int
        and end["horizon_turns"] == horizon,
        "terminal_context",
    )
    turns = [e["turn"] for e in events if e["type"] == "turn.begin"]
    require(turns == list(range(1, horizon + 1)), "turn_coverage")
    require("jobs" in end, "missing_terminal_roster")
    final = {r["job_id"]: r for r in end["jobs"]}
    require(
        len(final) == len(end["jobs"]) and set(final) == set(roster),
        "terminal_roster_identity",
    )
    for jid, row in final.items():
        require(row["freight_id"] == roster[jid]["freight_id"], "terminal_freight")
        require(
            (row["state"] == "delivered") == (jid in done),
            "terminal_completion_mismatch",
        )
    count, total = len(done), len(roster)
    primary = {
        "status": "available" if total else "undefined",
        "numerator": count,
        "denominator": total,
        "value": count / total if total else None,
        "sequences": [init["seq"], *[e["seq"] for e in done.values()], terminal["seq"]],
    }
    interventions = [
        e
        for e in events
        if e["type"] == "disturbance.applied"
        and e["payload"].get("kind") == "peer-mute"
    ]
    schedule = p.get("disturbance_schedule", {})
    require(isinstance(schedule, dict), "invalid_disturbance_configuration")
    expected = schedule.get("peer-mute", {})
    require(isinstance(expected, dict), "invalid_disturbance_configuration")
    if (
        horizon < 8
        or len(interventions) != 1
        or expected.get("turn") != 8
        or expected.get("agent") != "c"
    ):
        return primary, unavailable("intervention_not_established")
    intervention = interventions[0]
    if (
        intervention["turn"] != 8
        or intervention["payload"].get("detail", {}).get("agent") != "c"
    ):
        return primary, unavailable("intervention_not_established")
    if any(
        e["turn"] == 8
        and e["type"] in ("action.proposed", "job.completed")
        and e["seq"] < intervention["seq"]
        for e in events
    ):
        return primary, unavailable("intervention_not_at_start")
    after = [e for e in done.values() if e["turn"] >= 8]
    if not after:
        return primary, {
            "status": "right_censored",
            "value": None,
            "observed_through_turn": horizon,
            "follow_up_turns": horizon - 8,
            "sequences": [intervention["seq"], terminal["seq"]],
        }
    first = min(e["turn"] for e in after)
    witnesses = [e for e in after if e["turn"] == first]
    return primary, {
        "status": "available",
        "value": first - 8,
        "completion_turn": first,
        "job_ids": sorted(e["payload"]["job_id"] for e in witnesses),
        "sequences": [intervention["seq"], *[e["seq"] for e in witnesses]],
    }


def analyze_bytes(raw):
    """Return validated measurements or a categorical invalid result.

    Args:
        raw: Original episode bytes, never normalized before hashing.

    Returns:
        A JSON-compatible result with provenance and explicit measure statuses.
    """
    result = {"analysis_version": 1, "sha256": hashlib.sha256(raw).hexdigest()}
    try:
        events, config = _load(raw)
        commits, actions, traffic = _identities(events)
        completion, resumption = _jobs(events, config, commits)
        p = config["payload"]
        result.update(
            status="valid",
            run_id=config["run_id"],
            event_count=len(events),
            schema="swarmachines/events/v1",
            evidence_version=p.get("job_evidence_version"),
            policy=p.get("policy"),
            topology=p.get("comm_topology"),
            seed=p.get("seed"),
            horizon=p.get("horizon_turns"),
            completion=completion,
            resumption=resumption,
            actions=actions,
            traffic=traffic,
            provider_usage=unavailable("no_usage_manifest"),
            failures=unavailable("no_execution_manifest"),
            fallbacks=unavailable("no_fallback_telemetry"),
        )
    except EvidenceError as error:
        result.update(status="invalid", reason=str(error))
    except (
        UnicodeError,
        json.JSONDecodeError,
        jsonschema.ValidationError,
        TypeError,
        KeyError,
        RecursionError,
        ValueError,
    ):
        result.update(status="invalid", reason="malformed_evidence")
    return result


def main(argv=None):
    """Read bounded input and exclusively create a private result artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        descriptor = os.open(args.episode, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("regular input required")
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("input limit exceeded")
        result = analyze_bytes(raw)
        with os.fdopen(
            os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w"
        ) as stream:
            json.dump(result, stream, ensure_ascii=True, allow_nan=False, indent=2)
            stream.write("\n")
        print(json.dumps({"status": result["status"], "sha256": result["sha256"]}))
        return 1 if result["status"] == "invalid" else 0
    except (OSError, ValueError):
        print('{"status":"blocked","reason":"input_or_output_unavailable"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
