# spec 013 calibration v0

status: retained apparatus finding; not accepted for model-behavior comparison

date: 2026-11-08

base revision: `e21deb6114ddd77813bbca0b5da482c280ae4b8e`

sdk: `adaption 0.19.0`

## bounded run

- three accepted panel models, one agent, seed 42, two turns each.
- peer-required freight regime with release turns 1, 7, 9 and 11.
- six calls total, zero retries, shared 10.000-credit hard ledger.
- actual reconciled charge: 1,579 microcredits (`0.001579` credits).
- the jsonl files are sealed public evidence. prompts and provider responses are
  retained separately as private mode-0600 artifacts and are not in this tree.

## observed result

all six calls returned usage. the strict parser recorded `invalid_json` for all
six decisions. gemma's two private outputs each contained an object with exactly
`action` and `reason`, but wrapped it in a markdown fence, so rejection under the
accepted exact-json contract is correct. glm and qwen each consumed the full
160-token output allowance while their normalized `output_text` was empty.

the v0 adapter did not persist the provider response status or full response
object. the sealed logs therefore retain the categorical `malformed` result and
must not be rewritten. adaption documents that reasoning items are excluded from
`output_text` and that an incomplete response can identify `max_output_tokens`;
those facts make token exhaustion a plausible explanation for glm and qwen, not
an established fact about these four retained calls.

## repair and gate

the adapter now preserves provider status and incomplete reason in events and
the full provider response only in the private sidecar. the analyzer now counts
jobs released by the horizon and summarizes call usage and decision failures.

no stage-one matrix follows automatically. another paid calibration requires an
accepted bound amendment because the accepted gate allowed at most two calls per
model and fixed 160 output tokens.
