#!/usr/bin/env python3
"""
freight-in-the-fog world module

implements:
- graph-based delivery world with depots, hubs, routes (open/closed)
- freight items with lifecycle: pending → in-transit → delivered (or stuck)
- partial observations per agent (local view only)
- route validation against world state
- deterministic state transitions from seed
"""

import random
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Route:
    """A route between two locations with optional bridge."""

    from_loc: str
    to_loc: str
    status: str = "open"  # "open" or "closed"
    bridge: str | None = None
    capacity: int = 3  # Max concurrent freight on this route
    current_load: int = 0  # Current freight count on this route

    def key(self) -> str:
        """Canonical key for route lookup."""
        return f"{self.from_loc}->{self.to_loc}"


@dataclass
class FreightItem:
    """A freight item being transported."""

    item_id: str
    freight_type: str  # "med-kit", "supplies", "equipment"
    origin: str
    destination: str
    current_location: str
    state: str = "pending"  # "pending", "in-transit", "delivered", "stuck"


@dataclass
class DeliveryJob:
    """A delivery job tracking a freight item's progress."""

    job_id: str
    freight_id: str
    origin: str
    destination: str
    state: str = "pending"  # "pending", "in-transit", "delivered", "stuck"
    via_path: list[str] = field(default_factory=list)


class FreightWorld:
    """
    Freight-in-the-fog world state.

    Manages:
    - Graph of depots/hubs connected by routes
    - Freight items and delivery jobs
    - Partial observations per agent
    - Route validation and action application
    """

    def __init__(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)

        # Initialize world graph
        self.depots = ["west", "east", "south"]
        self.hubs = ["relay-a"]
        self.all_locations = self.depots + self.hubs

        # Initialize routes (bidirectional)
        self.routes: dict[str, Route] = {}
        self._init_routes()

        # Initialize freight items
        self.freight_items: dict[str, FreightItem] = {}
        self.delivery_jobs: dict[str, DeliveryJob] = {}
        self._init_freight()

        # Agent-to-depot assignment (for partial observations)
        self.agent_depots: dict[str, list[str]] = {
            "a": ["west"],
            "b": ["east"],
            "c": ["south"],
            "d": ["relay-a"],
        }

        # Event sequence counter for determinism
        self.event_seq = 0

    def _init_routes(self) -> None:
        """Initialize the route graph."""
        # West <-> East
        self.routes["west->east"] = Route("west", "east", "open")
        self.routes["east->west"] = Route("east", "west", "open")

        # East <-> South (via bridge)
        self.routes["east->south"] = Route("east", "south", "open", "east-bridge")
        self.routes["south->east"] = Route("south", "east", "open", "east-bridge")

        # West <-> South (direct)
        self.routes["west->south"] = Route("west", "south", "open")
        self.routes["south->west"] = Route("south", "west", "open")

        # Hub connections (relay-a is central)
        for depot in self.depots:
            self.routes[f"{depot}->relay-a"] = Route(depot, "relay-a", "open")
            self.routes[f"relay-a->{depot}"] = Route("relay-a", depot, "open")

    def _init_freight(self) -> None:
        """Initialize freight items and delivery jobs."""
        # Create some initial freight items at different depots
        freight_configs = [
            ("f-001", "med-kit", "west", "south"),
            ("f-002", "supplies", "east", "west"),
            ("f-003", "equipment", "south", "east"),
            ("f-004", "med-kit", "relay-a", "west"),
        ]

        for item_id, freight_type, origin, destination in freight_configs:
            item = FreightItem(
                item_id=item_id,
                freight_type=freight_type,
                origin=origin,
                destination=destination,
                current_location=origin,
                state="pending",
            )
            self.freight_items[item_id] = item

            job = DeliveryJob(
                job_id=f"j-{item_id}",
                freight_id=item_id,
                origin=origin,
                destination=destination,
                state="pending",
            )
            self.delivery_jobs[job.job_id] = job

    def get_freight_at_location(self, location: str) -> list[FreightItem]:
        """Get all freight items at a given location."""
        return [
            item
            for item in self.freight_items.values()
            if item.current_location == location
            and item.state not in ("delivered", "stuck")
        ]

    def get_adjacent_locations(self, location: str) -> list[str]:
        """Get all locations reachable from the given location via open routes."""
        adjacent = []
        for route in self.routes.values():
            if route.from_loc == location and route.status == "open":
                adjacent.append(route.to_loc)
        return sorted(adjacent)

    def observe(self, agent_id: str, turn: int, rng: random.Random) -> dict[str, Any]:
        """
        Generate partial observation for an agent.

        Returns a dict with:
        - visible_freight: freight items at agent's assigned depots
        - adjacent_locations: locations reachable from agent's current position
        - known_routes: status of routes the agent can see
        """
        assigned_depots = self.agent_depots.get(agent_id, ["west"])
        current_location = assigned_depots[0]

        # Get visible freight
        visible_freight = [
            {
                "id": item.item_id,
                "type": item.freight_type,
                "destination": item.destination,
            }
            for item in self.get_freight_at_location(current_location)
        ]

        # Get adjacent locations
        adjacent = self.get_adjacent_locations(current_location)

        # Get known route statuses (routes from current location)
        known_routes = {
            route.key(): route.status
            for route in self.routes.values()
            if route.from_loc == current_location
        }

        return {
            "current_location": current_location,
            "visible_freight": visible_freight,
            "adjacent_locations": adjacent,
            "known_routes": known_routes,
            "turn": turn,
        }

    def validate_action(self, action: dict) -> tuple[bool, str]:
        """
        Validate an action against world state.

        Returns (legal, reason) tuple.
        Rejection reasons are sanitized - never echo raw hostile input.
        """
        try:
            if action.get("kind") != "route_freight":
                return False, "unknown action kind"

            freight_id = action.get("freight_id")
            if not freight_id or freight_id == "none":
                return True, ""  # No-op is always legal

            # Validate freight_id is a valid string key
            if not isinstance(freight_id, str):
                return False, "invalid freight_id format"

            if freight_id not in self.freight_items:
                return False, "freight not found"  # Don't echo the ID

            freight = self.freight_items[freight_id]
            if freight.state in ("delivered", "stuck"):
                return False, "freight already completed"  # Don't echo state

            # Parse via path
            via = action.get("via", "")
            if not isinstance(via, str) or "->" not in via:
                return False, "invalid via path format"  # Don't echo the via

            from_loc, to_loc = via.split("->", 1)

            # Verify freight is at from_loc
            if freight.current_location != from_loc:
                return (
                    False,
                    "freight not at specified location",
                )  # Don't echo locations

            # Verify route exists and is open
            route_key = f"{from_loc}->{to_loc}"
            if route_key not in self.routes:
                return False, "route does not exist"  # Don't echo route key

            if self.routes[route_key].status != "open":
                return False, "route is closed"

            # Check route capacity
            if self.routes[route_key].current_load >= self.routes[route_key].capacity:
                return False, "route at capacity"  # Don't echo numbers

            return True, ""
        except (TypeError, AttributeError, KeyError):
            # Fail closed on any unexpected error
            return False, "validation error"

    def apply_action(
        self, action: dict, agent_id: str
    ) -> tuple[bool, str, dict | None]:
        """
        Apply an action to the world state.

        Returns (success, reason, world_change) tuple.
        world_change is a dict describing what changed (for event logging).
        Fails closed on malformed input - validate_action should be called first.
        """
        try:
            if action.get("kind") != "route_freight":
                return False, "unknown action kind", None

            freight_id = action.get("freight_id")
            if not freight_id or freight_id == "none":
                return True, "", None  # No-op

            # Validate freight_id is hashable
            if not isinstance(freight_id, str):
                return False, "invalid freight_id", None

            if freight_id not in self.freight_items:
                return False, "freight not found", None

            freight = self.freight_items[freight_id]

            # Parse via path - fail closed on malformed
            via = action.get("via", "")
            if not isinstance(via, str) or "->" not in via:
                return False, "invalid via", None
            from_loc, to_loc = via.split("->", 1)

            route_key = f"{from_loc}->{to_loc}"

            # Move freight
            old_location = freight.current_location
            freight.current_location = to_loc

            # Update route loads
            # Decrement load on the route freight is leaving (it's no longer on that route)
            # Increment load on the route freight is entering
            # Note: freight is "on a route" only while in transit; when it arrives at a location,
            # it's no longer on the previous route

            # Find and decrement the route the freight was on (the route that brought it to old_location)
            # This is the route that ends at old_location (to_loc == old_location)
            for route in self.routes.values():
                if route.to_loc == old_location and route.current_load > 0:
                    # Decrement this route's load - freight is leaving it
                    route.current_load -= 1
                    break  # Only decrement one route (the one freight arrived on)

            # Increment load on the new route
            if route_key in self.routes:
                self.routes[route_key].current_load += 1

            # Update state
            if to_loc == freight.destination:
                freight.state = "delivered"
                job = self.delivery_jobs.get(f"j-{freight_id}")
                if job:
                    job.state = "delivered"
            else:
                freight.state = "in-transit"
                job = self.delivery_jobs.get(f"j-{freight_id}")
                if job:
                    job.state = "in-transit"
                    job.via_path.append(to_loc)

            self.event_seq += 1

            world_change = {
                "what": "freight moved",
                "freight_id": freight_id,
                "from": old_location,
                "to": to_loc,
                "new_state": freight.state,
            }

            return True, "", world_change
        except (TypeError, AttributeError, KeyError, ValueError):
            # Fail closed on any unexpected error
            return False, "apply error", None

    def get_delivery_stats(self) -> dict[str, int]:
        """Get current delivery statistics."""
        stats = {"pending": 0, "in_transit": 0, "delivered": 0, "stuck": 0}
        for job in self.delivery_jobs.values():
            if job.state == "pending":
                stats["pending"] += 1
            elif job.state == "in-transit":
                stats["in_transit"] += 1
            elif job.state == "delivered":
                stats["delivered"] += 1
            elif job.state == "stuck":
                stats["stuck"] += 1
        return stats
