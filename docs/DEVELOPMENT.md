# swarmachines / development

> continuity role: operational procedure
> status: current for the proposal page
> last verified: 2026-11-06
> owns: local preview, maintenance checks, and recovery
> update when: the entry point, dependencies, or validation path changes

## what runs

[plans/index.html](../plans/index.html) is the entire working presentation:
html, css, svg illustrations, and browser javascript in one file. it has no
package manifest, install step, build step, backend, or configured provider
integration. a modern browser is sufficient to open the file directly.

the optional http preview uses python 3; python 3.12.3 was exercised here.
there is no environment configuration to load for the proposal. `.env` is
outside this workflow and must not be read or sourced by agents.

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

there is no committed automated test suite. earlier browser verification
scripts and screenshots were temporary aids, not repository dependencies.
do not require a returning teammate to recover files from `/tmp`.

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
