# Pi–Qwen closed-loop candidate report

Working Agent self-check and raw evidence, awaiting independent exact-SHA Verdict. WorkOrder12 E2E1.0, baseline1bd0443c436f9fb4bb11dfbcaa8c481eaf311239. No project/resume fact promotion or publication.

## Result

The opt-in path completed actual Go → Pi1.3.0 → Qwen3-8B → Pi NDJSON → PostgreSQL terminal transaction → client SSE. Three sequential tasks produced:

| Session/turn | Output | Input/output tokens | Durable status |
| --- | --- | --- | --- |
| context/one | OK |59/2|completed|
| context/two | LANTERN |83/4|completed|
| independent/one | hello |51/2|completed|

Each idempotent resubmit returned its original task. Model HTTP attempt count stayed3; three distinct model-call IDs link raw requests/stream frames, Pi runtime/result and persisted task/event identities. The second request contains the first user/assistant exchange; the independent session has no previous conversation. Actual totals193 input and8 output tokens come from generation token IDs, not chunk counts or output ceilings. Raw originals and recomputed diagnostics are in [real-functional](real-functional/README.md).

## Execution and resource identity

Successful execution source1112502ab2ba186787383762f026fd6e3ccfd2ef; Stage B config SHA2560d2350140bd2e00105ba383342e6af83c6b75e531339b6d6cde5124569adb0d6; source archive b881acdd189ca75f6295a34f5c7f4efdd6b111143ac646e3ba18d865c5832324. Linux API binary ae0fbdd2eceed242c7de28159d3d148203c611fa9827fd1bf3754a6629b9d458 is built from unchanged Go runtime sources. Final Evidence commit is identified by Handoff separately.

Only GPU3 UUID GPU-dd5fc05f-7d4d-17f7-8d33-2f474b56b74e was used. Qwen revision b968826d9c46dd6066d109eabc6255188de91218, BF16, greedy/nonthinking, physical context1024/output≤128, one serialized active generation. No batching or continuous-batching engine was introduced. Model33-file manifest4380c0c2174d1ba6a4698f37d06d05cfb01d3652a19fccdeeb414a96b573a1a8 and dependency2349-file manifest0daa116e06671a31c9b57f69a7664aa30c5e33d04898eda18f08451bfa93a1e3 passed before startup.

Live image7e8449fcd1ce73c68dc35292e94182a3b09ddf155eba052fafcb0b6cf174c1c2: Python3.10.12, torch2.5.1+cu121, Transformers4.51.3, tokenizers0.21.4, NumPy1.26.4, aiohttp3.13.5. Native process maps show libcuda.so.535.309.01; host PID1359984 joins the owned model process to the authorized GPU UUID. CPU tests use separately pinned aiohttp3.12.15/pytest8.4.2/psycopg3.2.10, so CPU timing/version coverage is not relabelled as the live environment.

Actual inspect enforces model6CPU/28GiB, PG1/1, Pi2/4, API1/2, client2/5: total12CPU/40GiB. Client runs UID:GID1001:1001 with cap-drop ALL/read-only/sourceRO/evidenceRW/hostnet; a CPU-only exact-parameter ledger write/fsync probe passed before GO3. Host ports18181/2/3 bind loopback only; PG has no published port.

## Failures and corrections

All failures remain in the [case record](compatibility-case.md) and raw packs. SDK missing usage became zero-filled result before the raw gate; the bridge now streams content while requiring valid finish/usage/DONE/EOF for success. The public explicit-stream interface avoids Pi's4096-token estimate reserve while preserving the real1024 context and explicit smaller output budgets. Go treats Pi result as provisional until valid NDJSON EOF and durable terminal persistence.

Independent preliminary probes exposed detached model-call IDs, fabricated first-content time, late frames, dropped failure denominator, fixture relabelling and skipped measurement tests. Narrow repairs bind all original source sets, derive first content from raw frames, and require positive test collection with zero skips. Go external integration caching also replayed a PASS without creating a new database schema; count=1 and independent API Init remove that dependency. Original false-green/failed records are preserved.

| Real-stack attempt | Source | Outcome | Generation attempts |
| --- | --- | --- | ---: |
| First |7d826e57596cff7b8e903695047f410792880464|PG temporary Unix socket readiness preceded TCP; API refused; owned stack stopped|0|
| Second |3df2167b75823399d1d27ef04c6ff7686bc382a8|Stack ready; client default root without capabilities could not write owned evidence directory; stopped|0|
| Third |1112502ab2ba186787383762f026fd6e3ccfd2ef|UID-matched client,3 completed tasks, idempotent repeat inventory unchanged|3|

The [lifecycle ledger](gpu-budget-ledger-final.json) totals501.086926245seconds, conservatively502seconds, including initialization/teardown. This is an upper bound for container GPU ownership, not measured active CUDA time. Model/Pi required external kill137 on shutdown; API/PG/client stopped0 in the successful run. Watchdog exited, GPU3 returned6MiB/0util, no compute PID/owned listener remained. Builder containers/network were removed; PG/Pi volumes and originals remain.

## CI and measurement limits

One entry runs actual SDK wire tests, required measurement counterexamples, original inference API tests and Go race/PostgreSQL behavior plus5 synthetic durable tasks. Latest clean-source1112502 CI run39927224804 succeeded. Before final Handoff, the final Evidence SHA must itself complete CI; its run/artifact is recorded in Handoff rather than guessed here. Full-run inventory so far: f403 success,7d success,3df failure,111 success; initialization failures and concurrency cancellations are separate. No GPU runner or scheduled model job was installed.

ACK, client first nonempty content, Pi local request/content/result, Go since-claim spans, PostgreSQL terminal and client terminal have separate source records. Monotonic values are only subtracted within their own process clock. PG queue values use transaction now() differences and are diagnostics, not precise commit latency. The three real samples include a slower first request and are functional observations, not a stable P95/SLO, load curve, kernel profile, causal optimization or C10K result. The default synthetic deployment remains available, and no high-load stage was executed here.
