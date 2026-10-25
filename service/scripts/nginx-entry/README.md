# Private Nginx CPU entry

Opt-in Product, WorkOrder Pi #15 / NG1.2. The default service and singleton lock remain unchanged. The platform uses actual Pi SDK1.3.0 with its deterministic synthetic model. The separate lab uses two stateless HTTP fixtures, not two Go controllers or model replicas.

`run.py --out ABSENT_DIRECTORY [--measure]` is the single bounded entry. Required environment: `SOURCE_SHA` full checkout SHA, `NODE_ROOT` Linux Node22.23.3 root, `PI_MODULES` matching Linux dependencies installed from `service/pi/package-lock.json`, `NG_DEPS` isolated Python dependencies from `service/inference/requirements-test.txt`; `NG_PROJECT` begins `pi-ng15-`, `NG_OWNER` is builder/regulator/ci. Server additionally needs `GO_ROOT`, `GO_MOD_CACHE`, writable `NG_BUILD_CACHE`, and existing GCC-capable `NG_BUILD_IMAGE` immutable ID. `--build-host` is for the bounded hosted CI machine, with `NG_HOST_TEST_DATABASE_URL` pointing to this profile's dedicated `ng_test` database. Never point at user history.

```sh
SOURCE_SHA=$(git rev-parse HEAD) python3 service/scripts/nginx-entry/run.py \
  --measure --out /media/usv012/pjx/pi-agent-platform/experiments/15-nginx-entry-20261025/builder/evidence/run-01
```

Server source/build/cache/logs must all stay beneath the authorized work root. The runner reserves loopback18201–18207, refuses conflicts, requires20GiB free, has a15min alarm, and caps each client/build container1CPU/2GiB. Platform PG0.75CPU/1GiB, Pi1CPU/3GiB, API1CPU/1GiB and Nginx0.5CPU/256MiB plus one build/client slot stay below6CPU/10GiB. Singleton probe uses the API slot. Lab runs after platform stops: two0.5CPU/256MiB fixtures and0.5CPU/256MiB Nginx plus client. At most six owned containers run. Only explicitly named/labelled owned resources are stopped; PG/Pi volumes remain for diagnosis. No GPU devices are passed.

Required suites: `go test -race -count=1 -json ./...` against fresh `ng_test`, all inference CPU pytest via its strict public entry, nonempty measurement unittest, three real platform tests, four lab tests. Zero required skips is mandatory. Clients save HTTP and SSE receipts; PG snapshots bind retained records. Config/inspect/logs and cleanup accompany the receipts. The independent Regulator supplies additional isolated seeded failures; Builder does not self-accept.

The optional frozen config contains exactly12 points: hey C1/8/32 × direct/proxy,300 requests; Vegeta10/25/50rps × direct/proxy,10s. Per-path10 warmups and2s interpoint idle are separate. HTTP/1.1, keepalive, no redirects,5s timeout. Raw hey CSV and Vegeta binary/decoded receipts are retained. hey supplies no custom per-attempt IDs; its CSV and proxy logs are only interval/count-correlated, not claimed to join one-to-one. For hey0.1.4, configured N300 schedules C*floor(N/C):300/296/288 at C1/8/32. The0/4/12 unissued remainder is separate from service errors. Actual scheduled attempts missing CSV receipts count as unknown failures. Completion fractions use both scheduled and configured-intent denominators. P50/P95 use nearest-rank over observed successful HTTP attempts, alongside all planned/observed/missing/error counts. One repetition is exploratory; tool rounding and same-host generator interference limit interpretation. SSE causal marker latency is separate from HTTP completion. No model TTFT, Qwen throughput, C10K capacity or improvement is established.

`recompute.py` is the authoritative sealed-input entry; it requires the external manifest digest before recomputing all12 points. Internal statistics reject missing/extra receipts and changed matrix identity. `test_entry.py` exercises actual public HTTP interfaces. Fixture ledgers preserve marker→independent release→terminal and received POST count. Client disconnect does not cancel a durable platform task. No background scheduling or public publishing is installed.

## NG1.2: required tests and authoritative sealed recomputation

Required unittest suites run through `strict_suite.py`, which reads the actual `TestResult` and writes JSON counts. A skipped test, empty discovery, errors, failures or expected failures return nonzero. The full runner executes both the8 statistical tests and9 actual-CLI tests; matching text such as `OK` is not a gate. Go still permits package-level no-test events while requiring the real PostgreSQL test to pass.

For sealed raw receipts, use the public entry below. Copy the expected digest from the external Handoff/CI binding; do not derive a new trusted digest from the input you want to check.

```sh
python3 service/scripts/nginx-entry/recompute.py \
  --root docs/evidence/nginx-entry-20261025/raw/run-08 \
  --expected-manifest-sha256 35d43915ecfab8e4224ff17a3d692481610a11680327bb899167fbc555c3210d \
  --out /path/outside/the/sealed/input/verified-summary.json
```

This entry first matches the external manifest SHA256, then verifies every listed receipt and the complete file inventory, and only then computes statistics. Missing/wrong anchors and changed CSV/manifest fail in the integrity phase. Legal equal rounded hey CSV rows remain present: they do not provide unique real-attempt identities. The wrapper rejects output inside the sealed tree. `measurement.report` also requires an explicit expected digest; underscore-prefixed statistical helpers are internal and do not establish integrity. Producer-only live intermediate statistics carry `integrity_verified=false`; they cannot rewrite a sealed tree or claim authoritative verification. The original run08 manifest and all historical failed reports remain unchanged.
