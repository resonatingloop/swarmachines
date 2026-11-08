# .beads anchoring — what is tracked and why (2026-11-08)

Beads is the sole task tracker for this repo (owner directive 2026-11-08).
This directory carries the **control surface only**; the board's data plane
is the Dolt remote, never git blobs.

## Tracked here

- `config.yaml` — bd defaults + `sync.remote` (the git+dolt remote URL).
  Contains no secrets; credentials stay in env vars / the credentials file.
- `.gitignore` — the store's own boundary: excludes all payload and runtime
  state (see below). Do not add negation patterns; they would override fork
  protection.
- `README.md` — beads' own store readme.
- `metadata.json` — store identity (backend, dolt mode, project id). No
  secrets.

## Explicitly NOT in git

`embeddeddolt/`, `backup/`, `dolt/`, every `*.lock` / `*.gate.lock*`,
`last-touched`, `.local_version`, `push-state.json`, credential key files.
The `.gitignore` above keeps them out. **Never commit the live database
payload** — the shared board travels as `refs/dolt/data` on origin
(verified 2026-11-08: `fe91fec9`), and committing payload copies would
duplicate and corrupt the git+dolt sync boundary.

## Fresh-clone bootstrap

A fresh clone hydrates the board from origin's dolt refs:

```bash
bd dolt pull        # from the clone root; .beads/config.yaml supplies sync.remote
```

(Verified path: asterion's read-side bootstrap 2026-11-08 17:26Z — 73 issues
from the git+dolt remote, zero local state.)

## Control-plane container note

On the coordinator container the live store is relocated OUTSIDE any git
tree. Export before any bd command:

```bash
export BEADS_DIR=/workspace/.beads-store
```

## Pushing board state

`bd dolt push` fails with `could not read Username for 'https://github.com'`
when the gh credential helper is only configured repo-level — dolt's git
subprocess runs outside the repo and cannot see it. Inject the helper:

```bash
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=credential.helper \
GIT_CONFIG_VALUE_0='!gh auth git-credential' \
GIT_TERMINAL_PROMPT=0 bd dolt push
```

## Hard rules

- **NEVER `bd init`** while a store exists — it wipes live state.
- **NEVER `git clean -fd` / `git stash -u`** in a checkout with untracked
  state — this destroyed the in-repo store twice before the relocation.
- If the board looks empty, check `BEADS_DIR` first — an unset export
  resolves a dead or hollow store and looks like "the board is empty".
