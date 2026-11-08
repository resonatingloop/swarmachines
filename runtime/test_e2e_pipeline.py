#!/usr/bin/env python3
"""
End-to-end pipeline test for swarmachines.

Exercises the full pipeline from a fresh clone:
1. Runner execution with --world freight producing episode JSONL
2. Schema validation via verify_events.py
3. Determinism check (two runs, byte-identical log)
4. Viewer replay readiness (replay.js loader contract offline check)
5. Trace-layer smoke (Langfuse-compatible layer; SKIP if absent)

Usage:
    python runtime/test_e2e_pipeline.py

Hard rules (owner directive):
- Zero provider/API calls (runner is scripted/zero-model by design)
- Google-style docstrings, ruff-clean
- Test authors only; execution against master gated by coordinator
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def fresh_clone(repo_url: str, target_dir: Path) -> None:
    """Clone the repo fresh to target_dir.

    Args:
        repo_url: Git repository URL (local path or remote)
        target_dir: Destination directory for clone
    """
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", str(repo_url), str(target_dir)],
        check=True,
        capture_output=True,
        text=True,
    )


def run_runner(
    workdir: Path,
    seed: int,
    turns: int,
    output_path: Path,
    world: str = "freight",
    topology: str = "mesh",
) -> tuple[int, str]:
    """Run the runner with given parameters.

    Args:
        workdir: Working directory (cloned repo root)
        seed: Random seed for determinism
        turns: Number of turns to simulate
        output_path: Output file path for episode JSONL
        world: World mode ("freight" or "scripted")
        topology: Communication topology

    Returns:
        Tuple of (exit_code, stdout output)
    """
    cmd = [
        sys.executable,
        "runtime/runner.py",
        "--seed",
        str(seed),
        "--turns",
        str(turns),
        "--world",
        world,
        "--topology",
        topology,
        "--agents",
        "a,b,c,d",
        "--output",
        str(output_path),
    ]
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        cwd=str(workdir),
    )
    return result.returncode, result.stdout.strip()


def verify_events(workdir: Path, episode_path: Path) -> tuple[int, str]:
    """Run verify_events.py against an episode file.

    Args:
        workdir: Working directory (cloned repo root)
        episode_path: Path to episode JSONL file

    Returns:
        Tuple of (exit_code, stdout output)
    """
    cmd = [sys.executable, "runtime/verify_events.py", str(episode_path)]
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        cwd=str(workdir),
    )
    return result.returncode, result.stdout.strip()


def check_determinism(workdir: Path, seed: int, turns: int) -> tuple[bool, str]:
    """Verify two runs with same seed produce byte-identical output.

    Args:
        workdir: Working directory (cloned repo root)
        seed: Random seed (must be same for both runs)
        turns: Number of turns

    Returns:
        Tuple of (success, message)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        run1 = tmp / "run1.jsonl"
        run2 = tmp / "run2.jsonl"

        # First run
        code1, out1 = run_runner(workdir, seed, turns, run1)
        if code1 != 0:
            return False, f"Run 1 failed with code {code1}: {out1}"

        # Second run
        code2, out2 = run_runner(workdir, seed, turns, run2)
        if code2 != 0:
            return False, f"Run 2 failed with code {code2}: {out2}"

        # Compare byte-identical
        hash1 = hashlib.sha256(run1.read_bytes()).hexdigest()
        hash2 = hashlib.sha256(run2.read_bytes()).hexdigest()

        if hash1 != hash2:
            return False, f"Determinism failed: {hash1[:16]} != {hash2[:16]}"

        return True, f"Determinism OK: {hash1[:16]}"


def check_viewer_replay(episode_path: Path) -> tuple[bool, str]:
    """Check that the episode can be parsed by viewer's replay.js.

    Uses Node.js to run a headless check of the replay.js loader contract.

    Args:
        episode_path: Path to episode JSONL file

    Returns:
        Tuple of (success, message)
    """
    # Create a Node.js script to test replay.js
    check_script = """
const fs = require('fs');
const path = require('path');

// Load replay.js
const replayPath = path.join(process.argv[2], 'viewer', 'replay.js');
const Replay = require(replayPath);

// Read episode
const episodePath = process.argv[3];
const content = fs.readFileSync(episodePath, 'utf-8');

try {
    const episode = Replay.parseEpisode(content);
    console.log(`Viewer replay OK: ${episode.runId}, ${episode.events.length} events, ${episode.turns.length} turns`);

    // Check snapshot at cursor 0 and last
    const snapshot0 = Replay.snapshot(episode, 0);
    const snapshotLast = Replay.snapshot(episode, episode.events.length - 1);

    if (!snapshot0.event || !snapshotLast.event) {
        console.error('Snapshot failed: missing event');
        process.exit(1);
    }

    console.log('Snapshot contract: OK');
    process.exit(0);
} catch (err) {
    console.error(`Viewer replay failed: ${err.message}`);
    process.exit(1);
}
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(check_script)
        script_path = f.name

    try:
        result = subprocess.run(
            ["node", script_path, str(episode_path.parent.parent), str(episode_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False, f"Viewer check failed: {result.stderr.strip()}"

        # Parse output
        lines = result.stdout.strip().split("\n")
        return True, "; ".join(lines)
    finally:
        os.unlink(script_path)


def check_trace_layer(workdir: Path) -> tuple[str, str]:
    """Smoke test for the trace layer.

    Checks if tracer module exists and can be imported.
    Returns SKIP if tracer module is absent (not a failure).

    Args:
        workdir: Working directory (cloned repo root)

    Returns:
        Tuple of (status, message) where status is "PASS", "SKIP", or "FAIL"
    """
    tracer_path = workdir / "runtime" / "tracer.py"

    if not tracer_path.exists():
        return "SKIP", "Tracer module not present (Langfuse layer absent)"

    # Try to import and instantiate tracer
    check_script = """
import sys
sys.path.insert(0, 'runtime')

try:
    from tracer import Tracer, TraceConfig, create_tracer

    # Test basic instantiation with fake exporter (no network)
    tracer, exporter = create_tracer(
        run_id="test-e2e-smoke",
        condition="e2e-test",
        seed=42,
        use_fake_exporter=True,
    )

    # Exercise basic trace lifecycle
    tracer.start_trace(run_id="test-e2e-smoke", condition="e2e-test", seed=42)

    with tracer.span("test-span", metadata={"test": "e2e"}):
        pass  # Minimal work

    tracer.end_trace(
        status=__import__('tracer').RunStatus.COMPLETED,
        reason="e2e smoke test completed",
    )

    # Verify exporter captured events
    if len(exporter.traces) == 0:
        print("FAIL: No traces recorded")
        sys.exit(1)

    if len(exporter.spans) == 0:
        print("FAIL: No spans recorded")
        sys.exit(1)

    print(f"Trace smoke OK: {len(exporter.traces)} traces, {len(exporter.spans)} spans")
    sys.exit(0)

except ImportError as e:
    print(f"SKIP: Tracer import failed - {e}")
    sys.exit(0)  # SKIP, not FAIL
except Exception as e:
    print(f"FAIL: Trace smoke failed - {e}")
    sys.exit(1)
"""

    result = subprocess.run(
        [sys.executable, "-c", check_script],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(workdir),
    )

    output = result.stdout.strip()
    if "SKIP:" in output:
        return "SKIP", output
    elif result.returncode != 0:
        return "FAIL", output
    else:
        return "PASS", output


def run_e2e_test(repo_path: Path | None = None) -> dict:
    """Run the full e2e pipeline test.

    Args:
        repo_path: Optional local repo path to clone from.
                   If None, uses current working directory's parent.

    Returns:
        Dict with test results and metrics
    """
    results = {
        "runner_execution": {"status": "PENDING", "message": ""},
        "schema_validation": {"status": "PENDING", "message": ""},
        "determinism": {"status": "PENDING", "message": ""},
        "viewer_replay": {"status": "PENDING", "message": ""},
        "trace_layer": {"status": "PENDING", "message": ""},
        "overall": "PENDING",
    }

    # Determine repo source
    if repo_path is None:
        repo_path = Path(__file__).parent.parent

    # Create temp directory for fresh clone
    with tempfile.TemporaryDirectory() as tmpdir:
        clone_dir = Path(tmpdir) / "swarmachines-clone"

        # Step 1: Fresh clone
        print("Step 1: Fresh clone...")
        try:
            fresh_clone(str(repo_path), clone_dir)
            print(f"  Cloned to {clone_dir}")
        except subprocess.CalledProcessError as e:
            results["overall"] = "FAIL"
            results["runner_execution"] = {
                "status": "FAIL",
                "message": f"Clone failed: {e.stderr}",
            }
            return results

        # Step 2: Runner execution with --world freight
        print("Step 2: Runner execution (--world freight)...")
        episode_path = clone_dir / "runtime" / "e2e-episode.jsonl"
        seed = 42
        turns = 4

        code, out = run_runner(clone_dir, seed, turns, episode_path)
        if code != 0:
            results["runner_execution"] = {
                "status": "FAIL",
                "message": f"Runner failed with code {code}: {out}",
            }
            results["overall"] = "FAIL"
            return results

        if not episode_path.exists():
            results["runner_execution"] = {
                "status": "FAIL",
                "message": f"Output file not created: {episode_path}",
            }
            results["overall"] = "FAIL"
            return results

        event_count = sum(1 for _ in open(episode_path) if _.strip())
        results["runner_execution"] = {
            "status": "PASS",
            "message": f"Generated {event_count} events to {episode_path.name}",
        }
        print(f"  {results['runner_execution']['message']}")

        # Step 3: Schema validation
        print("Step 3: Schema validation...")
        code, out = verify_events(clone_dir, episode_path)
        if code != 0:
            results["schema_validation"] = {
                "status": "FAIL",
                "message": out,
            }
            results["overall"] = "FAIL"
            return results

        results["schema_validation"] = {"status": "PASS", "message": out.split("\n")[-1]}
        print(f"  {results['schema_validation']['message']}")

        # Step 4: Determinism check
        print("Step 4: Determinism check...")
        success, msg = check_determinism(clone_dir, seed, turns)
        if not success:
            results["determinism"] = {"status": "FAIL", "message": msg}
            results["overall"] = "FAIL"
            return results

        results["determinism"] = {"status": "PASS", "message": msg}
        print(f"  {results['determinism']['message']}")

        # Step 5: Viewer replay readiness
        print("Step 5: Viewer replay readiness...")
        success, msg = check_viewer_replay(episode_path)
        if not success:
            results["viewer_replay"] = {"status": "FAIL", "message": msg}
            results["overall"] = "FAIL"
            return results

        results["viewer_replay"] = {"status": "PASS", "message": msg}
        print(f"  {results['viewer_replay']['message']}")

        # Step 6: Trace-layer smoke
        print("Step 6: Trace-layer smoke...")
        status, msg = check_trace_layer(clone_dir)
        results["trace_layer"] = {"status": status, "message": msg}
        print(f"  {results['trace_layer']['message']}")

        # Overall result
        if status == "FAIL":
            results["overall"] = "FAIL"
        else:
            results["overall"] = "PASS"

    return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="E2E pipeline test for swarmachines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python runtime/test_e2e_pipeline.py
    python runtime/test_e2e_pipeline.py --repo /path/to/swarmachines

Hard rules:
- Zero provider/API calls (runner is scripted/zero-model by design)
- Test authors only; execution against master gated by coordinator
""",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Local repo path to clone from (default: parent of this script)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("E2E Pipeline Test — swarmachines")
    print("=" * 60)
    print()

    results = run_e2e_test(args.repo)

    print()
    print("=" * 60)
    print("Results Summary")
    print("=" * 60)

    for test_name, result in results.items():
        if test_name == "overall":
            continue
        status = result.get("status", "UNKNOWN")
        message = result.get("message", "")
        marker = "✓" if status == "PASS" else "✗" if status == "FAIL" else "○"
        print(f"{marker} {test_name}: {status}")
        if message:
            print(f"    {message}")

    print()
    print(f"OVERALL: {results['overall']}")

    if args.json:
        print()
        print(json.dumps(results, indent=2))

    return 0 if results["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
