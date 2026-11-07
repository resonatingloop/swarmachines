# swarmachines

> continuity role: operational front door
> status: proposal phase
> last verified: 2026-11-06
> owns: the way in, present maturity, and the documentation authority map
> update when: primary use, location, or documentation ownership changes

a hackathon project taking shape around one question: what forms of relation
make an agent collective more capable without flattening distinction,
provenance, dissent, or recoverability?

**what works now:** an interactive, self-contained
[visual team proposal](plans/index.html). it explains the candidate experiment,
four swim lanes, an illustrative network disruption, a workload calculator,
and a two-day rhythm. the swarm runtime is not implemented.

start with [the current checkpoint](STATUS.md) if returning after a break,
or [the project brief](PROJECT_BRIEF.md) for the purpose and open choices.

## first successful use

you need a modern browser. for the local http path below, also have python 3
available. no packages, accounts, credentials, or background services need to
be configured.

1. enter this checkout on the owner's machine; in a different checkout, use
   its repository root instead:

   ```sh
   cd /home/resonatingloop/.organocybernetics/swarmachines
   ```

2. confirm python is available. expect a python 3 version; 3.12.3 was used here:

   ```sh
   python3 --version
   ```

3. start a local preview of the presentation directory:

   ```sh
   python3 -m http.server 8765 --bind 127.0.0.1 --directory plans
   ```

4. open [http://127.0.0.1:8765/](http://127.0.0.1:8765/) in your browser. expect
   “what shape does a swarm take under pressure?”. choose a swim lane and see
   its dossier change; the initial workload is 768 planned agent calls.

stop the preview with ctrl+c. alternatively, open `plans/index.html` directly
in a browser: the file includes its styling, illustrations, and behavior.

## where to go next

the [written two-day plan](specs/001-hackathon-plan.md) gives the team a
provisional step-by-step route from setup to a recorded experiment and demo.
review its defaults, choose the world and lane owners, and accept the first
bounded implementation slice. agent context handoffs come after those choices;
nobody is assigned by clicking a lane on the page.

the owner reported a $500 / 1,500-credit adaption grant and wants to use the
platform substantially. a separate coding-agent listener has verified one
hosted model and its published rates; see [discord setup](docs/DISCORD.md).
the grant balance and experimental-run costs remain unverified. the page's
calculator counts calls, not credits or dollars.

## documentation authority

| document | role | owns |
|---|---|---|
| [README.md](README.md) | operational | entry point, maturity, and this map |
| [STATUS.md](STATUS.md) | operational checkpoint | exercised state, gaps, and the next useful action |
| [AGENTS.md](AGENTS.md) | behavioral | repository working rules and agent continuity |
| [PROJECT_BRIEF.md](PROJECT_BRIEF.md) | durable intent | purpose, audience, constraints, and exploratory direction |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | operational procedure | preview, validation, state, and recovery |
| [docs/DISCORD.md](docs/DISCORD.md) | operational procedure | local agent connection, room identities, and communication proof |
| [plans/index.html](plans/index.html) | planning / discussion draft | the detailed visual proposal for the team |
| [specs/001-hackathon-plan.md](specs/001-hackathon-plan.md) | planning / draft | proposed sequence, defaults, integration points, and future acceptance evidence |

the html is authored source, not a generated projection of an accepted spec.
there are no runtime contracts, accepted implementation specs, or implemented
architecture documents yet. add them when their facts or proposed transitions
exist. decide disagreements by ownership of the disputed fact, not filename.

## configuration and data

the proposal reads no environment configuration and makes no provider calls.
its controls do not persist state; reload resets them. documentation links
leave the page only when followed. print/save creates a browser-managed export.

an unrelated `.env` exists in the checkout and is outside agent read access.
do not read, source, copy, stage, or serve it. use the `plans` preview directory
above. no deployment or remote publishing workflow is established here.

the [development guide](docs/DEVELOPMENT.md) contains the repeatable browser
checks and documentation-check command, including the checker's known
lowercase-heading warnings.
