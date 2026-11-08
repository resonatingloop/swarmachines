# Frozen run manifest — spec006 formal pair, seed 42 (scripted, zero provider calls)

- runtime commit: `0f84075` (spec006 Gate-1 anchor; master at run time)
- policy: `route-gossip-v1` (declared; requires freight world)
- interpreter: Python 3.14.9 (harness venv); deps: jsonschema per requirements.txt
- schema: `runtime/schema/events.schema.json`
- provider mode: none — zero model/provider calls (scripted policy run)
- agents: a, b, c, d (route-gossip policy roles; ring order a-b-c-d-a)
- seed: 42 (single deterministic scenario replicate; exact reruns test
  reproducibility, not sample size)
- horizon: 16 turns
- disturbance: `peer-mute:8:c` — mute agent c's communication starting at turn 8
  through turn 16; local routing actions continue; mute verified applied at turn 8
  in both arms; agent c delivered 0 messages turns 8-16 in both arms
- physical world: freight world initialized per seed 42; world-init evidence lives
  in each artifact's `world.init` event (hash per-artifact below; do NOT use
  delivery_config_sha as a physical-world hash)
- stop condition: horizon (both arms `termination: completed`, `horizon_turns: 16`)

## Condition manifest

| condition id | topology | arm order | artifact | sha256 (first 16) | events | exit |
|---|---|---|---|---|---|---|
| spec006-seed42-mesh-mutec-t8 | mesh (fully connected) | 1st | runs/spec006/spec006-seed42-mesh-mutec-t8/episode.jsonl | 432dbf9f7704e7f5 | 414 | 0 |
| spec006-seed42-ring-mutec-t8 | bidirectional ring (a-b-c-d-a) | 2nd | runs/spec006/spec006-seed42-ring-mutec-t8/episode.jsonl | 53a843e40267da13 | 386 | 0 |

- execution order: mesh-first (spec rule; alternate across seeds — next seed is ring-first)
- full sha256:
  - mesh: 432dbf9f7704e7f580589ddf16bc0284c4a4aadeef793cf4a24958bacf00c613
  - ring: 53a843e40267da13a3157f93de1a7dc15960ee9e59af9c9768a181a94c362bc6

## Invocations (verbatim, run from repo root at 0f84075)

```
python3 runtime/runner.py --seed 42 --topology mesh --turns 16 --world freight --policy route-gossip-v1 --disturbance peer-mute:8:c --agents a,b,c,d --output runs/spec006/spec006-seed42-mesh-mutec-t8/episode.jsonl
python3 runtime/runner.py --seed 42 --topology bidirectional-ring --turns 16 --world freight --policy route-gossip-v1 --disturbance peer-mute:8:c --agents a,b,c,d --output runs/spec006/spec006-seed42-ring-mutec-t8/episode.jsonl
```

## Headline observation (from the artifacts; measures computed downstream)

Both arms terminated `completed` at horizon 16 with all 4 jobs `delivered`.
The topology difference under this scripted policy shows up in event volume
(mesh 414 vs ring 386) and message traffic, not in job completion. Per the
spec: zero/negative/mixed outcomes are valid; per-run numerators and
ring-minus-mesh differences are computed downstream (T-007 measure mapping).
