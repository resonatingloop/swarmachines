"""Bounded, read-only projection of private local worker evidence."""

import hashlib
import json
import os
import re
import sqlite3
import stat
import time
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

if __package__:
    from .limits import DEFAULT, validate_limits
else:
    from limits import DEFAULT, validate_limits

MAX_JOBS = 1000
MAX_FIELD = 96 * 1024
MAX_SCAN = 8 * 1024 * 1024
MODEL = "glm-53-flash"
# Reviewed producer source fingerprints: 61b8ae1 and 8abecd4. These identify
# compatible configuration, not authenticity or immutable historical limits.
PRODUCERS = {
    "a860c8e65b1add160e8210f4f8fd53d85dff8e49860a1d92e740cb30cb09b2f0",  # spec010: persisted session policy
    "aac56334783a7c7f230dfec5a9c7955375073f9008fb9fdee2f81f4492eaaf62",
    "47553b9faf78c0de5b491376abc5248cc18e4542bc430334f7ac667de3465175",
    "3cf60e688de7dbc2fda858b59fb1ab6994a134c391c5d991a82065ab8a01e567",  # sanitized model/usage receipts
}
COLUMNS = {
    "budget": ["id", "requests", "reserved_micro"],
    "jobs": [
        "task_id",
        "attempt_id",
        "packet_hash",
        "packet",
        "worker",
        "mode",
        "state",
        "claim_token",
        "ack",
        "receipt",
    ],
}


def integer(value, maximum=10**9):
    """Return a bounded integer or unknown, excluding bools."""
    return value if type(value) is int and 0 <= value <= maximum else None


def matched(value, pattern):
    """Validate a bounded scalar without coercing arbitrary objects."""
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def stamp(value):
    """Return a bounded timezone-aware timestamp, otherwise unknown."""
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        date = datetime.fromisoformat(value)
        return value if date.utcoffset() is not None else None
    except ValueError:
        return None


def sha(text):
    """Hash exact UTF-8 bytes without inferring correctness."""
    return hashlib.sha256(text.encode()).hexdigest()


def project(row, policy=None, binding=None):
    """Validate matching evidence, returning only the approved projection.

    Args:
        row: A bounded database row; private content never escapes this function.

    Returns:
        A projected attempt and whether its producer configuration is known.

    Raises:
        ValueError: Evidence is malformed, contradictory or oversized.
    """
    packet, ack = json.loads(row["packet"]), json.loads(row["ack"])
    if not isinstance(packet, dict) or not isinstance(ack, dict):
        raise TypeError("invalid envelope")
    keys = {
        "task_id": row["task_id"],
        "attempt_id": row["attempt_id"],
        "worker": row["worker"],
        "mode": row["mode"],
        "packet_hash": row["packet_hash"],
    }
    for key in ("task_id", "attempt_id", "worker"):
        if not matched(keys[key], r"[a-zA-Z0-9_.-]{1,80}"):
            raise ValueError("invalid identity")
    if keys["mode"] not in ("offline", "adaption") or row["state"] not in (
        "running",
        "completed",
        "failed",
    ):
        raise ValueError("invalid mode/state")
    if packet.get("schema_version") != "v1" or ack.get("schema_version") != "v1":
        raise ValueError("unsupported envelope")
    if any(ack.get(key) != value for key, value in keys.items()):
        raise ValueError("ack mismatch")
    if (
        packet.get("task_id") != keys["task_id"]
        or packet.get("attempt_id") != keys["attempt_id"]
        or packet.get("assigned_worker") != keys["worker"]
    ):
        raise ValueError("packet mismatch")
    canonical = json.dumps(
        packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    if sha(canonical) != keys["packet_hash"]:
        raise ValueError("packet hash mismatch")
    source = packet.get("source", {})
    if not isinstance(source, dict):
        raise TypeError("invalid source")
    revision = source.get("revision")
    result = {
        **keys,
        "state": row["state"],
        "acknowledged_at": stamp(ack.get("acknowledged_at")),
        "finished_at": None,
        "source_revision": revision if matched(revision, r"[a-f0-9]{40}") else None,
        "result_hash": None,
        "model": "unknown",
        "input_tokens": None,
        "output_tokens": None,
        "estimated_credits": None,
        "error_code": None,
        "response_status": None,
    }
    known = ack.get("harness_sha256") in PRODUCERS
    if policy is not None and (
        ack.get("budget_policy") != policy or ack.get("session_sha256") != binding
    ):
        raise ValueError("ack policy mismatch")
    if row["state"] == "running":
        if row["receipt"] is not None:
            raise ValueError("running with receipt")
        return result, known
    receipt = json.loads(row["receipt"])
    if not isinstance(receipt, dict) or any(
        receipt.get(key) != value for key, value in keys.items()
    ):
        raise ValueError("receipt mismatch")
    if (
        receipt.get("schema_version") != "v1"
        or receipt.get("state") != row["state"]
        or receipt.get("outcome") != row["state"]
        or receipt.get("harness_sha256") != ack.get("harness_sha256")
    ):
        raise ValueError("receipt state mismatch")
    if policy is not None and (
        receipt.get("budget_policy") != policy
        or receipt.get("session_sha256") != binding
    ):
        raise ValueError("receipt policy mismatch")
    result["finished_at"] = stamp(receipt.get("finished_at"))
    output = receipt.get("result")
    if row["state"] == "completed":
        if (
            not isinstance(output, dict)
            or not isinstance(output.get("text"), str)
            or receipt.get("error")
        ):
            raise ValueError("invalid completed receipt")
        if sha(output["text"]) != receipt.get("result_sha256"):
            raise ValueError("result hash mismatch")
        result["result_hash"] = receipt["result_sha256"]
        result["model"] = MODEL if output.get("model") == MODEL else "unknown"
    elif output is not None or receipt.get("result_sha256") is not None:
        raise ValueError("failed with result")
    elif known and keys["mode"] == "adaption":
        result["model"] = (
            MODEL  # fixed model from recognized producer, not provider text
        )
    usage = receipt.get("usage")
    if isinstance(usage, dict):
        for key in ("input_tokens", "output_tokens"):
            result[key] = integer(usage.get(key))
    error = receipt.get("error")
    if isinstance(error, dict):
        code = error.get("code")
        result["error_code"] = (
            code
            if code in ("response_not_completed", "invalid_output_text")
            else "unknown"
        )
        diagnostics = error.get("diagnostics")
        status = diagnostics.get("status") if isinstance(diagnostics, dict) else None
        result["response_status"] = (
            status
            if status
            in (
                "completed",
                "incomplete",
                "failed",
                "cancelled",
                "queued",
                "in_progress",
            )
            else "unknown"
        )
    if (
        keys["mode"] == "adaption"
        and result["model"] == MODEL
        and result["input_tokens"] is not None
        and result["output_tokens"] is not None
    ):
        estimate = (
            Decimal(result["input_tokens"]) * Decimal("0.15")
            + Decimal(result["output_tokens"]) * Decimal("0.50")
        ) / Decimal(1_000_000)
        result["estimated_credits"] = format(estimate, "f")
    return result, known


def inspect_path(directory):
    """Require private owned files, no symlink ancestors, and rollback journal mode."""
    directory = Path(os.path.abspath(directory))
    path = directory / "queue.sqlite3"
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("symlink refused")
    for item, expected in ((directory, stat.S_ISDIR), (path, stat.S_ISREG)):
        info = item.stat()
        if (
            not expected(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
        ):
            raise ValueError("private source required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        header = os.read(fd, 100)
    finally:
        os.close(fd)
    if (
        len(header) != 100
        or header[:16] != b"SQLite format 3\x00"
        or header[18:20] != b"\x01\x01"
    ):
        raise ValueError("unsupported journal mode")
    if any(
        Path(str(path) + suffix).exists() for suffix in ("-wal", "-shm", "-journal")
    ):
        raise ValueError("active journal unavailable")
    return path


def collect_workers(directory=None):
    """Capture an optional private source without creating or repairing state."""
    view = {
        "status": "not supplied",
        "read_at": datetime.now(UTC).isoformat(),
        "source": "local worker queue",
        "schema": "delegation v1",
        "attempts": [],
        "diagnostics": [],
        "budget": None,
        "accounting": None,
    }
    if directory is None:
        return view
    db = None
    try:
        path = inspect_path(directory)
        db = sqlite3.connect(
            path.as_uri() + "?mode=ro", uri=True, timeout=0.1, isolation_level=None
        )
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        end = time.monotonic() + 2
        db.set_progress_handler(lambda: int(time.monotonic() > end), 1000)
        db.execute("BEGIN")
        objects = db.execute(
            "SELECT name,type FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        ).fetchall()
        if {(r["name"], r["type"]) for r in objects} != {
            ("jobs", "table"),
            ("budget", "table"),
        }:
            raise ValueError("unexpected schema")
        stored_policy = False
        for table, columns in COLUMNS.items():
            actual = [r["name"] for r in db.execute(f"PRAGMA table_info({table})")]
            if table == "budget" and actual == columns + ["policy", "binding"]:
                stored_policy = True
            elif actual != columns:
                raise ValueError("unexpected columns")
        policy = dict(DEFAULT)
        binding = None
        if stored_policy:
            raw_policy = db.execute(
                "SELECT CASE WHEN length(CAST(policy AS BLOB))<=1024 THEN policy ELSE NULL END FROM budget WHERE id=1"
            ).fetchone()
            if raw_policy is None or raw_policy[0] is None:
                raise ValueError("policy unavailable")
            policy = validate_limits(json.loads(raw_policy[0]))
            binding = db.execute(
                "SELECT CASE WHEN length(binding)<=64 THEN binding ELSE NULL END FROM budget WHERE id=1"
            ).fetchone()[0]
            if binding != "" and not matched(binding, r"[a-f0-9]{64}"):
                raise ValueError("invalid session binding")
        budget = db.execute(
            "SELECT id,requests,reserved_micro FROM budget LIMIT 2"
        ).fetchall()
        if len(budget) != 1 or budget[0]["id"] != 1:
            raise ValueError("invalid budget")
        used = integer(budget[0]["requests"])
        reserved = integer(budget[0]["reserved_micro"], 10**12)
        if used is None or reserved is None:
            raise ValueError("invalid budget values")
        # Metadata first: never allocate an unbounded packet/receipt from SQLite.
        rows = db.execute(
            """SELECT rowid AS ordinal,
            length(CAST(packet AS BLOB)) AS p, length(CAST(ack AS BLOB)) AS a,
            length(CAST(receipt AS BLOB)) AS r,
            length(CAST(task_id AS BLOB))+length(CAST(attempt_id AS BLOB))+
            length(CAST(worker AS BLOB))+length(CAST(mode AS BLOB))+
            length(CAST(state AS BLOB))+length(CAST(packet_hash AS BLOB)) AS metadata FROM jobs ORDER BY rowid LIMIT ?""",
            (MAX_JOBS + 1,),
        ).fetchall()
        truncated, total, known = len(rows) > MAX_JOBS, 0, True
        attempts = []
        for meta in rows[:MAX_JOBS]:
            if time.monotonic() > end:
                raise ValueError("worker read deadline exceeded")
            sizes = [meta[k] or 0 for k in ("p", "a", "r", "metadata")]
            if any(n > MAX_FIELD for n in sizes):
                view["diagnostics"].append("invalid oversized worker row; excluded")
                known = False
                continue
            total += sum(sizes)
            if total > MAX_SCAN:
                truncated = True
                break
            row = db.execute(
                "SELECT task_id,attempt_id,packet_hash,packet,worker,mode,state,ack,receipt FROM jobs WHERE rowid=?",
                (meta["ordinal"],),
            ).fetchone()
            try:
                attempt, compatible = project(
                    row, policy if stored_policy else None, binding
                )
                attempts.append(attempt)
                known = known and compatible
            except (ValueError, TypeError, KeyError, RecursionError):
                view["diagnostics"].append("invalid worker evidence; excluded")
                known = False
        counts = Counter(a["task_id"] for a in attempts)
        ids = Counter(a["attempt_id"] for a in attempts)
        duplicate = any(n > 1 for n in (*counts.values(), *ids.values()))
        if duplicate:
            attempts = [
                a for a in attempts if counts[a["task_id"]] == ids[a["attempt_id"]] == 1
            ]
            view["diagnostics"].append("duplicate identities; excluded")
        known = (
            known
            and (bool(attempts) or stored_policy)
            and not truncated
            and not duplicate
        )
        live = [a for a in attempts if a["mode"] == "adaption"]
        if not truncated and used != len(live):
            view["diagnostics"].append(
                "budget request count differs from valid live rows"
            )
            known = False
        if known and (
            reserved != used * policy["reservation_micro"]
            or used > policy["request_limit"]
            or reserved > policy["credit_limit_micro"]
        ):
            view["diagnostics"].append(
                "budget differs from recognized producer configuration"
            )
            known = False
        estimates = [
            Decimal(a["estimated_credits"])
            for a in live
            if a["estimated_credits"] is not None
        ]
        view.update(
            status="truncated" if truncated else "available",
            attempts=attempts,
            budget={
                "requests_used": used,
                "reserved_credits": format(Decimal(reserved) / 1000000, "f"),
                "request_limit": policy["request_limit"] if known else None,
                "reservation_ceiling": format(
                    Decimal(policy["credit_limit_micro"]) / 1000000, "f"
                )
                if known
                else None,
                "requests_remaining": max(0, policy["request_limit"] - used)
                if known
                else None,
                "limit_basis": "recognized producer configuration; not account quota"
                if known
                else "unknown",
            },
            accounting={
                "live_attempts": len(live),
                "known_usage_attempts": len(estimates),
                "unknown_usage_attempts": len(live) - len(estimates),
                "estimated_subtotal": format(sum(estimates, Decimal(0)), "f"),
                "coverage": "partial / lower bounds"
                if truncated or view["diagnostics"]
                else "returned collection",
                "rate_basis": "2026-11-07 glm-53-flash: 0.15 input / 0.50 output credits per million tokens",
                "actual_billed_spend": "unknown",
            },
        )
        return view
    except (OSError, sqlite3.Error, ValueError, TypeError):
        view.update(
            status="unavailable",
            attempts=[],
            budget=None,
            accounting=None,
            diagnostics=["worker source unavailable; no repair attempted"],
        )
        return view
    finally:
        if db is not None:
            db.close()
