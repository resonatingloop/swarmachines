"""
dataset_pack/upload.py — HF + Adaption upload script reading credentials from environment only

Uploads packaged dataset to Hugging Face Hub using the `hf` CLI, or to Adaption via API.
Credentials are read from the environment (cached hf CLI auth or ADAPTION_API_KEY) — never printed,
copied, or written to any file.

Usage:
    python -m dataset_pack.upload <pack_dir> <repo_id> [--dry-run] [--target hf|adaption]

Security:
- Refuses to run without authenticated hf CLI or ADAPTION_API_KEY
- Never prints or logs token values
- Validates repo/dataset existence before upload
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    from adaption import Adaption, APIConnectionError, APIStatusError

    ADAPTION_AVAILABLE = True
except ImportError:
    Adaption = None  # type: ignore
    APIStatusError = APIConnectionError = Exception  # type: ignore
    ADAPTION_AVAILABLE = False


class AdaptionUploader:
    """
    Adaption dataset uploader using the Python SDK.

    Uploads records.jsonl + runs.jsonl to Adaption's datasets API.
    API key is read from ADAPTION_API_KEY environment variable (never printed).

    Attributes:
        pack_dir: Directory containing the packaged dataset
        dataset_name: Name for the dataset in Adaption
        dry_run: If True, validate without uploading
    """

    def __init__(
        self,
        pack_dir: str,
        dataset_name: str = "swarmachines-freight-swarm-runs",
        dry_run: bool = False,
    ):
        if not ADAPTION_AVAILABLE:
            raise RuntimeError(
                "adaption SDK not installed. Install with: pip install adaption"
            )

        self.pack_dir = Path(pack_dir)
        self.dataset_name = dataset_name
        self.dry_run = dry_run

        # API key is read from env by the SDK automatically
        # We just verify it exists (never print the value)
        if not os.environ.get("ADAPTION_API_KEY"):
            raise RuntimeError(
                "ADAPTION_API_KEY not set in environment. "
                "Add it to .env or export before running."
            )

        self.client = Adaption()  # Picks up ADAPTION_API_KEY from env

    def _upload_file_to_presigned_url(
        self, url: str, file_path: Path, method: str = "PUT"
    ) -> bool:
        """
        Upload a file to a presigned S3 URL.

        Args:
            url: Presigned upload URL
            file_path: Path to file to upload
            method: HTTP method (PUT for S3)

        Returns:
            True if upload succeeded

        Raises:
            RuntimeError: If upload fails
        """
        import httpx

        with open(file_path, "rb") as f:
            content = f.read()

        response = httpx.request(
            method=method,
            url=url,
            content=content,
            headers={"Content-Type": "application/jsonl"},
        )

        if response.status_code not in (200, 201, 204):
            raise RuntimeError(
                f"File upload failed with status {response.status_code}: "
                f"{response.text[:200]}"
            )

        return True

    def _poll_dataset_status(
        self, dataset_id: str, timeout_seconds: int = 300, poll_interval: float = 2.0
    ) -> dict[str, Any]:
        """
        Poll dataset status until it reaches a terminal state.

        Args:
            dataset_id: Dataset ID to poll
            timeout_seconds: Max time to wait
            poll_interval: Seconds between polls

        Returns:
            Final status response

        Raises:
            RuntimeError: If status is 'failed' or timeout occurs
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                status = self.client.datasets.get_status(dataset_id)

                if status.status == "succeeded":
                    return {
                        "dataset_id": dataset_id,
                        "status": status.status,
                        "row_count": status.row_count,
                        "success": True,
                    }
                elif status.status == "failed":
                    error_data = getattr(status, "error_data", None)
                    error_msg = error_data.message if error_data else "Unknown error"
                    raise RuntimeError(f"Dataset processing failed: {error_msg}")
                elif status.status in ("pending", "running"):
                    # Continue polling
                    time.sleep(poll_interval)
                else:
                    # awaiting_input or other states
                    return {
                        "dataset_id": dataset_id,
                        "status": status.status,
                        "row_count": status.row_count,
                        "success": True,
                        "note": f"Dataset in {status.status} state",
                    }

            except APIStatusError as e:
                raise RuntimeError(
                    f"API error while polling status: {e.status_code} - {e}"
                ) from e
            except APIConnectionError:
                # Retry on connection errors
                time.sleep(poll_interval * 2)

        raise RuntimeError(
            f"Timeout waiting for dataset {dataset_id} to process "
            f"(waited {timeout_seconds}s)"
        )

    def upload(self) -> dict[str, Any]:
        """
        Upload the packaged dataset to Adaption.

        B5 fix: Uploads BOTH tables:
        - data/records.jsonl (event records table)
        - data/runs.jsonl (run summaries table)

        Returns:
            Dict with upload results including dataset_id.
        """
        if self.dry_run:
            return self._dry_run_upload()

        # Validate required files
        required_files = ["data/records.jsonl", "data/runs.jsonl"]
        for filename in required_files:
            file_path = self.pack_dir / filename
            if not file_path.exists():
                raise RuntimeError(f"Required file missing: {filename}")

        uploaded_datasets = []

        # Upload records.jsonl
        try:
            create_response = self.client.datasets.create(
                source={
                    "type": "file",
                    "name": f"{self.dataset_name}-records",
                    "file_format": "jsonl",
                }
            )

            dataset_id = create_response.dataset_id
            upload_instructions = getattr(create_response, "upload_instructions", None)

            if not upload_instructions:
                raise RuntimeError(
                    "No upload_instructions returned from dataset creation"
                )

            # Upload records.jsonl to presigned URL
            self._upload_file_to_presigned_url(
                url=upload_instructions.url,
                file_path=self.pack_dir / "data" / "records.jsonl",
                method=upload_instructions.method,
            )

            # Poll for completion
            status_result = self._poll_dataset_status(dataset_id)

            uploaded_datasets.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_name": f"{self.dataset_name}-records",
                    "status": status_result["status"],
                    "row_count": status_result.get("row_count"),
                }
            )

        except (APIStatusError, APIConnectionError) as e:
            raise RuntimeError(
                f"Adaption API error uploading records: {e.status_code if hasattr(e, 'status_code') else e}"
            ) from e

        # Upload runs.jsonl (B5 fix)
        try:
            create_response = self.client.datasets.create(
                source={
                    "type": "file",
                    "name": f"{self.dataset_name}-runs",
                    "file_format": "jsonl",
                }
            )

            dataset_id = create_response.dataset_id
            upload_instructions = getattr(create_response, "upload_instructions", None)

            if not upload_instructions:
                raise RuntimeError(
                    "No upload_instructions returned from dataset creation"
                )

            # Upload runs.jsonl to presigned URL
            self._upload_file_to_presigned_url(
                url=upload_instructions.url,
                file_path=self.pack_dir / "data" / "runs.jsonl",
                method=upload_instructions.method,
            )

            # Poll for completion
            status_result = self._poll_dataset_status(dataset_id)

            uploaded_datasets.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_name": f"{self.dataset_name}-runs",
                    "status": status_result["status"],
                    "row_count": status_result.get("row_count"),
                }
            )

        except (APIStatusError, APIConnectionError) as e:
            raise RuntimeError(
                f"Adaption API error uploading runs: {e.status_code if hasattr(e, 'status_code') else e}"
            ) from e

        return {
            "uploaded": True,
            "target": "adaption",
            "datasets": uploaded_datasets,
            "files_uploaded": ["data/records.jsonl", "data/runs.jsonl"],
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
        required_files = ["data/records.jsonl", "data/runs.jsonl"]
        for filename in required_files:
            file_path = self.pack_dir / filename
            if file_path.exists():
                files_to_upload.append(filename)
            else:
                files_to_upload.append(f"{filename} (MISSING)")

        return {
            "uploaded": False,
            "dry_run": True,
            "target": "adaption",
            "files_to_upload": files_to_upload,
            "pack_valid": all("(MISSING)" not in f for f in files_to_upload),
            "api_key_present": bool(os.environ.get("ADAPTION_API_KEY")),
        }

    def full_workflow(self) -> dict[str, Any]:
        """
        Execute full upload workflow: API key check → upload → poll status.

        Returns:
            Dict with workflow results.
        """
        # Check API key
        if not os.environ.get("ADAPTION_API_KEY"):
            raise RuntimeError("ADAPTION_API_KEY not set in environment")

        # Upload
        upload_result = self.upload()

        return {
            "api_key_present": True,
            "upload": upload_result,
        }


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
        - data/records.jsonl (event records table)
        - data/runs.jsonl (run summaries table)
        - data/runs/ (all run directories with raw layer)

        Defect 10 fix: Check and propagate real return codes from hf upload-file/upload-folder.

        Returns:
            Dict with upload results.
        """
        if self.dry_run:
            return self._dry_run_upload()

        # Validate pack directory (spec-conformant: no train/test split)
        required_files = [
            "README.md",
            "MANIFEST.md",
            "data/records.jsonl",
            "data/runs.jsonl",
        ]
        for filename in required_files:
            file_path = self.pack_dir / filename
            if not file_path.exists():
                raise RuntimeError(f"Required file missing: {filename}")

        # Upload README.md first (dataset card) - Defect 10 fix: check return code
        result = self._run_hf_command(
            [
                "upload-file",
                self.repo_id,
                str(self.pack_dir / "README.md"),
                "README.md",
                "--repo-type",
                "dataset",
            ]
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to upload README.md: {result.stderr.strip()}")

        # Upload MANIFEST.md - Defect 10 fix: check return code
        result = self._run_hf_command(
            [
                "upload-file",
                self.repo_id,
                str(self.pack_dir / "MANIFEST.md"),
                "MANIFEST.md",
                "--repo-type",
                "dataset",
            ]
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to upload MANIFEST.md: {result.stderr.strip()}")

        # Upload data/records.jsonl (B5: spec-conformant, no train/test split) - Defect 10 fix
        result = self._run_hf_command(
            [
                "upload-file",
                self.repo_id,
                str(self.pack_dir / "data" / "records.jsonl"),
                "data/records.jsonl",
                "--repo-type",
                "dataset",
            ]
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to upload records.jsonl: {result.stderr.strip()}"
            )

        # Upload data/runs.jsonl - Defect 10 fix
        result = self._run_hf_command(
            [
                "upload-file",
                self.repo_id,
                str(self.pack_dir / "data" / "runs.jsonl"),
                "data/runs.jsonl",
                "--repo-type",
                "dataset",
            ]
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to upload runs.jsonl: {result.stderr.strip()}")

        # Upload data/runs/ directory (raw per-run layer) - Defect 10 fix
        runs_dir = self.pack_dir / "data" / "runs"
        if runs_dir.exists():
            result = self._run_hf_command(
                [
                    "upload-folder",
                    self.repo_id,
                    str(runs_dir),
                    "data/runs",
                    "--repo-type",
                    "dataset",
                ]
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to upload runs/: {result.stderr.strip()}")

        return {
            "uploaded": True,
            "repo_id": self.repo_id,
            "files_uploaded": [
                "README.md",
                "MANIFEST.md",
                "data/records.jsonl",
                "data/runs.jsonl",
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

        # Check required files (spec-conformant: no train/test split)
        required_files = [
            "README.md",
            "MANIFEST.md",
            "data/records.jsonl",
            "data/runs.jsonl",
        ]
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
    target: str = "hf",
) -> dict[str, Any]:
    """
    Convenience function to upload a dataset to HF Hub or Adaption.

    Args:
        pack_dir: Directory containing packaged dataset
        repo_id: Target repo ID (for HF) or dataset name (for Adaption)
        dry_run: If True, validate without uploading
        target: Upload target - "hf" or "adaption"

    Returns:
        Dict with upload results.
    """
    if target == "adaption":
        if not ADAPTION_AVAILABLE:
            raise RuntimeError(
                "adaption SDK not available. Install with: pip install adaption"
            )
        uploader = AdaptionUploader(pack_dir, dataset_name=repo_id, dry_run=dry_run)
    else:
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
    except (RuntimeError, OSError):
        pass  # Org check failed; fall through to user namespace

    # Fall back to user namespace
    slug = "swarmachines-freight-swarm-runs"
    return f"christopherwoodall/{slug}"


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Usage: python -m dataset_pack.upload <pack_dir> <repo_id> [--dry-run] [--target hf|adaption]"
        )
        print("  pack_dir: Directory containing packaged dataset")
        print(
            "  repo_id: Target HF repo ID (e.g., swarmachines/freight-swarm-runs) or Adaption dataset name"
        )
        print("  --dry-run: Validate without uploading")
        print("  --target: Upload target - 'hf' (default) or 'adaption'")
        sys.exit(1)

    pack_dir = sys.argv[1]
    repo_id = sys.argv[2]
    dry_run = "--dry-run" in sys.argv

    # Parse --target option
    target = "hf"  # default
    if "--target" in sys.argv:
        target_idx = sys.argv.index("--target")
        if target_idx + 1 < len(sys.argv):
            target = sys.argv[target_idx + 1].lower()
            if target not in ("hf", "adaption"):
                print(
                    f"Invalid target: {target}. Must be 'hf' or 'adaption'.",
                    file=sys.stderr,
                )
                sys.exit(1)

    print(f"Uploading dataset from {pack_dir} to {repo_id} (target={target})...")
    if dry_run:
        print("(dry-run mode — no actual upload)")

    try:
        result = upload_dataset(pack_dir, repo_id, dry_run=dry_run, target=target)

        if dry_run:
            print("Dry-run validation:")
            if target == "adaption":
                print(f"  API key present: {result.get('api_key_present', False)}")
                print(f"  Files to upload: {result['upload']['files_to_upload']}")
                print(f"  Pack valid: {result['upload']['pack_valid']}")
            else:
                print(f"  Auth: {result['auth']}")
                print(f"  Repo exists: {result['repo']['exists']}")
                print(f"  Files to upload: {result['upload']['files_to_upload']}")
                print(f"  Pack valid: {result['upload']['pack_valid']}")
        else:
            print("Upload complete:")
            if target == "adaption":
                print("  Target: Adaption")
                print(f"  Dataset ID: {result['upload']['dataset_id']}")
                print(f"  Status: {result['upload']['status']}")
                print(f"  Row count: {result['upload'].get('row_count')}")
            else:
                print(f"  Repo: {result['upload']['repo_id']}")
                print(f"  Files: {result['upload']['files_uploaded']}")

    except RuntimeError as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        sys.exit(1)
