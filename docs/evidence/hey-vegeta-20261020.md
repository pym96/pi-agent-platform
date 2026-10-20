# hey / Vegeta bounded HTTP experiment — 2026-10-20

Builder candidate for [Pi WorkOrder #3](https://github.com/pym96/pi-agent-platform/issues/3), Criteria1.0. This report is not an independent Verdict, project-fact registration, resume claim or production capacity statement.

## Identity and reproduction

- Accepted input baseline: `ef176befbd63f0c89d57505b9ed5576a939401d7`.
- Frozen execution driver: `7cdbfec320eb07b6db9dc9f85d87c95f7856ceec`. Final candidate adds analysis/documentation only; Go/Pi/business sources and Compose remain unchanged from the accepted baseline. `service-source-sha256.txt` binds the actual Linux sources and driver; source-identity.json records service/load binaries and fixture/config hashes.
- hey module `github.com/rakyll/hey@v0.1.4`; Linux amd64 executable SHA256 `d1489e8d371fe30055fce19740c51050a243b4954b4d0d7b3aa1ff389d875a8a`.
- Vegeta module `github.com/tsenart/vegeta/v12@v12.12.0`; executable SHA256 `9a00d6a264707d66d618eb6811ccb0070aa49d9d2123507c00b80510fbfc220a`.
- Official modules were cross-compiled on macOS with Go1.27.1, GOMAXPROCS1, `-p=1`, Linux/amd64 and CGO disabled; complete `go version -m` receipts retain dependency versions and checksums. Local GOMEMLIMIT800MiB is a runtime target, not an OS hard limit. Tool build completed before measured containers started.
- Linux service build used existing Go1.24.13/Node22.23.3 toolchains and cached dependencies, a network-disabled 1 CPU/1 GiB container, actual Pi1.3.0, and `go test -p 1 ./...`. PostgreSQL integration tests without TEST_DATABASE_URL retain their existing skip; this campaign's HTTP history reads a real dedicated PostgreSQL database.
- Owned server root: `/media/usv012/pjx/pi-agent-platform/experiments/3/builder/`; Compose project `pi-hv3`. Published ports are only 127.0.0.1:18151/18152. HTTP generators access the same owned API through its private Docker network alias `api:8080`; no external target is attacked.
- Hard container limits: PostgreSQL 1 CPU/1 GiB, API 1 CPU/2 GiB, Pi+fixture 1 CPU/4 GiB, one generator 1 CPU/1 GiB. The idle HTTP generator is stopped and removed before starting the dedicated SSE generator, keeping the aggregate at 4 CPU/8 GiB. No global daemon/kernel/resource setting changed.
- Fresh owned database/context volumes are retained. Disk was above the 20 GiB floor; host nofile was 1024 while measured API/Pi/load containers had 32768. Container inspect, process limits and image identities are in the raw evidence. No GPU, Redis, credentials, paid model or public endpoint was used.

Reproduction and analysis commands are in [the scripts guide](../../service/scripts/hey-vegeta/README.md). All per-run command arguments, UTC start/end, source SHA, expected counts, exit codes, and artifact SHA256 values are in runs.jsonl. The summarizer rejects a missing matrix cell, duplicate run identity, repeated primary raw bytes, missing file or changed per-run hash. It preserves non-success HTTP responses and missing transport-error observations as failures.

## Workload and statistical meaning

The fixed session `hv3-fixed` contains two completed actual-Pi tasks against the deterministic streaming fixture. GET `/sessions/hv3-fixed/tasks` returned HTTP200 and 268 bytes, SHA256 `994043ff92a225733921320adfd10463d163b7556813d5da81c8b6b6616ca939`. The body was checked unchanged before and after each cache state; all36,600 decoded Vegeta response bodies also matched its SHA256. These two rows are a deliberately small history fixture.

hey tested `/health` and this history path with c=1/10/100, n=1000, three repetitions, cache=0 then cache=1. Vegeta tested the same history at offered rates10/100/500 requests/s, duration10s and three repetitions for each cache state. Both use HTTP/1.1 over cleartext, keepalive enabled, redirects disabled, timeout5s, no proxy. hey's `-h2` is omitted because the cleartext service is HTTP/1.1; its explicit redirect switch and CPU1 switch are recorded. Vegeta explicitly fixes HTTP2=false, keepalive=true, redirects=0, workers10 and max-workers100.

Nearest-rank P50/P95/P99 sort each run's observed request latencies and choose element `ceil(p*n)`. No samples are pooled across runs, tools or cache states. hey CSV rounds seconds to four decimal places, so its latency resolution is 0.1ms; upstream hey omits transport-error rows from CSV. Missing expected rows are counted as failed/unobserved, never assigned fabricated latency. Vegeta's native interpolated quantiles are preserved separately in each JSON report and summary.nativeReport.

hey observed completion rate is observed rows / max(offset+response-time), using its benchmark-relative request timestamps; external Docker invocation wall time is separate. Vegeta records offered rate, actual native send rate and observed completion rate computed from first send to last completion (`duration+wait`). For a finite run, native sent count / first-to-last-send duration can slightly exceed the offered rate even when the intended 10-second count is exact. HTTP success means 2xx plus a zero tool exit and complete observed denominator; it does not mean an Agent task executed.

## Results

54 runs completed: 36 hey runs (36,000 requests) and18 Vegeta runs (36,600 requests), with72,600/72,600 observed requests returning HTTP200 and all tool exits zero. No workload run was dropped or retried. Each range below is the minimum–maximum of the three separate run values; percentiles are not pooled. hey load is concurrency; Vegeta load is offered requests/s.

| Tool / interface | Load | Cache | Runs / observed | Actual completion req/s | P50 ms | P95 ms | P99 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| hey / health | 1 | 0 | 3 / 3000 | 3218.5–4948.0 | 0.200–0.300 | 0.300–0.400 | 0.300–0.700 |
| hey / health | 10 | 0 | 3 / 3000 | 12804.1–16103.1 | 0.500–0.700 | 0.900–1.200 | 1.700–2.200 |
| hey / health | 100 | 0 | 3 / 3000 | 6988.1–10040.2 | 6.700–10.500 | 31.200–38.600 | 38.400–45.400 |
| hey / history | 1 | 0 | 3 / 3000 | 2091.2–2377.0 | 0.400–0.500 | 0.500–0.600 | 0.700–0.900 |
| hey / history | 10 | 0 | 3 / 3000 | 6788.9–8116.9 | 1.000–1.200 | 1.700–1.800 | 2.900–4.600 |
| hey / history | 100 | 0 | 3 / 3000 | 5115.1–5546.3 | 9.900–14.600 | 34.300–57.300 | 39.600–58.900 |
| vegeta / history | 10 | 0 | 3 / 300 | 10.1–10.1 | 1.184–1.438 | 1.601–1.922 | 1.722–2.152 |
| vegeta / history | 100 | 0 | 3 / 3000 | 100.1–100.1 | 0.711–0.785 | 1.079–1.115 | 1.257–1.500 |
| vegeta / history | 500 | 0 | 3 / 15000 | 500.1–500.1 | 0.480–0.503 | 0.604–0.653 | 0.830–0.924 |
| hey / health | 1 | 1 | 3 / 3000 | 3402.5–3570.2 | 0.300–0.300 | 0.300–0.300 | 0.400–0.500 |
| hey / health | 10 | 1 | 3 / 3000 | 8733.6–13774.1 | 0.600–1.100 | 0.900–1.600 | 2.100–3.300 |
| hey / health | 100 | 1 | 3 / 3000 | 6472.5–8116.9 | 9.600–11.500 | 32.800–36.900 | 37.400–44.800 |
| hey / history | 1 | 1 | 3 / 3000 | 2270.1–2314.8 | 0.400–0.400 | 0.500–0.500 | 0.700–0.700 |
| hey / history | 10 | 1 | 3 / 3000 | 6038.6–11933.2 | 0.600–1.300 | 1.000–2.000 | 3.600–5.000 |
| hey / history | 100 | 1 | 3 / 3000 | 4849.7–5577.2 | 14.500–16.700 | 37.200–43.800 | 41.400–49.600 |
| vegeta / history | 10 | 1 | 3 / 300 | 10.1–10.1 | 1.098–1.247 | 1.422–1.871 | 1.644–2.862 |
| vegeta / history | 100 | 1 | 3 / 3000 | 100.1–100.1 | 0.633–0.637 | 0.919–0.984 | 1.053–1.342 |
| vegeta / history | 500 | 1 | 3 / 15000 | 500.1–500.1 | 0.491–0.497 | 0.631–0.657 | 0.868–0.937 |

All54 per-run values, actual Vegeta send rates, native reports, resource snapshots and27 paired cache deltas are in summary.json. The matrix contains no failed/unobserved request in this campaign; error handling still requires the independent negative probes.

## Resources and independent SSE probe

The dedicated generator ran repetition1 with cache1, one hot session and seed142, from12:37:06.321912924Z to12:39:26.735358182Z. After a20.413s paced connection ramp, its actual hold was120.000668722s. It established10,000 clients; all24 API samples during the hold reported10,000 online connections. At the end10,000 clients satisfied the generator’s health rule: established, at least one heartbeat, no client error, and last observed activity within20s.

Each client received11–14 heartbeats (124,858 total) and264 unique ordered event IDs (2,640,000 client observations). Client duplicate/regression/error counts were0/0/0. The existing generator intentionally reconnects every10th client once after30s: exactly1,000 planned reconnects occurred. The service nevertheless counted21 write failures; these are retained as failures and their precise cause is not established by the receipts. No uninterrupted identity of the same10,000 TCP sockets for the whole120s is claimed. The supported observation is10,000 logical subscriptions at sampled points during a bounded hold with planned reconnects; brief between-sample dips are not ruled out.

All24 offered synthetic tasks were acknowledged202 and observed completed, with0 task errors. Completion polling latency P50/P95/P99 was3623.846/4370.105/4532.632ms, including100ms polling and this load’s scheduling/queueing. These values are neither model inference latency nor the short history-read latencies above. No real model was used.

| Phase / process | Observed maximum RSS KiB | Observed maximum FD | Observed maximum API goroutines |
|---|---:|---:|---:|
| HTTP API, before/after snapshots | 17,236 | 10 | 12 |
| SSE API, sampled during hold | 476,000 | 10,014 | 20,021 |
| SSE dedicated load process | 604,748 | 10,007 | Not exposed |

The149 continuous whole-container samples observed maximum CPU percentages of API100.62%, PostgreSQL27.47%, Pi+fixture4.96%, HTTP-generator42.72%, and SSE-generator86.98%. These are sampled Docker percentages, not exact peaks or cumulative averages; small excursions around100% are sampling/accounting values and do not replace inspect’s1-CPU quota. The HTTP generator’s whole-container memory/CPU samples remain separate from API/Pi/PG. After SSE client shutdown, API metrics returned to0 connections and11 goroutines before stack shutdown.

Before/after every HTTP run, raw snapshots retain Docker whole-container CPU/memory, API goroutines/heap, process1 RSS/FD/CPU ticks and actual process limits. Per-run CPU tick deltas divided by SC_CLK_TCK and the snapshot interval include sampling/orchestration overhead; PostgreSQL process1 excludes its backend processes. Whole-container Docker CPU remains separately available. HTTP generator process1 is the idle supervisor, so its process1 RSS is not the hey/Vegeta child RSS; independent generator-container memory/CPU accounting is retained, while per-child HTTP generator RSS/FD/goroutine peaks are not demonstrated. This limit must not be silently replaced with supervisor metrics.

A continuous Docker stats sampler began after the first14 hey runs; every run still has before/after snapshots. Samples and short bursts do not establish exact CPU/RSS/FD/goroutine peaks. The dedicated SSE generator is process1, so its sampled RSS/FD belongs to the actual load executable. Continuous sampling, the host and the shared physical machine can perturb timings. The private Docker network and resource limits do not provide a dedicated physical host.

## Interpretation, failures and remaining limits

The initial question combined tool execution, goroutines and C10K. The measurement separates three objects: short HTTP requests, held SSE connections, and bounded actual Pi tasks. hey concurrency100 is not10,000 live connections; Vegeta's offered rate is not observed completion rate or Agent execution throughput. Actual task execution remains configured at two bounded workers, and the SSE probe submits one hot-session synthetic task every5s. This campaign does not benchmark two-worker task throughput or a real model.

Code inspection shows history calls the PostgreSQL history path; SSE_TAIL_CACHE selects an event-tail path for SSE delivery. Therefore, paired history/health measurements are a controlled toggle comparison, not evidence that an SSE tail cache accelerates history queries. summary.cachePairs retains all27 same-tool/interface/load/repetition deltas. Serial cache order and a shared host also limit causal interpretation; no speedup is claimed.

Preparation failures are retained in this account: an initial rsync failed because the dedicated parent directory did not exist; creating only the owned target directory resolved it before any experiment. Direct server Go-module access and an old proxy endpoint timed out; no shared proxy or daemon was changed. The official fixed tools were then built locally and transferred, with module/build identities preserved. These are setup failures, not successful workload runs. The measurement matrix is not replaced, optimized or selectively rerun.

Human supplied the goal, role authorization, tools and bounded budget; Master froze the contract and coordination. This Builder Agent implemented the measurement scripts, ran the owned fixture stack, collected evidence and drafted this analysis. Go/PostgreSQL, upstream Pi and both load tools provide the underlying implementation. These Agent-run measurements are not Human's independent implementation work. Only a separate Regulator can issue a Verdict against the final remote SHA; external disclosure or resume-fact promotion needs its own Human authorization.

## Evidence and stop receipt

Persistent local evidence root: `~/.local/state/pi-agent-platform/hey-vegeta3-20261020/`.

- `inventory.json`:322 files,89,904,298 bytes, SHA256 `0f3e0e7450f7ba3d4a53e3e1213ece4804f8cfaf82eff6468e87f6d4cceccb2d`. Each entry records relative path, byte count and SHA256; inventory itself is excluded from its file list.
- `summary.json`: all54 run records,27 cache pairs, nearest-rank metrics, per-run resource observations and separate native Vegeta reports; SHA256 `80879ac179961665ace5e83fe390bc931572c07ed641ef3143a80ff7d6e65d5b`.
- `raw/`: untouched hey CSV/stderr, Vegeta attack binaries/decoded JSONL/native reports/targets, runs.jsonl, source and tool identities, resource snapshots, continuous Docker samples, C10K receipts/logs and stop evidence. The server copy remains under `/media/usv012/pjx/pi-agent-platform/experiments/3/builder/evidence/`.
- `tools/`: the measured Linux hey/Vegeta executables for independent small reproduction; their hashes are above and bound by inventory.
- `summarizer-smoke.json`: Builder isolated parser checks on copied/transformed receipts: valid run accepted for analysis, duplicate identity and missing raw rejected, synthetic404 rows and nonzero process exit never marked normalSuccess. These are parser probes, not live wrong-port/HTTP404 tests; C-HV-04 still requires a new independent Regulator’s actual network probes and clean remote-SHA reproduction.

The original campaign and sampler exited. `raw/stop.json` records successful owned Compose down at12:39:42.549547Z, no remaining owned Compose container and preserved volumes; final-owned-processes.txt independently lists no matching container. preserved-volumes.txt lists exactly `pi-hv3_pg-data` and `pi-hv3_pi-data`. Cleanup’s final attempt to stop already-removed HTTP/SSE generators returned “No such container”; the successful down and empty final process listing establish cleanup rather than treating that message as a surviving process. No historical volume or evidence was deleted.

To independently verify inventory, recompute SHA256 and byte count for every relative path under the registered local root, then run `python3 service/scripts/hey-vegeta/summarize.py /path/to/root/raw` and compare the JSON with summary.json. The new Regulator must also decode the original attack binaries independently, perform the frozen small live reproductions and negative tests, and inspect actual container limits/loopback isolation. The separate Verdict is authoritative for acceptance, not this Builder account.
