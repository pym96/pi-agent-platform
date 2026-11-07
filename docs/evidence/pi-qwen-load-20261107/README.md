# Pi #13 LB13.1 producer evidence

Status: CPU implementation candidate, independent acceptance and GPU GO pending. Baseline accepted76ac647318b1154b56338de5e9d12bdc592f0013; no new GPU/model requests have run at CPU-ready time.

- `tdd-red.log`: actual slow-SSE CLI fails before implementation.
- `tdd-green.log`: first terminal-aware closed CLI passes.
- `cpu-tests.log`: current native HTTP/CLI regression results, including open arrivals, delayed durable terminal, unresolved EOF and resealed-ledger/raw mismatch.

The first open fixture incorrectly supplied `{}` and was rejected by the real-payload requirement; corrected fixture uses a nonempty payload. Initial local inference test entry failed because default Python lacked pytest; a read-only existing test venv subsequently ran50 tests with zero skips. These are environment/fixture corrections, not GPU results or claimed model improvements. Full receipts and execution identity will be added by Handoff. No facts/resume disclosure is authorized.

## Concentrated repair after independent CPU rejection

Independent Regulator reproduced an opt-in trace I/O exception retaining the serialized slot, a slow response extending beyond the absolute point deadline, and two launcher preflight ownership/watch-binding failures (the launcher cases used a subprocess test double and did not stop real foreign resources). Original a9 source/CI1 success and all independent failure originals remain traceable through #13; a green broad suite did not cover these cases.

The authorized repair puts all worker settlement under unconditional final slot release, bounds the full HTTP response with a socket shutdown timer, and binds the watcher to exact project/source/deadline/live PID/start ticks. Preflight rejection performs no resource mutation; actual cleanup stops/removes only full IDs with matching ownership. A live guard starts before model startup and continues while startup/collection run. New HTTP trickle and trace failure recovery regressions exercise these boundaries. Builder reran original independent probes outside the candidate; only independent Regulator can determine the repaired candidate's Verdict.
