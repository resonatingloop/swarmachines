"""Capability and refusal tests for the pure route-gossip policy."""

import copy
import unittest

from route_gossip import admit_report, make_report, select


def view():
    return {
        "current_location": "a",
        "turn": 8,
        "visible_freight": [{"id": "f-1", "destination": "z"}],
        "known_routes": {"a->b": "open", "a->c": "open"},
    }


def report(sender, routes, message_id=None, turn=8):
    body = make_report(
        {"current_location": sender, "turn": turn, "known_routes": routes}, sender
    )
    result, error = admit_report(
        body, sender=sender, message_id=message_id or f"m-{sender}", turn=8
    )
    assert error is None
    return result


class PolicyTests(unittest.TestCase):
    def test_message_changes_legal_first_hop(self):
        """Both alternatives are locally legal; only report content differs."""
        local = view()
        left = select(
            local, [report("b", {"b->z": "open"}), report("c", {"c->z": "closed"})]
        )
        right = select(
            local, [report("b", {"b->z": "closed"}), report("c", {"c->z": "open"})]
        )
        self.assertEqual((left["next_hop"], right["next_hop"]), ("b", "c"))
        self.assertTrue(left["choice_changed"])
        self.assertIsNone(select(local)["next_hop"])
        self.assertEqual(local, view())

    def test_irrelevant_report_does_not_change_choice(self):
        base = report("b", {"b->z": "open"})
        self.assertEqual(
            select(view(), [base])["path"],
            select(view(), [base, report("x", {"x->y": "open"})])["path"],
        )

    def test_conflict_unknown_and_local_wins(self):
        local = view()
        # Reports from different senders can observe the same depot.
        first = report("b", {"b->z": "open"})
        body = make_report(
            {"current_location": "b", "turn": 8, "known_routes": {"b->z": "closed"}},
            "d",
        )
        second, error = admit_report(body, sender="d", message_id="m-d", turn=8)
        self.assertIsNone(error)
        self.assertIsNone(select(local, [first, second])["next_hop"])
        local["known_routes"]["a->z"] = "open"
        body = make_report(
            {"current_location": "a", "turn": 8, "known_routes": {"a->z": "closed"}},
            "d",
        )
        peer, _ = admit_report(body, sender="d", message_id="m-d", turn=8)
        self.assertEqual(select(local, [peer])["next_hop"], "z")

    def test_shortest_then_lexicographic_path(self):
        peers = [report("b", {"b->z": "open"}), report("c", {"c->z": "open"})]
        self.assertEqual(select(view(), peers)["path"], ["a", "b", "z"])
        self.assertEqual(select(view(), peers), select(view(), list(reversed(peers))))

    def test_refusals(self):
        body = make_report(
            {"current_location": "b", "turn": 8, "known_routes": {"b->z": "open"}}, "b"
        )
        for field, bad in [
            ("turn", 7),
            ("turn", 9),
            ("turn", True),
            ("sender", "foreign"),
            ("routes", {"z->a": "open"}),
            ("routes", {"b->z": []}),
            ("location", []),
        ]:
            changed = copy.deepcopy(body)
            changed[field] = bad
            result, reason = admit_report(changed, sender="b", message_id="m-b", turn=8)
            self.assertIsNone(result)
            self.assertIsNotNone(reason)

    def test_limits_and_no_mutation(self):
        local = view()
        before = copy.deepcopy(local)
        peers = [report("b", {"b->z": "open"})]
        select(local, peers)
        self.assertEqual(before, local)
        with self.assertRaises(ValueError):
            select(local, peers * 33)
        with self.assertRaises(ValueError):
            select(local, peers * 2)
        with self.assertRaises(ValueError):
            make_report(
                {
                    "current_location": "b",
                    "turn": 8,
                    "known_routes": {f"b->x{i}": "open" for i in range(33)},
                },
                "b",
            )

    def test_empty_destination_and_wait(self):
        local = view()
        self.assertEqual(select(local)["reason"], "no_known_path")
        local["visible_freight"] = []
        self.assertEqual(select(local)["reason"], "no_visible_freight")
        local["visible_freight"] = [{"id": "f-1", "destination": "a"}]
        self.assertEqual(select(local)["reason"], "at_destination")

    def test_never_invents_first_hop(self):
        local = view()
        local["known_routes"] = {}
        self.assertIsNone(select(local, [report("b", {"b->z": "open"})])["next_hop"])


if __name__ == "__main__":
    unittest.main()
