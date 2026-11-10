# Pi #13 LB13.1 producer evidence

Status: CPU implementation candidate, independent acceptance and GPU GO pending. Baseline accepted76ac647318b1154b56338de5e9d12bdc592f0013; no new GPU/model requests have run at CPU-ready time.

- `tdd-red.log`: actual slow-SSE CLI fails before implementation.
- `tdd-green.log`: first terminal-aware closed CLI passes.
- `cpu-tests.log`: current native HTTP/CLI regression results, including open arrivals, delayed durable terminal, unresolved EOF and resealed-ledger/raw mismatch.

The first open fixture incorrectly supplied `{}` and was rejected by the real-payload requirement; corrected fixture uses a nonempty payload. Initial local inference test entry failed because default Python lacked pytest; a read-only existing test venv subsequently ran50 tests with zero skips. These are environment/fixture corrections, not GPU results or claimed model improvements. Full receipts and execution identity will be added by Handoff. No facts/resume disclosure is authorized.

## Concentrated repair after independent CPU rejection

Independent Regulator reproduced an opt-in trace I/O exception retaining the serialized slot, a slow response extending beyond the absolute point deadline, and two launcher preflight ownership/watch-binding failures (the launcher cases used a subprocess test double and did not stop real foreign resources). Original a9 source/CI1 success and all independent failure originals remain traceable through #13; a green broad suite did not cover these cases.

The authorized repair puts all worker settlement under unconditional final slot release, bounds the full HTTP response with a socket shutdown timer, and binds the watcher to exact project/source/deadline/live PID/start ticks. Preflight rejection performs no resource mutation; actual cleanup stops/removes only full IDs with matching ownership. A live guard starts before model startup and continues while startup/collection run. New HTTP trickle and trace failure recovery regressions exercise these boundaries. Builder reran original independent probes outside the candidate; only independent Regulator can determine the repaired candidate's Verdict.

- [学习与X私稿](LEARNING-DRAFT.md)：CPU锁/截止/测试前提故障，未发布、不晋升事实。

## Bounded-window closeout, 2026-11-07

Remote394e4f15a821ab969a104aae7f8803d3efd3ef72 remains unaccepted; CI2 failed only the new10ms-offer trickle test. The native generator correctly classified that fixture's slot as generator_drop. Test-only pending work now explicitly uses rate1/drain0.2 and longer trickle; actual cached Linux/Python3.12.15 constrained runc execution passed6 tests/skip0. No new commit or CI3 was triggered. Original CI2 ZIP and the Linux receipts are sealed outside the candidate in producer state and bound by the partial Handoff. The original failing test used TemporaryDirectory and its per-slot trace was deleted during teardown; its assertion stack is preserved, and no nonexistent raw ledger is claimed.

The model-start cutoff passed before all prerequisites and the exact pilot GO could be executed. Builder started no model, external GPU watch, or real inference HTTP; no pilot, Rb or formal curves exist. Actual server closeout at02:51:22.960Z: owned project objects0, GPU0no computePID/6MiB, source394clean, no pilot/watch outputs. Main integration and independent acceptance remain pending. Further GPU work requires a new bounded restoration contract and fresh exact GO.

## November10 restoration and actual startup failure

[Watch freshness failure and scoped repair](20261110-watch-repair/README.md) retains the real failed startup,29.348931seconds model lifetime/zero inferenceHTTP, original timing-fixture correction and new CPU monitoring probes. Independent review, new-SHA CI and actual GPU baseline remain separate pending gates.

- [November10 full captured-input pairing](20261110-paired-input/README.md) preserves actual SDK workspace differences, refused pilot04 comparison, and the prospective per-slot exact replay protocol. This does not establish a completed real paired baseline.

- [November10 interruption accounting repair](20261110-interrupt-repair/README.md) preserves the foreign-guard partial run and actual CPU red/green regression; it is not a completed matrix.
