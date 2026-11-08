# explicit task submission

prepare and inspect a bounded task, then run exactly its fingerprint. commands
are explicit; no daemon, browser write server or automatic dispatch is installed.
read-only investigation results remain advisory.

## prepare

```sh
python3 -m control_plane.submit prepare --repo . --revision FULL_COMMIT_SHA \
  --source runtime/example.py --start 10 --end 25 \
  --task-id example-check --attempt-id example-check-01 \
  --objective 'inspect the selected branch' --deliverable 'a short finding with evidence' \
  --output /private/new-task-review
```

use a real tracked regular Python file under runtime/ or control_plane/. source
is read from the specified commit, never a dirty working file or credential file.
optional start/end are inclusive and must both be supplied. preparation checks
the blob size before retrieval; source and envelope limits still apply. inspect
the new mode-0600 review.txt in an editor: it includes exact source and is PRIVATE.
terminal output contains only paths and fingerprints. no task has executed yet.

## initialize an authorized session

```sh
python3 -m control_plane.submit init --root /private/sessions \
  --session-id example-session --authorization 'actual owner instruction reference' \
  --purpose 'bounded read-only code investigations' --authorize-live
```

this records an instruction already supplied by the owner; a string in a manifest
is not evidence of consent. omit authorize-live for offline-only work. initialization
creates a new private directory, a write-once manifest and a queue bound to the
manifest hash. existing destinations refuse. interrupted initialization remains
for inspection; never invent another session to bypass it or its accounting.

current new-session policy: 20 requests maximum, 2 credits reserved ceiling,
0.1 credits retained per live claim, one active worker, no automatic retry. it is
stored in the budget row and read on restart. legacy queues retain four requests
and their original one-credit ceiling, without migration. the selected runner
source fingerprint is pinned in the manifest; a changed runner refuses rather
than silently changing session behavior. these are local controls, not an account
quota or observed bill. additional sessions require actual owner authorization.

## submit and capture

```sh
python3 -m control_plane.submit run --session /private/sessions/example-session \
  --manifest-sha256 MANIFEST_SHA --packet /private/new-task-review/packet.json \
  --packet-sha256 PACKET_SHA --repo . --output /private/new-board
```

this defaults to the deterministic offline worker. explicit live execution adds
`--live` and uses the existing private credential launcher, which injects
ADAPTION_API_KEY into the child environment. never put the key in arguments,
manifest, packet or review files. offline/live tasks must use distinct ids.

packet and manifest fingerprints must match. the wrapper reads the packet once
and passes that same validated object to the existing runner. mismatches, missing
or partial queues, conflicting ids, active claims, exhausted policies and absent
live authority/key refuse; none triggers a fallback worker. identical completed
or failed packets replay their persisted receipt without another execution.

after receipt persistence, the wrapper attempts one new board capture. a failed
capture does not undo or repeat the worker. output includes recorded state,
replay flag, result hash and capture status, never the worker's answer. inspect
private receipts separately if you need the advisory text.

exit codes: 0 completed + available capture; 1 failed worker (capture status
reported separately); 2 blocked/invalid input; 3 completed + unavailable capture.

## recapture without execution

```sh
python3 -m control_plane.submit capture --session /private/sessions/example-session \
  --manifest-sha256 MANIFEST_SHA --repo . --output /private/another-new-board
```

no provider call occurs here. new captures include the session id and manifest
hash; the board remains frozen. multiple sessions are separate captures, not an
account-wide total. keep all session/review/capture files out of the repository.

## validation and limits

`python3 -m unittest control_plane.test_submission -v` exercises fictional git
sources, exact excerpts, tampering, initialization interruptions, swapped queues,
legacy no-migration, persistent limits, replay and capture failure. SDK calls are
mocked. normal tests never need a real key. the existing browser harness checks
the produced board. independent review is required before shared use.

this tool trusts the local owner to supply genuine authorization and inspect
source before sending. it does not enforce semantic task-purpose matching or
resist an owner who deliberately edits databases. provider-response sanitization
is a separate teammate-owned follow-up; this wrapper does not rewrite that work.
