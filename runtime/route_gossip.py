"""Bounded, deterministic route selection from observations and delivered reports."""

import heapq
import re
from dataclasses import dataclass

POLICY = "route-gossip-v1"
MAX_ROUTES = 32
MAX_REPORTS = 32
IDENTIFIER = re.compile(r"[a-zA-Z0-9_-]{1,64}\Z")


def _identifier(value):
    return isinstance(value, str) and IDENTIFIER.fullmatch(value) is not None


def _routes(value):
    if not isinstance(value, dict) or len(value) > MAX_ROUTES:
        raise ValueError("invalid_routes")
    for edge, status in value.items():
        if not isinstance(edge, str) or len(edge) > 130:
            raise ValueError("invalid_route")
        parts = edge.split("->")
        if len(parts) != 2 or not all(_identifier(p) for p in parts):
            raise ValueError("invalid_route")
        if status not in ("open", "closed"):
            raise ValueError("invalid_status")
    return dict(value)


def make_report(observation, sender):
    """Copy only locally observed route facts into a typed report.

    Args:
        observation: Current local view, never a world instance.
        sender: Transport-owned sender identifier.

    Returns:
        A bounded report containing no freight or private agent context.
    """
    location = observation["current_location"]
    turn = observation["turn"]
    if not _identifier(sender) or not _identifier(location):
        raise ValueError("invalid_identity")
    if type(turn) is not int or turn < 1:
        raise ValueError("invalid_turn")
    routes = _routes(observation["known_routes"])
    if any(edge.split("->")[0] != location for edge in routes):
        raise ValueError("nonlocal_route")
    return {
        "type": "route_report",
        "sender": sender,
        "turn": turn,
        "location": location,
        "routes": routes,
    }


@dataclass(frozen=True)
class Report:
    """A report admitted by the recipient after successful delivery."""

    message_id: str
    sender: str
    turn: int
    routes: tuple


def admit_report(body, *, sender, message_id, turn):
    """Validate a delivered body against transport-owned identity and time.

    Args:
        body: Received typed report; not executable text.
        sender: Actual sender supplied by the delivery path.
        message_id: Actual message identity supplied by the delivery path.
        turn: Recipient's current logical turn.

    Returns:
        A frozen report, or None and a categorical refusal reason.
    """
    if not isinstance(body, dict) or set(body) != {
        "type",
        "sender",
        "turn",
        "location",
        "routes",
    }:
        return None, "malformed_report"
    if not _identifier(sender) or not _identifier(message_id):
        return None, "invalid_identity"
    if body["type"] != "route_report" or body["sender"] != sender:
        return None, "identity_mismatch"
    if type(body["turn"]) is not int or body["turn"] != turn:
        return None, "wrong_turn"
    try:
        checked = make_report(
            {
                "current_location": body["location"],
                "turn": body["turn"],
                "known_routes": body["routes"],
            },
            sender,
        )
    except (ValueError, TypeError):
        return None, "malformed_report"
    return Report(
        message_id, sender, turn, tuple(sorted(checked["routes"].items()))
    ), None


def _path(routes, start, destination, local):
    queue = [(0, (start,))]
    visited = set()
    while queue:
        length, path = heapq.heappop(queue)
        node = path[-1]
        if node in visited:
            continue
        visited.add(node)
        if node == destination:
            return path
        adjacent = sorted(
            edge.split("->")[1]
            for edge, state in routes.items()
            if state == "open" and edge.split("->")[0] == node
        )
        for target in adjacent:
            if length == 0 and local.get(f"{node}->{target}") != "open":
                continue
            if target not in visited:
                heapq.heappush(queue, (length + 1, (*path, target)))
    return ()


def select(observation, reports=()):
    """Choose one first hop using only a local view and admitted current reports.

    Args:
        observation: Bounded current local observation.
        reports: At most MAX_REPORTS admitted Report objects.

    Returns:
        A deterministic decision including a local-only sensitivity diagnostic.
    """
    local = _routes(observation["known_routes"])
    start, turn = observation["current_location"], observation["turn"]
    if not _identifier(start) or type(turn) is not int or turn < 1:
        raise ValueError("invalid_observation")
    if any(edge.split("->")[0] != start for edge in local):
        raise ValueError("nonlocal_observation")
    freight = observation["visible_freight"]
    if not isinstance(freight, list) or len(freight) > 32 or len(reports) > MAX_REPORTS:
        raise ValueError("input_limit")
    if any(
        not isinstance(item, dict)
        or not _identifier(item.get("id"))
        or not _identifier(item.get("destination"))
        for item in freight
    ):
        raise ValueError("invalid_freight")
    if len({item["id"] for item in freight}) != len(freight):
        raise ValueError("duplicate_freight")
    facts = {}
    ids = set()
    for report in reports:
        if (
            not isinstance(report, Report)
            or type(report.turn) is not int
            or report.turn != turn
            or not _identifier(report.message_id)
            or not _identifier(report.sender)
        ):
            raise ValueError("unadmitted_report")
        if report.message_id in ids:
            raise ValueError("duplicate_report")
        ids.add(report.message_id)
        if not isinstance(report.routes, tuple) or len(report.routes) > MAX_ROUTES:
            raise ValueError("invalid_routes")
        try:
            checked_routes = _routes(dict(report.routes))
        except (TypeError, ValueError):
            raise ValueError("invalid_routes") from None
        if len(checked_routes) != len(report.routes):
            raise ValueError("duplicate_route")
        for edge, status in checked_routes.items():
            facts.setdefault(edge, set()).add(status)
    merged = {
        edge: next(iter(states)) if len(states) == 1 else "unknown"
        for edge, states in facts.items()
    }
    merged.update(local)
    item = min(freight, key=lambda f: f["id"]) if freight else None
    path = _path(merged, start, item["destination"], local) if item else ()
    baseline = _path(local, start, item["destination"], local) if item else ()
    hop = path[1] if len(path) > 1 else None
    baseline_hop = baseline[1] if len(baseline) > 1 else None
    used = sorted(
        report.message_id
        for report in reports
        if any(edge not in local for edge, _ in report.routes)
    )
    return {
        "policy": POLICY,
        "freight_id": item["id"] if item else None,
        "path": list(path),
        "next_hop": hop,
        "reason": (
            "route"
            if hop
            else "at_destination"
            if path
            else "no_known_path"
            if item
            else "no_visible_freight"
        ),
        "consumed_message_ids": used,
        "local_only_next_hop": baseline_hop,
        "choice_changed": hop != baseline_hop,
    }
