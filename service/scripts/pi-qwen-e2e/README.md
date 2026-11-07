# Pi–Qwen CPU and functional checks

Opt-in Product candidate, WorkOrder Pi #12 E2E1.1. Default fixture behavior remains available. Stage B requires a fresh Master GO bound to an exact execution SHA, this config digest and deadline; historical GPU3 permissions do not apply.

`python3 service/scripts/pi-qwen-e2e/run.py --out ABSOLUTE_NEW_DIRECTORY` is the CPU entry from repository root. It requires Node>=22.19, Go>=1.24, inference test requirements plus psycopg and an empty, dedicated disposable PostgreSQL URL in TEST_DATABASE_URL (database name begins e2e12). Without that URL, local initdb/pg_ctl/createdb may start a dedicated database. Missing tools, required test IDs, skipped or empty tests, unittest expectedFailure/unexpectedSuccess and pytest xfail/XPASS all fail the required entry. Node SDK tests use actual JUnit testcase events and mandatory names. The required Go PostgreSQL test must execute with-count=1/-race; regression tests do not initialize the later task-chain schema as a side effect. The API initializes its own schema after reset.

The bridge validates actual pinned SDK1.3.0 wire, maps text arrays/max_completion_tokens, and translates only explicit store=false and include_usage=true. Unsupported fields fail closed. Content streams before terminal; valid finish/usage/DONE/EOF are necessary for success. Raw usage is required because SDK defaults can normalize missing counters. Qwen context1024/output128 use public runtime.stream, bypassing streamSimple's4096-token reserve without altering the distribution. Tokenization/rejection remains the inference backend's responsibility. Context is not silently trimmed; no tool, sampling or retry capability is claimed.

Current hosted `ci.yml` invokes the CPU entry and then the unchanged accepted Nginx entry `service/scripts/nginx-entry/run.py --build-host --out NEW_DIR` without its measurement matrix. It stops its dedicated first-phase PG container before the Nginx phase. Only push on main/workorder/12-candidate triggers this workflow; creating the draft PR does not duplicate a run. The accepted Nginx workflow/config/scripts and974 historical evidence files remain unchanged. Local macOS CPU results and hosted Linux/runtime versions are reported separately.

## Fresh GPU0 functional execution

Only the authorized server `/media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/{builder,regulator}` roots may contain new host artifacts. Set process CUDA_VISIBLE_DEVICES=0. Projects are pi-e2e12-1031-b / pi-e2e12-1031-r. `compose.qwen.yaml` exposes loopback18181–18183, targets host physical GPU0 UUID GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead, uses read-only existing model/deps/image, hard resource limits and a three-attempt cap for each new stack. The fresh GO/watch deadline is at most15minutes. Model's older30minute validation ceiling does not extend that GO.

Before any new GPU start, the Master must bind exact source/config/commands/deadline and two resource checks at least10seconds apart must show no foreign target-GPU compute PIDs. The external foreground `watch.py` starts before compose; it only stops exact project/workorder/execution-SHA objects. Its safety cleanup retains diagnostic volumes. New attempts/lifecycle add to historical B3/R0 and502seconds; they do not reset the24-attempt/3600second total. No automatic warmup or retry.

After the real stack is ready, collect `device_proof.py --project PROJECT --sha FULL_SHA --out NEW_IDENTITY_DIRECTORY` on the host. It captures actual host and container nvidia-smi command receipts, full model inspect, exact stage-b config and clean source identity. `smoke.py --identity IDENTITY_DIRECTORY --prefix builder12 --sha FULL_SHA --out NEW_DIR` runs exactly three sequential durable tasks: same-session two turns plus independent session, followed by idempotency/inventory checks. The client uses UID1001:1001/read-only/tmpfs/cap-dropALL/2CPU/5GiB with sourceRO/evidenceRW; the same settings must pass a CPU write-permission probe first. The client receives identity evidence read-only, never the Docker socket.

Copy Pi raw bridge, Go trace, PostgreSQL events and lifecycle/inspect/cleanup receipts to the output. `analyze(root)` is producer-only, returning integrity_verified=false; local monotonic spans are not cross-clock subtractions and synthetic times are not GPU performance. The real-kind analyzer requires coherent physical0 UUID/config/source/inspect/mount/device/health associations; a GPU=True label is insufficient.

Seal completed originals once:

```sh
python3 service/scripts/pi-qwen-e2e/seal.py --root SEALED_INPUT --receipt-out EXTERNAL_RECEIPT.json
python3 service/scripts/pi-qwen-e2e/recompute.py --root SEALED_INPUT \
  --expected-manifest-sha256 DIGEST_FROM_EXTERNAL_HANDOFF --out EXTERNAL_REPORT.json
```

The authoritative entry first verifies the external digest and full inventory through the unchanged NG1.2 integrity reader. It never rewrites sealed originals. Copy the digest to the external Handoff; deriving a new digest from altered inputs does not preserve the old identity. The old703 manifest-listed originals and their manifest remain historical GPU3/CPU fixtures with original hashes. This functional work does not establish throughput, stable P95, C10K capacity or a physical GPU limit.

## Exact-ID watchdog cleanup correction

The November2 functional run completed at source444096 but exposed a watchdog removal race. `watch_cleanup.py` supplies the live watch's exact-ID inspect/inventory/cleanup logic. A failed inspect is removed only if a successful full engine inventory lacks that exact ID; unreachable engines and ownership mismatches remain unknown/failing. No name fallback is used. `test_watch_cli.py` runs actual bounded1CPU/512MiB CPU containers against the public cleanup CLI, including reused names and a child-only wrong Docker socket. It requires explicit WATCH_CLI_EVIDENCE; scratch stays underneath that path. The hosted required step runs this suite between E2E and NG. Server's actual full-watch red/green probes are retained in [dated evidence](../../../docs/evidence/pi-qwen-e2e-20261031/20261102-builder/README.md); no additional Builder model run was made.

## PostgreSQL timestamp compatibility

The analyzer accepts timezone-aware PostgreSQL timestamps with zero through six fractional digits, using Python 3.10-compatible parsing. It rejects naive/malformed timestamps and negative queue intervals. The required measurement gate exercises these cases against the public analyzer, and CI runs that gate under Python 3.10 before the unchanged Python 3.12 full suites. [November 7 failure and replay evidence](../../../docs/evidence/pi-qwen-e2e-20261031/20261107-analyzer/README.md) preserve the old execution identity.
