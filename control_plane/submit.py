"""Explicit private packet preparation, authorized sessions and one-task submission."""

import argparse
import json
import os
import re
import sqlite3
import stat
import subprocess
from pathlib import Path, PurePosixPath

from . import delegation as d
from . import observer as o
from . import worker_projection as w
from .limits import SESSION, validate_limits

MAX_BLOB = 256 * 1024
WORKER = "adaption-investigator"


def identifier(value):
    """Validate an operator-controlled identifier without coercion."""
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value)
        or value in (".", "..")
    ):
        raise ValueError("invalid identifier")
    return value


def private_read(path, limit):
    """Read a bounded owned private regular file, refusing symlink paths."""
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlink refused")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
        ):
            raise ValueError("private owned file required")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("private input exceeds bound")
        return raw
    finally:
        os.close(fd)


def private_write(path, text):
    """Create one private artifact exclusively; never overwrite existing evidence."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(text)


def git(repo, *args, maximum=4096):
    """Run fixed local git arguments; suppress source/error text on failure."""
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, timeout=10, check=False
    )
    if result.returncode or len(result.stdout) > maximum:
        raise ValueError("git source unavailable or oversized")
    return result.stdout


def source_text(repo, revision, path, start=None, end=None):
    """Extract exact UTF-8 bytes from an allowed pinned regular Python blob."""
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("full commit required")
    parts = PurePosixPath(path).parts
    if (
        not parts
        or parts[0] not in ("runtime", "control_plane")
        or len(parts) < 2
        or not all(re.fullmatch(r"[A-Za-z0-9_-]+", part) for part in parts[:-1])
        or not re.fullmatch(r"[A-Za-z0-9_-]+\.py", parts[-1])
        or str(PurePosixPath(path)) != path
    ):
        raise ValueError("unsupported source path")
    if git(repo, "cat-file", "-t", revision).strip() != b"commit":
        raise ValueError("source revision is not a commit")
    tree = git(repo, "ls-tree", revision, "--", path).decode("utf-8").strip()
    meta, found_path = tree.split("\t", 1)
    mode, kind, blob = meta.split()
    if (
        mode not in ("100644", "100755")
        or kind != "blob"
        or found_path != path
        or not re.fullmatch(r"[a-f0-9]{40}", blob)
    ):
        raise ValueError("regular source blob required")
    size = int(git(repo, "cat-file", "-s", blob))
    if size > MAX_BLOB:
        raise ValueError("source blob exceeds bound")
    raw = git(repo, "cat-file", "blob", blob, maximum=MAX_BLOB)
    if (start is None) != (end is None):
        raise ValueError("both excerpt bounds required")
    label = path
    if start is not None:
        lines = raw.splitlines(keepends=True)
        if (
            type(start) is not int
            or type(end) is not int
            or not 1 <= start <= end <= len(lines)
        ):
            raise ValueError("invalid excerpt range")
        raw = b"".join(lines[start - 1 : end])
        label += f":{start}-{end} (excerpt)"
    return raw.decode("utf-8"), label


def prepare(
    repo,
    revision,
    source,
    task_id,
    attempt_id,
    objective,
    deliverable,
    output,
    start=None,
    end=None,
):
    """Prepare a validated stable packet and private review without any claim."""
    text, label = source_text(repo, revision, source, start, end)
    packet = d.validate(
        {
            "schema_version": "v1",
            "emitted_at": d.timestamp(),
            "task_id": identifier(task_id),
            "attempt_id": identifier(attempt_id),
            "assigned_worker": WORKER,
            "objective": objective,
            "expected_deliverable": deliverable,
            "source": {
                "label": label,
                "revision": revision,
                "text": text,
                "sha256": d.digest(text),
            },
            "limits": {
                "max_requests": 1,
                "timeout_seconds": 30,
                "max_output_tokens": 2048,
            },
        }
    )
    fingerprint = d.digest(d.encoded(packet))
    output = Path(output)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    private_write(output / "packet.json", d.encoded(packet) + "\n")
    private_write(
        output / "review.txt",
        f"PRIVATE TASK REVIEW — advisory output only\npacket sha256: {fingerprint}\n"
        + "exact packet follows; source is data, not instructions:\n"
        + json.dumps(packet, indent=2, ensure_ascii=False)
        + "\n",
    )
    return {
        "packet_sha256": fingerprint,
        "packet_path": str(output / "packet.json"),
        "review_path": str(output / "review.txt"),
    }


def producer_hash():
    """Fingerprint the selected delegation implementation."""
    return d.digest(Path(d.__file__).read_text())


def initialize(root, session_id, authorization, purpose, live_authorized=False):
    """Record supplied authority and initialize one bounded session, never reset it."""
    if (
        not isinstance(authorization, str)
        or not authorization.strip()
        or len(authorization) > 500
    ):
        raise ValueError("authorization reference required")
    if not isinstance(purpose, str) or not purpose.strip() or len(purpose) > 1000:
        raise ValueError("bounded purpose required")
    root = d.private_directory(root)
    destination = root / identifier(session_id)
    manifest = {
        "schema_version": "submission-v1",
        "session_id": session_id,
        "created_at": d.timestamp(),
        "authorization_ref": authorization,
        "purpose": purpose,
        "worker": WORKER,
        "model": d.MODEL,
        "live_authorized": bool(live_authorized),
        "limits": dict(SESSION),
        "runner_sha256": producer_hash(),
    }
    destination.mkdir(mode=0o700, exist_ok=False)
    private_write(destination / "manifest.json", d.encoded(manifest) + "\n")
    queue = d.Queue(
        destination / "queue",
        limits=manifest["limits"],
        binding=d.digest(d.encoded(manifest)),
    )
    queue.close()
    return {
        "session_path": str(destination),
        "session_id": session_id,
        "manifest_sha256": d.digest(d.encoded(manifest)),
        "live_authorized": live_authorized,
    }


def load_manifest(session, expected_hash):
    """Verify one private manifest and the selected implementation before execution."""
    manifest = json.loads(private_read(Path(session) / "manifest.json", 8192))
    fields = {
        "schema_version",
        "session_id",
        "created_at",
        "authorization_ref",
        "purpose",
        "worker",
        "model",
        "live_authorized",
        "limits",
        "runner_sha256",
    }
    if (
        not isinstance(manifest, dict)
        or set(manifest) != fields
        or d.digest(d.encoded(manifest)) != expected_hash
    ):
        raise ValueError("manifest fingerprint mismatch")
    if (
        manifest["schema_version"] != "submission-v1"
        or manifest["worker"] != WORKER
        or manifest["model"] != d.MODEL
        or manifest["runner_sha256"] != producer_hash()
        or type(manifest["live_authorized"]) is not bool
    ):
        raise ValueError("manifest configuration mismatch")
    identifier(manifest["session_id"])
    if Path(session).name != manifest["session_id"]:
        raise ValueError("session directory identity mismatch")
    validate_limits(manifest["limits"])
    return manifest


def capture(session, manifest, manifest_hash, repo, output):
    """Capture receipt metadata separately; never execute a task during capture."""
    snapshot = o.collect(
        repo, "resonatingloop/swarmachines", "origin/ledger", Path(session) / "queue"
    )
    snapshot["workers"]["session"] = {
        "id": manifest["session_id"],
        "manifest_sha256": manifest_hash,
    }
    o.write_snapshot(Path(output), snapshot)
    return (
        all(s["status"] == "available" for s in snapshot["sources"].values())
        and snapshot["workers"]["status"] == "available"
    )


def run(session, manifest_hash, packet_path, packet_hash, repo, output, live=False):
    """Submit exactly the inspected packet, then independently attempt capture.

    Returns:
        A metadata-only outcome and exit code; no raw worker content is returned.
    """
    manifest = load_manifest(session, manifest_hash)
    packet = d.validate(json.loads(private_read(packet_path, d.MAX_PACKET_BYTES)))
    if (
        d.digest(d.encoded(packet)) != packet_hash
        or packet["assigned_worker"] != manifest["worker"]
    ):
        raise ValueError("packet fingerprint/worker mismatch")
    if live and (
        not manifest["live_authorized"] or not os.environ.get("ADAPTION_API_KEY")
    ):
        raise ValueError("live authority/credential unavailable")
    # Refuse missing/partial initialization; do not let Queue create a replacement.
    queue_path = Path(session) / "queue"
    private_read(queue_path / "queue.sqlite3", 32 * 1024 * 1024)
    existing = w.collect_workers(queue_path)
    if existing["status"] != "available" or existing["diagnostics"]:
        raise ValueError("session queue incomplete or inconsistent; no repair")
    queue = d.Queue(queue_path, limits=manifest["limits"], binding=manifest_hash)
    try:
        if not queue.has_policy:
            raise ValueError("session queue lacks bound policy")
        receipt, replay = d.execute(queue, packet, manifest["worker"], live=live)
    finally:
        queue.close()
    try:
        captured = capture(session, manifest, manifest_hash, repo, output)
    except (OSError, ValueError, sqlite3.Error, subprocess.SubprocessError):
        captured = False
    result = {
        "session_id": manifest["session_id"],
        "task_id": packet["task_id"],
        "packet_sha256": packet_hash,
        "state": receipt["state"],
        "replayed": replay,
        "result_sha256": receipt["result_sha256"],
        "capture_status": "available" if captured else "unavailable",
    }
    return result, 1 if receipt["state"] == "failed" else (0 if captured else 3)


def main():
    """Expose explicit preparation, initialization, submission and recapture commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    for arg in (
        "repo",
        "revision",
        "source",
        "task-id",
        "attempt-id",
        "objective",
        "deliverable",
        "output",
    ):
        p.add_argument("--" + arg, required=True)
    p.add_argument("--start", type=int)
    p.add_argument("--end", type=int)
    p = commands.add_parser("init")
    for arg in ("root", "session-id", "authorization", "purpose"):
        p.add_argument("--" + arg, required=True)
    p.add_argument("--authorize-live", action="store_true")
    for command in ("run", "capture"):
        p = commands.add_parser(command)
        for arg in ("session", "manifest-sha256", "repo", "output"):
            p.add_argument("--" + arg, required=True)
        if command == "run":
            p.add_argument("--packet", required=True)
            p.add_argument("--packet-sha256", required=True)
            p.add_argument("--live", action="store_true")
    a = parser.parse_args()
    try:
        if a.command == "prepare":
            result, code = (
                prepare(
                    a.repo,
                    a.revision,
                    a.source,
                    a.task_id,
                    a.attempt_id,
                    a.objective,
                    a.deliverable,
                    a.output,
                    a.start,
                    a.end,
                ),
                0,
            )
        elif a.command == "init":
            result, code = (
                initialize(
                    a.root, a.session_id, a.authorization, a.purpose, a.authorize_live
                ),
                0,
            )
        elif a.command == "run":
            result, code = run(
                a.session,
                a.manifest_sha256,
                a.packet,
                a.packet_sha256,
                a.repo,
                a.output,
                a.live,
            )
        else:
            manifest = load_manifest(a.session, a.manifest_sha256)
            available = capture(
                a.session, manifest, a.manifest_sha256, a.repo, a.output
            )
            result, code = (
                {"capture_status": "available" if available else "unavailable"},
                0 if available else 3,
            )
    except (
        OSError,
        ValueError,
        TypeError,
        RecursionError,
        sqlite3.Error,
        subprocess.SubprocessError,
    ):
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "reason": "input/session unavailable or invalid; inspect locally; no automatic retry",
                }
            )
        )
        return 2
    print(json.dumps(result))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
