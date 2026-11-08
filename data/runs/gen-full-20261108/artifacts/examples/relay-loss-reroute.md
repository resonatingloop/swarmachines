# Coordination Example: Reroute After Relay Loss

### 1. Context
*   **Turn:** 42 (Operational Phase: Mid-transit)
*   **Topology:** Ring (Nodes: A $\rightarrow$ B $\rightarrow$ C $\rightarrow$ D $\rightarrow$ A)
*   **Agents:** 
    *   `Freight_Carrier_01` (Mobile Agent)
    *   `Relay_Node_B` (Fixed Infrastructure)
    *   `Relay_Node_C` (Fixed Infrastructure)
    *   `Orchestrator` (Monitoring Agent)
*   **Situation:** `Freight_Carrier_01` is moving from Node A toward Node C. The intended path is via Node B. Suddenly, Node B suffers a hardware failure (Relay Loss), breaking the primary ring segment. The carrier is currently in "the fog"—an area of high latency and intermittent connectivity—and must decide whether to attempt a connection to the failing node or reroute through the longer path (A $\rightarrow$ D $\rightarrow$ C).

---

### 2. Message Exchange

**Message 1: Failure Detection (Relay_Node_B $\rightarrow$ Orchestrator)**
*Node B attempts a final heartbeat before complete shutdown.*

```json
{
  "msg_id": "err_992",
  "sender": "Relay_Node_B",
  "receiver": "Orchestrator",
  "timestamp": "2023-10-27T14:02:01Z",
  "type": "STATUS_CRITICAL",
  "payload": {
    "status": "OFFLINE",
    "reason": "HARDWARE_FAILURE",
    "last_known_loc": "Ring_Segment_AB"
  }
}
```

**Message 2: Coordination Request (Orchestrator $\rightarrow$ Freight_Carrier_01)**
*The Orchestrator broadcasts the topology change to the carrier to prevent it from entering the dead zone.*

```json
{
  "msg_id": "coord_441",
  "sender": "Orchestrator",
  "receiver": "Freight_Carrier_01",
  "timestamp": "2023-10-27T14:02:05Z",
  "type": "TOPOLOGY_UPDATE",
  "payload": {
    "event": "NODE_LOSS",
    "affected_node": "Relay_Node_B",
    "new_topology": "broken_ring",
    "suggested_reroute": ["A", "D", "C"]
  }
}
```

**Message 3: Acknowledgement & Intent (Freight_Carrier_01 $\rightarrow$ Orchestrator)**
*The carrier acknowledges the instruction and confirms the new trajectory.*

```json
{
  "msg_id": "ack_002",
  "sender": "Freight_Carrier_01",
  "receiver": "Orchestrator",
  "timestamp": "2023-10-27T14:02:12Z",
  "type": "ACTION_INTENT",
  "payload": {
    "action": "REROUTE",
    "new_path": ["A", "D", "C"],
    "estimated_delay_increase": "+15min"
  }
}
```

---

### 3. Action Resolution
Upon receiving the `TOPOLOGY_UPDATE`, `Freight_Carrier_01` executes a local pathfinding algorithm. It identifies that the link `B $\rightarrow$ C` is no longer reachable. To maintain connectivity, the agent aborts its approach to Node B and initiates a course correction toward Node D. The agent enters a "low-bandwidth mode" to minimize data transmission while navigating the longer segment of the ring.

### 4. Outcome and Analysis
*   **Outcome:** Successful reroute. The freight arrived at Node C via Node D. Total transit time increased by 18 minutes, but data integrity and carrier safety were maintained.
*   **Analysis:** The coordination was successful because the `Orchestrator` pushed the topology update *before* the carrier entered the communication shadow of the failed Node B. Had the carrier reached the proximity of Node B before the update, it would have entered a "blind state," potentially wasting fuel/energy attempting to handshake with a dead node. The use of JSON-structured intent allowed the Orchestrator to predict the delay and update the logistics schedule automatically.

---

### 5. Provenance Note
**Log Trace ID:** `PROV-RING-42-B-FAIL`  
**Data Integrity:** Hash `sha256:e3b0c442...` verified.  
**Source:** Distributed Ledger (Fog-Edge Log)  
**Timestamp:** 2023-10-27T14:15:00Z