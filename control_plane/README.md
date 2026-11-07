# switchboard / observation only

this first control-plane slice reads task claims and github artifact facts into
one local, frozen board. it does not schedule work, change tasks, post messages,
run providers, verify gate verdicts, or infer that an agent is alive.

## capture

requires python 3.11+, git and an already-authenticated `gh` cli. the collector
uses the existing github authentication; it never loads adaption credentials.
refresh the ledger ref deliberately before capture:

```sh
git fetch origin ledger
python3 control_plane/observer.py --repo . --output /tmp/swarm-observation-01
```

choose a new output directory for every capture. existing directories are
refused. open its `index.html` directly in a browser. `snapshot.json` is the
machine-readable counterpart. directories are mode 0700 and files 0600.
these contain team metadata: keep captures outside the public repository.
no web server or javascript is required. the page has no polling and does not
update itself on reload; capture again for new evidence.

`--ledger-ref` defaults to `origin/ledger`; `--github-repo` defaults to
`resonatingloop/swarmachines`. git resolves the supplied ref once to an exact
commit, then reads only that commit's `TASKS.md`. it never reads the working
ledger or `.env`, switches branches, fetches automatically, or writes source
state. github queries at most 200 prs across all states; hitting the limit is
explicitly labeled possibly truncated. an absent pr is unknown, not nonexistent.

## what the board means

- open / doing / blocked / done are the ledger author's reported states.
- owner strings are claims, not authenticated worker identities.
- task mentions of `PR #N` are textual references, not accepted dependencies.
- nonterminal tasks mentioning merged prs get reconciliation hints, never
  automatic closure. a follow-up task can correctly mention a merged pr.
- invalid rows are counted in diagnostics; duplicate ids are excluded. legacy
  rows without timestamps remain visible with freshness unknown.
- source failure produces unavailable status, not a misleading zero count.
- collection times are distinct from task update times. the sources are not
  captured atomically. local git ref freshness is not remote freshness.
- no leases, heartbeat, spend, verdict or runtime readiness is verified here.

snapshot v1 stores `observed_at`, `github_repo`, `sources`, `tasks`, `prs` and
`diagnostics`. source receipts include exact ledger revision/content hash and
per-source read time; github facts include each pr's exact head and state.
this is a projection format, not the future task/receipt dispatch contract.

## verification

```sh
python3 -m unittest control_plane.test_observer -v
ruff check control_plane
node control_plane/browser-check.mjs /tmp/swarm-observation-01/index.html
```

browser checks need node 22+ and chromium (`CHROME_BIN` or
`/usr/bin/google-chrome`). the harness uses an isolated temporary profile and
`--no-sandbox`, matching the existing repository harness; use it only in an
isolated test environment against this generated artifact. it deletes its
profile, preserves a desktop screenshot beside the capture, and checks reflow,
keyboard disclosure, external requests and runtime errors. 720px is a reflow
proxy, not proof of actual 200% browser zoom or screen-reader operation.

remove the generated capture to roll back local observation state. removing
`control_plane/` removes this slice without changing any dispatcher or ledger.
