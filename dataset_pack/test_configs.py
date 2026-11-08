"""contract tests for the accepted fifteen-instance dataset matrix."""

from __future__ import annotations

import json
import unittest

from runtime.runner import TurnSeamRunner

from .configs import get_task_configs, validate_configs


class TaskConfigMatrixTests(unittest.TestCase):
    def test_matrix_matches_the_fifteen_instance_contract(self):
        configs = get_task_configs()

        self.assertEqual(validate_configs(configs), [])
        self.assertEqual(len(configs), 15)
        self.assertEqual(
            [config.seed for config in configs[:5]], [42, 137, 299, 413, 571]
        )
        self.assertEqual(
            {config.topology for config in configs},
            {"mesh", "hub-spoke", "bidirectional-ring"},
        )
        self.assertTrue(
            any("peer-mute" in config.disturbance_schedule for config in configs)
        )

    def test_matrix_replays_byte_identically(self):
        first = [
            json.dumps(config.__dict__, sort_keys=True, separators=(",", ":"))
            for config in get_task_configs()
        ]
        second = [
            json.dumps(config.__dict__, sort_keys=True, separators=(",", ":"))
            for config in get_task_configs()
        ]

        self.assertEqual(first, second)

    def test_declared_graph_and_jobs_reach_the_runtime_world(self):
        config = get_task_configs()[0]
        args = config.to_runner_args()
        runner = TurnSeamRunner(**args)

        self.assertEqual(
            [
                {
                    "from": route.from_loc,
                    "to": route.to_loc,
                    "status": route.status,
                    **({"bridge": route.bridge} if route.bridge else {}),
                }
                for route in runner.freight_world.routes.values()
            ],
            config.graph["routes"],
        )
        self.assertEqual(
            [
                {
                    "freight_id": item.item_id,
                    "origin": item.origin,
                    "destination": item.destination,
                    "freight_type": item.freight_type,
                }
                for item in runner.freight_world.freight_items.values()
            ],
            config.job_set,
        )

    def test_hub_spoke_uses_an_agent_as_the_communication_hub(self):
        config = get_task_configs()[2]
        runner = TurnSeamRunner(**config.to_runner_args())

        self.assertIn(runner.topology.hub, config.agent_roster)
        allowed, reason = runner.topology.can_communicate(
            runner.topology.hub, config.agent_roster[1], {}
        )
        self.assertTrue(allowed, reason)


if __name__ == "__main__":
    unittest.main()
