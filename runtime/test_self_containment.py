"""Self-containment guarantees for episode logs.

Every message.sent event must carry its full body inline — no pointer
chasing into an external store that may never have been written. The log
is the complete record: schema-valid, seal-valid, and deterministic.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _run_episode(seed: str, output: str) -> list:
    """Run one episode and return its validated events."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "runtime.runner",
            "--seed",
            seed,
            "--turns",
            "4",
            "--world",
            "freight",
            "--disturbance",
            "peer-mute:3:c",
            "--output",
            output,
        ],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
        check=False,
    )
    assert result.returncode == 0, f"runner failed: {result.stdout}{result.stderr}"
    return [
        json.loads(line)
        for line in Path(output).read_text().splitlines()
        if line.strip()
    ]


def test_message_bodies_are_inline():
    """Every message.sent carries a non-empty body object; no body_ref remains."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name
    try:
        events = _run_episode("42", output)
        sent = [e for e in events if e["type"] == "message.sent"]
        assert sent, "no message.sent events in episode"
        for event in sent:
            payload = event["payload"]
            assert "body_ref" not in payload, (
                f"{payload['message_id']} still passes by reference"
            )
            body = payload.get("body")
            assert isinstance(body, dict) and body, (
                f"{payload['message_id']} has no inline body"
            )
        # The log alone reconstructs the full message content.
        bodies = {e["payload"]["message_id"]: e["payload"]["body"] for e in sent}
        assert len(bodies) == len(sent), "duplicate message ids"
    finally:
        Path(output).unlink()


def test_episode_log_is_self_contained_and_seal_valid():
    """Bodies inline, seal verifies, and tampering an inline body breaks the seal."""
    from runner import verify_seal

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        output = f.name
    try:
        events = _run_episode("7", output)
        verify_seal(events)

        # Tamper with one inline body: the seal must catch it.
        for event in events:
            if event["type"] == "message.sent":
                event["payload"]["body"]["content"] = "fabricated"
                break
        try:
            verify_seal(events)
            raise AssertionError("tampered inline body was not detected")
        except ValueError as exc:
            assert "chain_mismatch" in str(exc), f"unexpected seal error: {exc}"
    finally:
        Path(output).unlink()


def test_determinism_with_inline_bodies():
    """Same seed and config still produce byte-identical self-contained logs."""
    with (
        tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as a,
        tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as b,
    ):
        out_a, out_b = a.name, b.name
    try:
        _run_episode("42", out_a)
        _run_episode("42", out_b)
        assert Path(out_a).read_bytes() == Path(out_b).read_bytes(), (
            "inline bodies broke replay determinism"
        )
    finally:
        Path(out_a).unlink()
        Path(out_b).unlink()
