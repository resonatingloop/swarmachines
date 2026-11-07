# delegation / one packet, one attempt, one receipt

this is a local, explicit round-trip runner for an advisory investigator. it
adds an adaption worker to the agreed envelope without modifying pug's hermes
runtime. no daemon, shell tool, repository mutation, remote dispatch or merge
permission is installed. the observer and worker modules can coexist; this
runner does not depend on the observer pr merging.

## protocol v1

owner authorized this bounded slice and its first paid trial on 2026-11-07.
pug accepted the mapping in the approved assistance room, messages
1568772226491097231 and 1568772228651421828. this implementation adopts version
and emitted-time amendments; the receipts remain advisory. connection to pug's
actual transport is not exercised by this local proof.

packet fields (all required):

- `schema_version`: `v1`; `emitted_at`: UTC ISO-8601.
- `task_id`, `attempt_id`, `assigned_worker`: bounded identifier strings.
- `objective`, `expected_deliverable`: explicit owner-supplied instructions.
- `source`: `label`, exact git `revision`, inline `text`, UTF-8 `sha256`.
- `limits`: `max_requests: 1`, `timeout_seconds: 30`, and
  `max_output_tokens` from 1 through 2048.

canonical packet hash: sha256 over UTF-8 JSON with recursively sorted keys,
compact separators, non-ASCII characters unescaped, and no trailing newline.
resend the identical packet, including its original emitted time. a changed
packet under an existing id is rejected. path-only source retrieval is not
implemented: callers must select and inspect inline text before submission.
the revision is a caller claim; the runner verifies text/hash consistency but
does not independently retrieve the git object.

acknowledgment is persisted before worker execution. it contains ids, worker,
mode, packet hash, implementation source hash and time. the terminal receipt
adds `outcome`, completion time, result, sha256 over the exact UTF-8 result text,
provider-reported token usage (unknown if missing), local attempt count,
sanitized error type and bounded response diagnostics, and a clear advisory-authority label.
`schema_valid` covers the locally constructed envelope/text type, not the
correctness of a model finding. estimated credits are separate from observed
credits; no fabricated provider spend field.

pug can map objective/context/deliverable into a hermes dispatch and echo the
ids/hash. that mapping agreement is not an authenticated remote receipt.
this local producer emits completed/failed outcomes; rejection before claim
is a CLI error, not a forged worker receipt. interrupted active attempts remain
running and require operator reconciliation. future transport import may add
rejected/abandoned terminal receipts; it is not implemented here.

## local safety and limits

SQLite transactions serialize claims across cooperating processes. one active
worker per state directory; one attempt per task in this first slice (stricter
than composite-key retries). terminal receipts are immutable. duplicate replay
returns the original receipt without worker execution or another reservation.
no automatic retry, lease expiry, reset, cancellation or reassignment command.
a crash can leave the slot occupied even if the provider finished; inspect
before any manually approved recovery, never delete the DB to retry blindly.

all processes for the approved trial MUST use the same state directory. its
budget persists across restarts: at most four live claims, each reserves 0.1
credits nonrefunded on errors or missing usage, with an additional 1-credit
reservation ceiling. these are local trial controls, not an account-wide or
cross-directory quota. deleting/copying state would defeat that coordination.

fixed hosted model: `glm-53-flash`. input packet ≤24,000 UTF-8 bytes; fixed
instructions add under 1,000 bytes; output ≤2048 tokens. at the 2026-11-07
published uncached rates (0.15 input / 0.50 output credits per million tokens),
even a conservative 25,000-input-token bound costs under 0.005 credits per
request. 0.1 reserved per claim leaves margin. revalidate rates before future
paid sessions; this is not a provider-enforced billing cap. usage estimates are
not account balance observations.

live SDK calls use only the official fixed base URL, no automatic retries,
no redirects, no tools, no stored responses and a 30s request timeout. incomplete
provider responses fail. source/model text is data; no model result is executed.
state directories must be owner-private; SQLite packets/results remain local.
this is not a defense against a malicious process already running as the owner.

## run and inspect

python 3.11+ for offline work; the live path additionally requires the adaption
SDK and its httpx dependency (0.19.0 exercised). the key comes only from the
child process's `ADAPTION_API_KEY`; the runner never reads credential files or
`.env`. use the owner's existing private credential launcher for live work.

```sh
python3 -m control_plane.delegation --state-dir /private/trial-state \
  --packet /private/packet.json --worker adaption-investigator \
  --receipt /private/new-receipt.json
```

that defaults to deterministic offline transport proof. `--live` explicitly
permits a provider call under the already-authorized trial budget. use separate
task ids for offline vs live work: an offline receipt cannot masquerade as live
proof. changing execution mode under an existing id is rejected.

```sh
python3 -m control_plane.delegation --state-dir /private/trial-state
python3 -m unittest control_plane.test_delegation -v
ruff check control_plane/delegation.py control_plane/test_delegation.py
```

without a packet, the CLI prints queue metadata and reservations, never source
or model text. receipt exports use exclusive creation and mode 0600. failed
export does not repeat execution: the terminal receipt remains in SQLite and
can be exported by resubmitting the same packet to a new receipt path.

## limitations / next slice

one-shot investigator, not an autonomous coding agent. file-edit/test tools,
builder/verifier roles, human decisions, remote receipts, automatic scheduling
and active dashboard integration require later bounded work. no quality claim
is inferred from the transport succeeding. independent review is required
before this runner is used as shared infrastructure.

## observed trial / 2026-11-07

17 offline tests pass. a local offline packet completed and replayed with an
identical receipt. the first live packet failed with a sanitized `ValueError`
after approximately 20 seconds. this retained neither a usable result nor token
usage; the exact provider/validation cause cannot be reconstructed from that
receipt. one live request was attempted and 0.1 credits remains reserved, not
reported as actual spend. replay of the identical live packet returned the same
failed receipt without invoking the worker or changing the budget.

a second, deliberately submitted fictional-source task completed. independent
inspection confirmed the answer matched the literal return value (42). usage:
278 input / 87 output tokens; estimated cost 0.0000852 credits under the listed
rate basis. actual account billing is unobserved. duplicate replay returned the
identical successful receipt with no invocation or budget change. the original
failed receipt remains untouched: its exact cause is still unknown.

the same database now records two live claims and 0.2 reserved credits. the
bounded live transport gate passes; investigator quality on substantive code,
remote dispatch and autonomous tools remain unproven. response validation now
preserves fixed reason codes, allowlisted status, and integer token counts;
unknown statuses and invalid usage become unknown, never provider text.
18 delegation tests plus 15 observer tests pass. independent review remains
required before shared use.
