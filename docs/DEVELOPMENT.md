# swarmachines / development

> continuity role: operational procedure
> status: current for the proposal and spec review
> last verified: 2026-11-07
> owns: local preview, maintenance checks, and recovery
> update when: the entry point, dependencies, or validation path changes

## what runs

[plans/index.html](../plans/index.html) is the original self-contained presentation:
html, css, svg illustrations, and browser javascript in one file. it has no
package manifest, install step, build step, backend, or configured provider
integration. a modern browser is sufficient to open the file directly.

the optional http preview uses python 3; python 3.12.3 was exercised here.
there is no environment configuration to load for the proposal. `.env` is
outside this workflow and must not be read or sourced by agents.

## written-spec review

[plans/spec-review/index.html](../plans/spec-review/index.html) is a separate
local html bundle built with the owner's attention-aperture skill. it reads
only neighboring files and works directly from `file://`. javascript is needed
for this interactive review; the canonical markdown remains readable separately.

the [authored input](../plans/spec-review-data.json) represents the draft's
twelve steps and fifteen review choices. its twenty-one passages include the
complete source wording with line locators, a base revision and a sha256 of
the working source. the builder refuses a changed source hash or mismatched
excerpt; reconcile meaning and correspondence before regenerating the data.
an extracted dependency is reading guidance, not an accepted contract.

to rebuild, supply the skill checkout and an empty, real destination:

```sh
node /home/resonatingloop/.agentic/attention-aperture/scripts/build-aperture.mjs --self-test
node scripts/build-spec-review.mjs --skill-root /home/resonatingloop/.agentic/attention-aperture --output /tmp/swarmachines-review-new
```

the second command refuses a nonempty destination. use another destination
for another build. inspect that bundle before replacing the generated files
under `plans/spec-review/`. readers need neither node nor the skill checkout.
project-owned additions live in `plans/spec-review-assets/`: source navigation,
small-screen step selection, and layout/copy adjustments. the shared skill
repository is not modified. removing this bundle and its entry links reverses
the presentation addition without changing the proposed experiment.

after editing, check all phase fields, exact source excerpts and both directions
of correspondence; filters, review marks, clear/next-unmarked, clipboard success
and refusal, and reset on reload. verify the workload distinction remains
visible. inspect desktop, 320px and enlarged layouts, keyboard focus and reduced
motion. check that the local-file page requests only bundle files and writes
no browser storage. real browser zoom and assistive-technology output remain
separate manual checks from viewport/device-scale emulation.

the initial browser pass used headless chrome at 1440px and 320px, plus a
720-css-pixel / 2x-device-scale view equivalent to the reflow area of 200% at
1440px. native clipboard copy succeeded; refusal handling was also exercised.
all twelve phase accounts and exact source counterparts matched the data;
no runtime errors, external page requests, storage writes or horizontal page
overflow were observed. this verifies the artifact, not the proposed runtime
or a reader's understanding.

## preview

from the repository root:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory plans
```

open [the local preview](http://127.0.0.1:8765/) in a browser. the directory is
deliberately `plans`: the server should serve the presentation directory,
not the repository root. stop the owned server with ctrl+c when finished.

in a second terminal, this checks the served entry point:

```sh
curl --fail --silent --output /dev/null --write-out '%{http_code}\n' http://127.0.0.1:8765/
```

expect `200`. a successful response proves delivery of the file, not correct
interaction. use the browser checks below for behavior. opening
`plans/index.html` directly is also supported and requires no server.

## focused browser checks

after changing the presentation, exercise the affected behavior:

1. open the page and see “what shape does a swarm take under pressure?”.
2. inspect all four swim lanes. each button selects one dossier; this does
   not assign a person or save a preference.
3. switch the network between intact, lost relay, and possible repair. the
   caption and diagram must agree, and repair must remain labeled hypothetical.
4. the workload starts at 768 calls: 4 agents × 16 turns × 4 conditions ×
   3 repeats. changing agents to 5 yields 960. this estimates call count,
   not price, and assumes one call per agent per turn before retries.
5. reach buttons and sliders by keyboard; use arrow keys on a slider and
   check its visible value and total.
6. inspect a narrow layout, including 320px, and desktop. lane names and
   controls must fit without horizontal overflow.
7. with reduced motion enabled, the moving packet dots should be omitted.
8. print preview should contain all four lane dossiers, regardless of the
   selected lane. with javascript disabled, the four text summaries remain
   readable and interactive-only controls are hidden.

the presentation has no committed automated test suite of its own; the
runtime and viewer carry their own committed suites — `python3
runtime/test_runner.py` and `node --test viewer/*.test.cjs` — which do not
exercise the page. earlier browser verification scripts and screenshots were
temporary aids, not repository dependencies. do not require a returning
teammate to recover files from `/tmp`.

## documentation checks

the owner-selected continuity skill provides a checker outside this repository.
on the owner's current machine, run:

```sh
python3 /home/resonatingloop/.resonance/exoresonance/repository-continuity/skills/manage-project-docs/scripts/check_docset.py .
```

it checks the core documents, local markdown links, template residue, spec
statuses when present, and checkpoint freshness. it does not verify browser
behavior, provider integration, or research findings. teammates without this
skill can review the authority map, links, date, and open decisions manually;
the checker is not needed to open the proposal.

the supplied checker expects title-case checkpoint headings. this repository
uses the owner's lowercase prose style, so its six “unexpected heading”
warnings for `STATUS.md` are a known casing mismatch. errors, other warnings,
or a changed warning count require inspection. keep the lowercase style and
report the mismatch; do not modify the shared skill just to clear this result.

## state and recovery

the coding-agent workroom connection is separate from the proposal and future
experimental runtime. [discord setup](DISCORD.md) records its machine-local
launcher, room card, current access evidence, and remaining connection steps.

- the proposal's controls change the current page only. reload resets them.
  there is no application database or saved lane selection to restore.
- a pdf saved from the browser is a separate user-chosen export; edits still
  belong in the html source.
- if the browser opens a directory listing, use the preview command above.
  the entry point is `plans/index.html`, not a root-level `index.html`.
- if port 8765 is occupied, choose another local port, such as 8766, and use
  the matching url. do not terminate an unknown listener.
- if a connected browser-control tool is unavailable, a human can perform the
  same browser checks. isolated headless chrome was used for local verification;
  it is not part of the project's runtime.
- the checkout began without commits and with an unrelated untracked `.env`.
  inspect git status before any version-control work. stage explicit intended
  files only when staging is requested; do not sweep up unrelated local files.

## smoke outcome regression checks

`python3 -m unittest runtime.test_smoke_outcomes -v` uses synthetic adapter/SDK
modules and makes no provider calls. it covers each failed call position,
multiple failures, complete success, and the missing-key path without an SDK.

the optional live smoke command reports `error` and exits 1 when any caught
provider call fails; a missing key remains `blocked` with exit 2. `calls_made`
counts attempted adapter invocations, including failures, not underlying SDK
requests or retries. call 1 still aborts on failure; later failures retain all
result rows and expose the first error at top level for the CLI. provider
configuration and retry policy are unchanged by this accounting fix.

## task10 response and trace repair

the accepted repair under
[`openspec/changes/repair-task10-observability/`](../openspec/changes/repair-task10-observability/)
uses adaption `0.19.x` and langfuse `5.x`. install them into an isolated
environment from `requirements.txt`; do not install from a host-specific sdk
directory.

the provider-free matrix and budget proof is:

```sh
python -m dataset_pack.task10 --credit-ceiling 10
```

it must report 1,920 planned calls, a 4,096-token per-call ceiling, no provider
calls, and a maximum reservation below 10 credits. the focused offline tests
are:

```sh
pytest -q runtime/test_task10_observability.py dataset_pack/test_run.py \
  dataset_pack/test_task10.py runtime/test_tracer.py
```

live task10 execution additionally requires
`--langfuse-credentials <private-file>`. the file is read directly rather
than sourced and must be an owner-owned, non-symlink regular file with mode
`0600`; it contains exactly `LANGFUSE_BASE_URL`, `LANGFUSE_PUBLIC_KEY`,
and `LANGFUSE_SECRET_KEY`. do not print it or add its values to process-wide
environment variables.

tracing exports hashes and bounded metadata only. every provider attempt owns
one generation, flushes before the next paid call, and stops the batch if trace
creation or export fails. a response becomes a sealed `model.call` only when
status is `completed` and visible output is nonempty. a rejected attempt
instead becomes exactly one source-linked `model.call.failed` event, and the
failed partial run is sealed before capture. package creation recomputes every
persisted event seal before it writes a manifest or copies raw runs.

offline success does not authorize langfuse authentication, synthetic export,
an adaption diagnostic call, runs 005–015, packaging, upload, or publication.
those gates remain explicit and sequential.

## e2e pipeline test

`python3 runtime/test_e2e_pipeline.py` exercises the full pipeline from a fresh
clone:

1. **Runner execution** with `--world freight` producing episode JSONL
2. **Schema validation** via `verify_events.py`
3. **Determinism check** (two runs, byte-identical log)
4. **Viewer replay readiness** (replay.js loader contract offline check)
5. **Trace-layer smoke** (Langfuse-compatible layer; SKIP if absent)

Hard rules (owner directive):
- Zero provider/API calls (runner is scripted/zero-model by design)
- Test authors only; execution against master gated by coordinator

Usage:
```sh
# Run from repo root
python3 runtime/test_e2e_pipeline.py

# Run against a specific repo path
python3 runtime/test_e2e_pipeline.py --repo /path/to/swarmachines

# Output as JSON
python3 runtime/test_e2e_pipeline.py --json
```

Exit codes: 0 = all tests PASS, 1 = any test FAIL. Trace-layer returns SKIP
(not FAIL) if the tracer module is absent.
