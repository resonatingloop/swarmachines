# tasks — add-eventlog-seal

1. [x] runner: chain helpers + `EventLog.seal()` (chain field on append,
       terminal `run.seal` record, append-after-seal refusal)
2. [x] schema: `run.seal` type, optional `chain` property, strict seal payload
3. [x] analyzer: seal verification in `_load` (tamper/insert/truncate/
       partial-chain rejected; legacy logs untouched)
4. [x] tests: determinism with chains, seal shape, tamper/insert/truncate/
       partial-chain/legacy cases (runner + analyzer)
5. [x] full suite green + ruff clean; STATUS.md checkpoint
