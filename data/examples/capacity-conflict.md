# Example: Resolving Capacity Contention

## Opening Context

The simulation has reached Turn 6. The environment is configured with a **MESH** topology, though the current active congestion is concentrated along a specific segment of the network that mimics a ring structure between nodes A, B, C, and D. The network is currently under heavy load due to a recent surge in freight generation. At this moment, the primary bottleneck is the West-to-East corridor connecting Agent B and Agent C, which has a maximum throughput capacity of 2 units per turn.

The tension arises from a critical capacity contention. Agent B is attempting to move a high-priority medical supply crate, while Agent C is attempting to move a heavy industrial component. Simultaneously, Agent D is requesting access to the same route to clear a backlog. With three distinct freight items demanding access to a route that can only accommodate two, the agents face a "deadlock or delay" scenario. Without explicit coordination, the agents risk a collision of requests that could lead to inefficient buffer utilization or systemic gridlock.

## Message Exchange

Agent B recognizes the congestion immediately through its local sensors. Its internal reasoning engine calculates that if it does not secure the route now, the medical supply will miss its delivery window, incurring a massive penalty. Agent B decides to initiate a coordination protocol by broadcasting its priority status to its immediate neighbors. Because of the MESH topology, B can reach C directly, but it also sends a signal through D to ensure the entire local cluster is aware of the impending contention.

Agent B sends the following coordination request to Agent C:

```json
{
  "turn": 6,
  "sender": "agent_b",
  "receiver": "agent_c",
  "message_type": "BID_PRIORITY",
  "payload": {
    "route_segment": "W-E_04",
    "requested_capacity": 1,
    "priority_level": 9,
    "cargo_type": "medical_supply",
    "deadline_turn": 8
  },
  "reasoning": "High-priority cargo detected. Attempting to secure capacity before segment saturation."
}
```

Agent C receives this message. Agent C’s internal logic evaluates its own cargo: a heavy industrial component with a priority of 5. Agent C realizes that yielding the route to Agent B is the mathematically optimal move to minimize total system penalty, even though it means delaying its own cargo. However, Agent C also notes that Agent D is attempting to push through. Agent C responds to Agent B to confirm the negotiation and broadcasts a "yield" signal to the local mesh to prevent Agent D from attempting a brute-force entry.

```json
{
  "turn": 6,
  "sender": "agent_c",
  "receiver": "agent_b",
  "message_type": "BID_ACCEPTANCE",
  "payload": {
    "route_segment": "W-E_04",
    "status": "YIELDING",
    "allocated_capacity_to_other": 1,
    "expected_delay_turns": 2
  },
  "reasoning": "Agent B priority (9) exceeds Agent C priority (5). Yielding to optimize global penalty scores."
}
```

Agent D, receiving the implicit signal of the negotiation through the mesh, realizes the capacity is being partitioned. It sends a final message to the cluster to update its own routing intention, preventing a redundant request that would have triggered a conflict resolution error.

```json
{
  "turn": 6,
  "sender": "agent_d",
  "receiver": "all",
  "message_type": "STATUS_UPDATE",
  "payload": {
    "intended_route": "N-S_02",
    "capacity_requirement": 1,
    "status": "REROUTING"
  },
  "reasoning": "Observed capacity contention on W-E_04. Diverting to alternate N-S route to avoid congestion."
}
```

## Action Resolution

With the negotiation concluded, the agents move from the communication phase to the execution phase. The simulation engine validates these actions against the physical constraints of the MESH topology. Agent B and Agent D (who successfully rerouted) are granted the two available slots on the W-E_04 segment. Agent C, having agreed to yield, must execute a "wait" action, holding its freight in its local buffer.

The validated action set for the turn is processed as follows:

```json
[
  {
    "agent": "agent_b",
    "action": "MOVE_FREIGHT",
    "target_route": "W-E_04",
    "capacity_consumed": 1,
    "validation": "SUCCESS"
  },
  {
    "agent": "agent_d",
    "action": "MOVE_FREIGHT",
    "target_route": "N-S_02",
    "capacity_consumed": 1,
    "validation": "SUCCESS"
  },
  {
    "agent": "agent_c",
    "action": "HOLD_IN_BUFFER",
    "target_route": null,
    "capacity_consumed": 0,
    "validation": "SUCCESS"
  }
]
```

The execution is seamless. Because the agents coordinated via the MESH network, there was no "collision" of requests at the controller level. The simulation engine accepted the instructions because the total `capacity_consumed` on the contested segment (W-E_04) did not exceed the limit of 2.

## Outcome

The turn concludes successfully. Agent B’s medical supply moves one node closer to its destination, maintaining its high-priority trajectory. Agent D successfully bypasses the bottleneck by utilizing the N-S route, effectively spreading the load across the mesh. Agent C remains stationary; while this results in a minor local penalty for Agent C, it prevents a catastrophic system-wide delay that would have occurred if all three agents had attempted to force entry simultaneously.

Through this process, the agents have updated their internal "congestion maps." Agent C now marks the W-E_04 segment as "High Contention" for the next three turns, and Agent D has learned that the N-S corridor is a viable relief valve for West-East bottlenecks. This turn has reinforced the value of proactive priority-based negotiation over reactive collision avoidance.

## Analysis

This interaction illustrates the **Priority-Based Yielding** coordination pattern. In a MESH topology, the agents benefited from multiple communication paths, allowing Agent B to communicate its intent and Agent D to observe the negotiation, thereby facilitating a more intelligent rerouting decision. If this had occurred in a **STAR** topology, all messages would have had to pass through a central hub, increasing latency and creating a single point of failure for the coordination. If it had been a **RING** topology, the "broadcast" from Agent B might have taken longer to reach Agent D, potentially causing Agent D to commit to the W-E route before the negotiation was finalized. The MESH topology allowed for the rapid, decentralized consensus required to resolve the capacity contention efficiently.

***

<!-- MODEL_GENERATED: gemma-4-26b-a4b-it @ 2026-11-08T03:56:35.313847+00:00 -->
<!-- RUN: gen-full-20261108 -->
<!-- EXAMPLE: capacity-conflict -->
<!-- TOPOLOGY: mesh -->

This example illustrates expected coordination patterns. Actual agent behavior
may vary based on implementation and simulation dynamics.

---
*Provenance: model-generated narrative (gemma-4-26b-a4b-it @ 2026-11-08T04:00:02.216371+00:00, call 33).*
