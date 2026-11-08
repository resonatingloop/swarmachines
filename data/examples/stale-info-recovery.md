| Time | Agent | Type | Payload |
|:---|:---|:---|:---|
| 10:01 | **A** | STATUS | Route: R-402 | Freight: F-99 | Status: ACTIVE |
| 10:02 | **B** | REPORT | Bridge: BR-12 | Status: CLOSED (Weight Limit Violation) |
| 10:03 | **C** | ALERT | Bridge: BR-12 | Status: REOPENED (Repaired) |
| 10:05 | **A** | CMD | Route: R-402 | Action: REROUTE (Avoid BR-12) |
| 10:05 | **D** | ACK | Route: R-402 | Action: REROUTE confirmed. New Path: R-405 |
| 10:06 | **A** | ERROR | Bridge: BR-12 | Reason: Stale Report (ID: B-001) |
| 10:06 | **A** | CMD | Route: R-402 | Action: REVERT (Resume Original Route) |
| 10:07 | **D** | ACK | Route: R-402 | Action: REVERT confirmed. Resuming via BR-12 |
| 10:07 | **B** | LOG | Bridge: BR-12 | Error: Report timestamp mismatch. Data outdated. |

---
*Provenance: model-generated via adaption (gemma-4-26b-a4b-it, 2026-11-08); kind: example exchange; seed draft: n/a (fresh). NOT observed experimental evidence.*
