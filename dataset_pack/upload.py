"""
dataset_pack/upload.py — HF upload script reading credentials from environment only

Uploads packaged dataset to Hugging Face Hub using the `hf` CLI.
Credentials are read from the environment (cached hf CLI auth) — never printed,
copied, or written to any file.

Usage:
    python -m dataset_pack.upload <pack_dir> <repo_id> [--dry-run]

Security:
- Refuses to run without authenticated hf CLI
- Never prints or logs token values
- Validates repo existence before upload
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any


class HFUploader:
    """
    Hugging Face dataset uploader using the hf CLI.

    Attributes:
        pack_dir: Directory containing the packaged dataset
        repo_id: Target repo ID (e.g., "swarmachines/freight-swarm-runs")
        dry_run: If True, validate without uploading
    """

    def __init__(
        self,
        pack_dir: str,
        repo_id: str,
        dry_run: bool = False,
    ):
        self.pack_dir = Path(pack_dir)
        self.repo_id = repo_id
        self.dry_run = dry_run

    def _run_hf_command(
        self,
        args: list[str],
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run an hf CLI command.

        Args:
            args: Command arguments (without 'hf' prefix)
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess result

        Raises:
            RuntimeError: If hf CLI is not available
        """
        try:
            result = subprocess.run(
                ["hf"] + args,
                capture_output=capture_output,
                text=True,
                check=False,
            )
            return result
        except FileNotFoundError:
            raise RuntimeError(
                "hf CLI not found. Install with: pip install huggingface_hub"
            ) from None

    def check_cli_auth(self) -> dict[str, Any]:
        """
        Check that hf CLI is authenticated.

        Returns:
            Dict with auth status.

        Raises:
            RuntimeError: If not authenticated.
        """
        result = self._run_hf_command(["whoami"])

        if result.returncode != 0:
            raise RuntimeError(
                "hf CLI not authenticated. Run 'huggingface-cli login' first."
            )

        # Parse username from output (format: "Username: <name>")
        username = "unknown"
        for line in result.stdout.strip().split("\n"):
            if line.startswith("Username:"):
                username = line.split(":", 1)[1].strip()
                break

        return {
            "authenticated": True,
            "username": username,
            "cli_available": True,
        }

    def check_repo_exists(self) -> dict[str, Any]:
        """
        Check if target repo exists.

        Returns:
            Dict with repo existence status.
        """
        result = self._run_hf_command(["repo", "ls", self.repo_id])

        exists = result.returncode == 0

        return {
            "repo_id": self.repo_id,
            "exists": exists,
            "type": "dataset",  # We're uploading a dataset
        }

    def create_repo_if_needed(self) -> dict[str, Any]:
        """
        Create the repo if it doesn't exist.

        Returns:
            Dict with creation result.
        """
        # Check if exists first
        check = self.check_repo_exists()
        if check["exists"]:
            return {"created": False, "repo_id": self.repo_id, "already_exists": True}

        # Create dataset repo
        result = self._run_hf_command(
            [
                "repo",
                "create",
                self.repo_id,
                "--type",
                "dataset",
                "--private",  # Default to private; can be changed manually
            ]
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to create repo: {result.stderr.strip()}")

        return {"created": True, "repo_id": self.repo_id, "already_exists": False}

    def upload(self) -> dict[str, Any]:
        """
        Upload the packaged dataset to HF Hub.

        Uploads:
        - README.md (dataset card)
        - MANIFEST.md
        - data/train.jsonl
        - data/runs/ (all run directories)

        Returns:
            Dict with upload results.
        """
        if self.dry_run:
            return self._dry_run_upload()

        # Validate pack directory
        required_files = ["README.md", "MANIFEST.md", "data/train.jsonl"]
        for filename in required_files:
            file_path = self.pack_dir / filename
            if not file_path.exists():
                raise RuntimeError(f"Required file missing: {filename}")

        # Upload README.md first (dataset card)
        self._run_hf_command(
            [
                "upload-file",
                self.repo_id,
                str(self.pack_dir / "README.md"),
                "README.md",
                "--repo-type",
                "dataset",
            ]
        )

        # Upload MANIFEST.md
        self._run_hf_command(
            [
                "upload-file",
                self.repo_id,
                str(self.pack_dir / "MANIFEST.md"),
                "MANIFEST.md",
                "--repo-type",
                "dataset",
            ]
        )

        # Upload data/train.jsonl
        self._run_hf_command(
            [
                "upload-file",
                self.repo_id,
                str(self.pack_dir / "data" / "train.jsonl"),
                "data/train.jsonl",
                "--repo-type",
                "dataset",
            ]
        )

        # Upload data/runs/ directory
        runs_dir = self.pack_dir / "data" / "runs"
        if runs_dir.exists():
            self._run_hf_command(
                [
                    "upload-folder",
                    self.repo_id,
                    str(runs_dir),
                    "data/runs",
                    "--repo-type",
                    "dataset",
                ]
            )

        return {
            "uploaded": True,
            "repo_id": self.repo_id,
            "files_uploaded": [
                "README.md",
                "MANIFEST.md",
                "data/train.jsonl",
                "data/runs/",
            ],
            "dry_run": False,
        }

    def _dry_run_upload(self) -> dict[str, Any]:
        """
        Simulate upload without actually uploading.

        Returns:
            Dict with dry-run results.
        """
        files_to_upload = []

        # Check required files
        required_files = ["README.md", "MANIFEST.md", "data/train.jsonl"]
        for filename in required_files:
            file_path = self.pack_dir / filename
            if file_path.exists():
                files_to_upload.append(filename)
            else:
                files_to_upload.append(f"{filename} (MISSING)")

        # Check runs directory
        runs_dir = self.pack_dir / "data" / "runs"
        if runs_dir.exists():
            run_count = len(list(runs_dir.glob("run-*")))
            files_to_upload.append(f"data/runs/ ({run_count} runs)")
        else:
            files_to_upload.append("data/runs/ (MISSING)")

        return {
            "uploaded": False,
            "dry_run": True,
            "repo_id": self.repo_id,
            "files_to_upload": files_to_upload,
            "pack_valid": all("(MISSING)" not in f for f in files_to_upload),
        }

    def full_workflow(self) -> dict[str, Any]:
        """
        Execute full upload workflow: auth check → repo check → upload.

        Returns:
            Dict with workflow results.
        """
        # Check auth
        auth_result = self.check_cli_auth()

        # Create repo if needed
        repo_result = self.create_repo_if_needed()

        # Upload
        upload_result = self.upload()

        return {
            "auth": auth_result,
            "repo": repo_result,
            "upload": upload_result,
        }


def upload_dataset(
    pack_dir: str,
    repo_id: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Convenience function to upload a dataset to HF Hub.

    Args:
        pack_dir: Directory containing packaged dataset
        repo_id: Target repo ID
        dry_run: If True, validate without uploading

    Returns:
        Dict with upload results.
    """
    uploader = HFUploader(pack_dir, repo_id, dry_run=dry_run)
    return uploader.full_workflow()


def determine_repo_id(org_preference: str = "swarmachines") -> str:
    """
    Determine the target repo ID based on org availability.

    Args:
        org_preference: Preferred org name

    Returns:
        Repo ID string.
    """
    # Try to check if org exists using hf CLI
    uploader = HFUploader(".", "dummy")  # Dummy for CLI access

    try:
        # Check if we can access the org
        result = uploader._run_hf_command(["org", "list"])
        if result.returncode == 0 and org_preference in result.stdout:
            # Org exists and we have access
            slug = "freight-swarm-runs"
            return f"{org_preference}/{slug}"
    except Exception:
        pass

    # Fall back to user namespace
    slug = "swarmachines-freight-swarm-runs"
    return f"christopherwoodall/{slug}"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m dataset_pack.upload <pack_dir> <repo_id> [--dry-run]")
        print("  pack_dir: Directory containing packaged dataset")
        print("  repo_id: Target HF repo ID (e.g., swarmachines/freight-swarm-runs)")
        print("  --dry-run: Validate without uploading")
        sys.exit(1)

    pack_dir = sys.argv[1]
    repo_id = sys.argv[2]
    dry_run = "--dry-run" in sys.argv

    print(f"Uploading dataset from {pack_dir} to {repo_id}...")
    if dry_run:
        print("(dry-run mode — no actual upload)")

    try:
        result = upload_dataset(pack_dir, repo_id, dry_run=dry_run)

        if dry_run:
            print("Dry-run validation:")
            print(f"  Auth: {result['auth']}")
            print(f"  Repo exists: {result['repo']['exists']}")
            print(f"  Files to upload: {result['upload']['files_to_upload']}")
            print(f"  Pack valid: {result['upload']['pack_valid']}")
        else:
            print("Upload complete:")
            print(f"  Repo: {result['upload']['repo_id']}")
            print(f"  Files: {result['upload']['files_uploaded']}")

    except RuntimeError as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        sys.exit(1)
