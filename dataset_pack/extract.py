"""
dataset_pack/extract.py — post-run artifact extraction from persisted logs

Extracts artifacts from the persisted calls.jsonl response fields after run completion.
Content is identical (not paraphrased) to its call's response field.
Each artifact carries one label:
- model-generated: model id + receipt ref
- team-authored: byte-exact from the git commit that held it
- reconstructed-from-log: reconstructed from event log

Provenance rules:
- Artifacts are extracted from RESPONSE fields only (never written prompt-side)
- Content-identity check vs response field
- Labels applied based on provenance metadata
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _sanitize_artifact_id(artifact_id: str, base_dir: Path) -> str:
    """
    Sanitize artifact_id to prevent path traversal attacks.

    Security rules:
    1. Reject absolute paths (starts with /)
    2. Reject '..' path segments (traversal attempt)
    3. Allowlist charset: [A-Za-z0-9_-] only
    4. Resolve full path and assert containment within base_dir

    Args:
        artifact_id: Untrusted artifact identifier from model response
        base_dir: Base directory that must contain the output file

    Returns:
        Sanitized artifact_id (safe to use in path join)

    Raises:
        ValueError: If artifact_id fails security validation
    """
    # Rule 1: Reject absolute paths
    if artifact_id.startswith("/"):
        raise ValueError(f"artifact_id cannot be absolute path: {artifact_id}")

    # Rule 2: Reject '..' path segments
    if ".." in artifact_id:
        raise ValueError(f"artifact_id cannot contain '..': {artifact_id}")

    # Rule 3: Allowlist charset [A-Za-z0-9_-]
    if not re.match(r"^[A-Za-z0-9_-]+$", artifact_id):
        raise ValueError(f"artifact_id contains invalid chars (allowed: A-Za-z0-9_-): {artifact_id}")

    # Rule 4: Resolve and verify containment
    resolved_base = base_dir.resolve()
    candidate_path = (base_dir / artifact_id).resolve()
    try:
        candidate_path.relative_to(resolved_base)
    except ValueError:
        raise ValueError(f"artifact_id would escape base directory: {artifact_id}")

    return artifact_id


@dataclass
class ExtractedArtifact:
    """
    An extracted artifact with provenance metadata.

    Attributes:
        artifact_id: Unique artifact identifier
        source_call_id: Call ID that generated this artifact
        source_receipt_ref: Receipt reference from the call
        content: Artifact content (byte-identical to response field)
        content_hash: SHA256 hash of content
        label: Provenance label
        model_id: Model ID if model-generated
        run_id: Source run ID
        turn: Turn number if applicable
        agent_id: Agent ID if applicable
    """

    artifact_id: str
    source_call_id: str
    source_receipt_ref: str
    content: str
    content_hash: str
    label: str  # "model-generated", "team-authored", "reconstructed-from-log"
    model_id: str | None = None
    run_id: str | None = None
    turn: int | None = None
    agent_id: str | None = None

    def to_metadata_dict(self) -> dict[str, Any]:
        """Convert to metadata dictionary for indexing."""
        return {
            "artifact_id": self.artifact_id,
            "source_call_id": self.source_call_id,
            "source_receipt_ref": self.source_receipt_ref,
            "content_hash": self.content_hash,
            "label": self.label,
            "model_id": self.model_id,
            "run_id": self.run_id,
            "turn": self.turn,
            "agent_id": self.agent_id,
        }


class ArtifactExtractor:
    """
    Extracts artifacts from persisted calls.jsonl logs.

    Attributes:
        calls_jsonl_path: Path to the calls.jsonl file
        artifacts_dir: Directory to write extracted artifacts
    """

    def __init__(
        self,
        calls_jsonl_path: str,
        artifacts_dir: str,
    ):
        self.calls_jsonl_path = Path(calls_jsonl_path)
        self.artifacts_dir = Path(artifacts_dir)
        self.extracted: list[ExtractedArtifact] = []
        self.validation_errors: list[str] = []

    def load_calls(self) -> list[dict[str, Any]]:
        """
        Load call records from calls.jsonl.

        Returns:
            List of call record dictionaries.

        Raises:
            FileNotFoundError: If calls.jsonl does not exist.
            ValueError: If any line is invalid JSON.
        """
        if not self.calls_jsonl_path.exists():
            raise FileNotFoundError(f"calls.jsonl not found at {self.calls_jsonl_path}")

        calls = []
        with open(self.calls_jsonl_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    call = json.loads(line)
                    calls.append(call)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON on line {line_num}: {e}") from e

        return calls

    def _extract_artifact_from_response(
        self,
        call: dict[str, Any],
        response_field: str = "response_full",
    ) -> tuple[str | None, str | None]:
        """
        Extract artifact content from a call's response field.

        Looks for artifact markers in the response:
        - ARTIFACT: <artifact_id> ... END_ARTIFACT
        - Or uses the full response if no markers present

        Args:
            call: Call record dictionary
            response_field: Name of the response field to extract from

        Returns:
            Tuple of (artifact_content, artifact_id) or (None, None) if no artifact found.
        """
        response = call.get(response_field, "")
        if not response:
            return None, None

        # Try to extract artifact with markers
        artifact_pattern = r"ARTIFACT:\s*(\S+)?\s*(.*?)\s*END_ARTIFACT"
        match = re.search(artifact_pattern, response, re.DOTALL)

        if match:
            artifact_id = match.group(1) or f"artifact-{call.get('call_id', 'unknown')}"
            content = match.group(2).strip()
            return content, artifact_id

        # No markers - check if response looks like an artifact
        # (for dry-run, we treat all responses as artifacts)
        if len(response) > 10:
            artifact_id = call.get(
                "artifact", f"artifact-{call.get('call_id', 'unknown')}"
            )
            return response, artifact_id

        return None, None

    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of artifact content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _validate_content_identity(
        self,
        artifact_content: str,
        call_response: str,
        call_id: str,
    ) -> bool:
        """
        Validate that artifact content is IDENTICAL to call's response field.

        B10: Identity failure is BLOCKING - refuse to ship the artifact.
        Uses byte-exact comparison only (no .strip() leniency).

        Args:
            artifact_content: Extracted artifact content
            call_response: Full response from the call
            call_id: Call ID for error reporting

        Returns:
            True if content matches byte-exactly, False otherwise.
        """
        # B10: Byte-identical comparison only (no strip/substring leniency)
        if artifact_content == call_response:
            return True

        # Content mismatch - this is BLOCKING
        self.validation_errors.append(
            f"BLOCKING: Content identity check failed for {call_id}: "
            f"artifact content does not match response field byte-for-byte"
        )
        return False

    def extract_all(self) -> list[ExtractedArtifact]:
        """
        Extract all artifacts from calls.jsonl.

        B10: Identity failure is BLOCKING - refuse to ship artifacts that fail.

        Returns:
            List of extracted artifacts (only those passing identity check).
        """
        calls = self.load_calls()
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        for call in calls:
            # Skip calls without response
            response = call.get("response_full", "")
            if not response:
                continue

            # Extract artifact from response
            content, artifact_id = self._extract_artifact_from_response(call)
            if content is None:
                continue

            # B10: Validate content identity - BLOCKING on failure
            if not self._validate_content_identity(
                content, response, call.get("call_id", "unknown")
            ):
                # BLOCKING: refuse to ship this artifact
                continue

            # Determine provenance label
            label = call.get("provenance", "model-generated")
            if label not in (
                "model-generated",
                "team-authored",
                "reconstructed-from-log",
            ):
                label = "model-generated"
                self.validation_errors.append(
                    f"Unknown provenance label for {call.get('call_id')}: {label}, defaulting to model-generated"
                )

            # Create artifact record
            artifact = ExtractedArtifact(
                artifact_id=artifact_id or f"artifact-{call.get('call_id', 'unknown')}",
                source_call_id=call.get("call_id", "unknown"),
                source_receipt_ref=call.get("receipt_ref", "unknown"),
                content=content,
                content_hash=self._compute_content_hash(content),
                label=label,
                model_id=call.get("model"),
                run_id=call.get("run_id"),
                turn=None,  # Would parse from artifact_id if needed
                agent_id=call.get("role"),
            )

            self.extracted.append(artifact)

            # Write artifact to disk - sanitize artifact_id to prevent path traversal
            try:
                safe_artifact_id = _sanitize_artifact_id(artifact.artifact_id, self.artifacts_dir)
            except ValueError as e:
                # Security rejection - skip this artifact and log the rejection
                print(f"  SECURITY: Skipping artifact - {e}")
                continue
            artifact_path = self.artifacts_dir / f"{safe_artifact_id}.txt"
            with open(artifact_path, "w", encoding="utf-8") as f:
                f.write(content)

        return self.extracted

    def write_metadata_index(self) -> Path:
        """
        Write a metadata index of all extracted artifacts.

        Returns:
            Path to the metadata index file.
        """
        index_path = self.artifacts_dir / "index.json"
        index_data = {
            "total_artifacts": len(self.extracted),
            "by_label": {},
            "artifacts": [a.to_metadata_dict() for a in self.extracted],
        }

        # Count by label
        for artifact in self.extracted:
            label = artifact.label
            if label not in index_data["by_label"]:
                index_data["by_label"][label] = 0
            index_data["by_label"][label] += 1

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

        return index_path

    def get_validation_report(self) -> dict[str, Any]:
        """
        Get a validation report for the extraction.

        Returns:
            Dict with validation results.
        """
        return {
            "total_artifacts": len(self.extracted),
            "validation_errors": len(self.validation_errors),
            "errors": self.validation_errors[:10],  # First 10 errors
            "by_label": {
                "model-generated": sum(
                    1 for a in self.extracted if a.label == "model-generated"
                ),
                "team-authored": sum(
                    1 for a in self.extracted if a.label == "team-authored"
                ),
                "reconstructed-from-log": sum(
                    1 for a in self.extracted if a.label == "reconstructed-from-log"
                ),
            },
        }

    def verify_team_authored_byte_exact(
        self,
        artifact_path: Path,
        git_commit: str,
        git_file_path: str,
    ) -> dict[str, Any]:
        """
        B10: Verify team-authored artifact is byte-exact from git commit.

        Args:
            artifact_path: Path to the extracted artifact
            git_commit: Git commit hash that held the file
            git_file_path: Path to the file in the git repo

        Returns:
            Dict with verification results.
        """
        import subprocess

        try:
            # Get file content from git commit
            result = subprocess.run(
                ["git", "show", f"{git_commit}:{git_file_path}"],
                capture_output=True,
                text=False,  # Binary mode for byte-exact comparison
                check=True,
            )
            git_content = result.stdout

            # Read artifact content
            with open(artifact_path, "rb") as f:
                artifact_content = f.read()

            # Byte-exact comparison
            if artifact_content == git_content:
                return {
                    "verified": True,
                    "artifact_path": str(artifact_path),
                    "git_commit": git_commit,
                    "git_file_path": git_file_path,
                    "artifact_hash": hashlib.sha256(artifact_content).hexdigest()[:16],
                }
            else:
                return {
                    "verified": False,
                    "error": "byte_mismatch",
                    "artifact_hash": hashlib.sha256(artifact_content).hexdigest()[:16],
                    "git_hash": hashlib.sha256(git_content).hexdigest()[:16],
                }
        except subprocess.CalledProcessError as e:
            return {
                "verified": False,
                "error": "git_command_failed",
                "stderr": e.stderr.decode("utf-8") if e.stderr else str(e),
            }


def extract_artifacts(
    calls_jsonl_path: str,
    artifacts_dir: str,
) -> dict[str, Any]:
    """
    Convenience function to extract artifacts from a calls.jsonl file.

    Args:
        calls_jsonl_path: Path to calls.jsonl
        artifacts_dir: Directory to write artifacts

    Returns:
        Dict with extraction results.
    """
    extractor = ArtifactExtractor(calls_jsonl_path, artifacts_dir)
    artifacts = extractor.extract_all()
    index_path = extractor.write_metadata_index()
    report = extractor.get_validation_report()

    return {
        "artifacts_extracted": len(artifacts),
        "artifacts_dir": str(artifacts_dir),
        "index_path": str(index_path),
        "validation_report": report,
    }


def verify_wrong_side_guard(
    calls_jsonl_path: str,
    artifacts_dir: str,
) -> dict[str, Any]:
    """
    Verify the wrong-side guard: every model-generated artifact's content
    matches its call's response field.

    Args:
        calls_jsonl_path: Path to calls.jsonl
        artifacts_dir: Directory with extracted artifacts

    Returns:
        Dict with verification results.
    """
    calls_path = Path(calls_jsonl_path)
    artifacts_path = Path(artifacts_dir)

    # Load calls
    calls = []
    with open(calls_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                calls.append(json.loads(line))

    # Load artifacts
    mismatches = []
    for call in calls:
        artifact_id = call.get("artifact")
        if not artifact_id:
            continue

        artifact_path = artifacts_path / f"{artifact_id}.txt"
        if not artifact_path.exists():
            mismatches.append(
                {
                    "call_id": call.get("call_id"),
                    "artifact_id": artifact_id,
                    "error": "artifact file not found",
                }
            )
            continue

        with open(artifact_path, "r", encoding="utf-8") as f:
            artifact_content = f.read()

        response_content = call.get("response_full", "")

        # Check identity
        if (
            artifact_content.strip() != response_content.strip()
            and artifact_content.strip() not in response_content
        ):
            mismatches.append(
                {
                    "call_id": call.get("call_id"),
                    "artifact_id": artifact_id,
                    "error": "content mismatch",
                    "artifact_hash": hashlib.sha256(
                        artifact_content.encode("utf-8")
                    ).hexdigest()[:16],
                    "response_hash": hashlib.sha256(
                        response_content.encode("utf-8")
                    ).hexdigest()[:16],
                }
            )

    return {
        "total_calls": len(calls),
        "artifacts_checked": len(calls)
        - sum(1 for c in calls if not c.get("artifact")),
        "mismatches": len(mismatches),
        "mismatch_details": mismatches[:10],  # First 10
        "guard_passed": len(mismatches) == 0,
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python -m dataset_pack.extract <calls.jsonl> <artifacts_dir>")
        sys.exit(1)

    calls_path = sys.argv[1]
    artifacts_dir = sys.argv[2]

    print(f"Extracting artifacts from {calls_path}...")

    try:
        result = extract_artifacts(calls_path, artifacts_dir)
        print("Extraction complete:")
        print(f"  Artifacts: {result['artifacts_extracted']}")
        print(f"  Index: {result['index_path']}")
        print(f"  Validation: {result['validation_report']}")

        # Verify wrong-side guard
        guard_result = verify_wrong_side_guard(calls_path, artifacts_dir)
        print(
            f"  Wrong-side guard: {'PASSED' if guard_result['guard_passed'] else 'FAILED'}"
        )
        if not guard_result["guard_passed"]:
            print(f"  Mismatches: {guard_result['mismatches']}")

    except (RuntimeError, OSError, json.JSONDecodeError) as e:
        print(f"Extraction failed: {e}", file=sys.stderr)
        sys.exit(1)
