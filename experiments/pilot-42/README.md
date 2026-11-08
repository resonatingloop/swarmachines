# seed-42 pilot / candidate readiness packet

status: blocked on independent review; no formal attempts started

runtime pinned: `0f84075c58c5f52c43fe7888d58ff51c9de18773` (merged pr #34).
this packet implements the pre-run readiness step of
[accepted spec006](../../specs/006-formal-experiment-handoff.md). it does not
change the protocol or claim results. the runtime is checked out in an isolated
clone; no shared teammate worktree was modified.

## artifacts

- [candidate manifest](manifest.candidate.json): two planned conditions,
  complete invocations, topology adjacency, world/job identities, source hashes,
  interpreter/dependency versions and explicit pending gate.
- [readiness evidence](readiness.json): 28 focused analyzer/policy tests passed
  in a fresh allowlisted child environment without provider credentials. a
  python audit hook refused socket.connect/getaddrinfo/sendto; no such events
  occurred. these are unit/integration fixtures, not formal episode attempts.

candidate manifest sha256:
`c069507baf98dc9f4774fcfd6d3a10d62a7039ad3a4a190a4d16b4187698d6fb`.
verify original bytes with `sha256sum experiments/pilot-42/manifest.candidate.json`.
world/job/rng hashes use UTF-8 `json.dumps(value, sort_keys=True,
separators=(',', ':'))`, then sha256. the full initial world and roster are
included for independent recomputation. initialization is performed separately
for each arm; the hashes agree. release_turn=0 is explicitly a derived constant
from construction before turn 1, not a DeliveryJob field.

## readiness disposition

- integrated policy/job runtime and exact commands: pinned.
- world/job initialization and action-rng controls: equal between arms.
- directed adjacency: mesh 12 links; ring 8 links, a–b–c–d–a in both directions.
  applying peer-mute removes all c send/receive links. policy integration tests
  verify the turn-8 boundary and continuing local decisions.
- actual job evidence and policy capability: approved mapping and merged code;
  the 28 focused tests pass again on the pinned merge.
- zero-provider operation: explicit route-gossip freight mode; readiness child
  environment excludes credentials and has no observed network activity.
- independent security disposition of #34: **pending**. the room records an
  explicit post-merge-fix-forward exception, not a passed security gate.
  merge notification: message `1568829822090743840`; gate request:
  `1568832683281223701` in the approved work-sharing channel.

therefore the manifest is **candidate_not_frozen**. planned execution order is
mesh then ring at seed 42. actual execution order and attempts are empty. no
formal pair, rerun, batch table or performance finding exists in this packet.
legacy freight no-op accounting is a separate teammate fix; route-gossip's
explicit wait path emits no invalid synthetic freight proposal. no legacy-mode
invocation is proposed here.

## next action after the gate clears

1. anchor exact-head independent verifier/security verdicts for #34 and confirm
   no resulting runtime/analyzer fix changes this pin. if a fix is required,
   construct a new candidate and recheck hashes; retain this candidate.
2. validate the manifest against the settled source, then create a separately
   named frozen manifest with its own hash. do not relabel this candidate in
   place as though it had been approved earlier.
3. create a fresh private output directory per condition/attempt before running
   the exact pinned invocation in the clean environment. the runner itself can
   overwrite its target, so reject any existing attempt path first.
4. retain output bytes, exit status, start/end time, stderr/failure details,
   event count, terminal status and sha256 for every attempt. validate/analyze
   complete episodes; exact reruns get separate output directories and do not
   increase sample size. stop on failures rather than silently retrying.
5. only after the pilot and exact reruns pass, consider the already accepted
   small seed batch. preserve limitations: no no-mute control, deterministic
   policy, few scenarios, and capability does not imply benefit.

focused checks used:

```sh
PYTHONPATH=runtime python3 -m unittest analysis.test_measure_episode \
  runtime.test_route_gossip runtime.test_gossip_integration -q
```

no credentials, raw chats or private environment values are included. this
packet supports report methods/reproducibility preparation, not a results section.
