# job evidence and offline measures

status: implemented; independent review pending

[accepted spec012](../specs/012-job-evidence-and-measures.md) adds job audit
records to explicit route-gossip freight runs. this is instrumentation and
analysis, not authorization for a formal experiment or a change to the world.

## local use

```sh
python3 runtime/runner.py --world freight --policy route-gossip-v1 \
  --seed 42 --turns 16 --topology bidirectional-ring \
  --disturbance peer-mute:8:c --output /tmp/new-job-episode.jsonl
python3 -m analysis.measure_episode /tmp/new-job-episode.jsonl \
  --output /tmp/new-job-measures.json
```

the runner retains its existing overwrite behavior: choose a new episode path.
the analyzer refuses an existing output and creates its result with mode 0600.
input must be a regular non-symlink UTF-8 file, at most 10,000,000 bytes,
20,000 events, 10,000 characters per line. duplicate JSON keys, nonfinite
numbers, malformed lines and schema violations are rejected; no lines are
silently discarded. jsonschema is the existing validation dependency.

exit 0 means structurally valid analysis (individual measures can still be
unavailable/undefined/censored); exit 1 means invalid evidence, with a
categorical result artifact; exit 2 means input/output could not be used.
terminal output contains only status and original-byte sha256, not raw input.
source hashes establish identity, not producer truth or tamper resistance.

## audit records

only the new policy mode records `job_evidence_version: 1` and `horizon_turns`
in run.config. `jobs.initialized` snapshots actual initial job identities,
freight mapping, origins/destinations and pending state at release turn 0.
`job.completed` joins the actual world job with a successful action, only on
transition to delivered. run.end snapshots terminal job identities/states and
marks a completed horizon. snapshots are global audit evidence and never
enter agent observations, messages or selector inputs.

legacy output stays byte-identical. new-policy event sequence numbers,
timestamps and observation sequence references shift because audit records
are added; the compared action/world/observation/message/decision trajectories
remain identical after accounting for those mechanical changes.

## result meanings

- `completion`: unique verified delivered jobs / actual released roster.
  includes numerator, denominator, ratio and supporting sequences. zero jobs
  gives `undefined`, with 0/0 retained and value null.
- `resumption`: first verified completion at/after observed peer-mute:c at
  start of turn 8, matching configuration. completion at turn 8 yields zero;
  completion before turn 8 does not count. witnesses and sequences are retained.
- complete consistent logs with no later completion give `right_censored`,
  value null and observed-through/follow-up fields. truncated logs give
  `unavailable`, not censoring. wrong/absent intervention leaves resumption
  unavailable without discarding an independently valid primary measure.
- contradictory identities, duplicate completions, failed-action completions,
  delivered commits without completion evidence, terminal disagreements and
  incomplete declared turn coverage give top-level `invalid`.
- old logs lacking versioned job evidence have unavailable job measures.
  `recovery_interval_turns` is never used. missing provider usage, failure
  manifests and fallback telemetry remain unavailable.

traffic counts retain per-agent records and supporting sequences in windows
1–7 and 8–16, with expected exposure and actually observed turns. they are
record counts, not influence. action counts distinguish validation rejection
from failed application and preserve reasons/proposal denominator. no pooled
statistics, morphology labels, runtime imports, resimulation or network calls.

## verification

```sh
PYTHONPATH=runtime python3 -m unittest analysis.test_measure_episode \
  runtime.test_route_gossip runtime.test_gossip_integration -v
python3 runtime/test_runner.py
node --test viewer/replay.test.cjs viewer/comparison.test.cjs viewer/evidence.test.cjs
```

fixtures are fictional. the positive runtime roundtrip reconciles analyzer
counts with the real world object; that is an integration check, not a formal
comparison. the independent reference base for noninterference is merged
policy commit `18218e706cf950c89161b6588166d14529f76726`.
