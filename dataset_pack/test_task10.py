"""offline tests for the one-drop task-10 coordinator."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from .configs import get_task_configs
from .task10 import CONFIRMATION, execute_batch, planned_call_count, preflight


class _FakeBatchAdapter:
    calls = 0

    def chat(self, *, model: str, messages: list[dict[str, str]], **kwargs):
        type(self).calls += 1
        return SimpleNamespace(
            model=model,
            output_text=f"offline-task10-response-{type(self).calls}",
            usage=SimpleNamespace(input_tokens=32, output_tokens=8),
            raw_response=SimpleNamespace(estimated_credits_consumed="0.0000088"),
        )


class Task10PreflightTests(unittest.TestCase):
    def test_exact_matrix_fits_the_authorized_envelope(self):
        configs = get_task_configs()
        self.assertEqual(planned_call_count(configs), 1920)

        proof = preflight("10")

        self.assertTrue(proof["matrix"]["all_passed"])
        self.assertEqual(len(proof["matrix"]["instances"]), 15)
        self.assertEqual(proof["budget"]["planned_calls"], 1920)
        self.assertLessEqual(float(proof["budget"]["max_reserved_credits"]), 10)
        self.assertEqual(proof["provider_calls"], 0)

    def test_ceiling_cannot_expand_past_owner_authority(self):
        with self.assertRaisesRegex(ValueError, "cannot exceed 10"):
            preflight("10.000001")

    def test_full_one_drop_path_with_fake_provider(self):
        _FakeBatchAdapter.calls = 0
        with (
            tempfile.TemporaryDirectory() as root,
            patch.dict(os.environ, {"ADAPTION_API_KEY": "synthetic-task10-key-value"}),
            patch("dataset_pack.task10._require_clean_generation_commit"),
            patch("runtime.adaption_adapter.AdaptionAdapter", _FakeBatchAdapter),
        ):
            root_path = Path(root)
            receipt = execute_batch(
                runs_dir=root_path / "runs",
                pack_dir=root_path / "pack",
                repo=Path.cwd(),
                ceiling_credits="10",
                confirmation=CONFIRMATION,
            )

        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(len(receipt["completed_instances"]), 15)
        self.assertEqual(receipt["budget"]["calls_started"], 1920)
        self.assertEqual(receipt["budget"]["calls_completed"], 1920)
        self.assertEqual(receipt["budget"]["calls_failed"], 0)
        self.assertEqual(receipt["package"]["runs"], 15)
        self.assertEqual(receipt["package"]["raw_runs"], 15)
        self.assertTrue(receipt["package"]["no_key_passed"])


if __name__ == "__main__":
    unittest.main()
