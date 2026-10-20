# Owned hey / Vegeta experiment

This directory adds measurement tooling, without changing service behavior. Run from
`service/` on the owned Linux host. Read [the experiment report](../../../docs/evidence/hey-vegeta-20261020.md)
and WorkOrder Pi #3 before reuse. Use a fresh directory/project and preserve failed attempts.

The frozen matrix is hey v0.1.4, HTTP health/history, c=1/10/100, n=1000,
three repetitions, followed by Vegeta v12.12.0 history at 10/100/500 requests/s,
10 seconds and three repetitions. Both cache states run serially. HTTP/1.1,
keepalive enabled, redirects disabled and 5-second request timeout are fixed.
The final optional probe uses the existing dedicated 10,000-connection SSE generator
for 120 seconds. That is separate from HTTP request rate and two bounded Pi workers.

Build the official fixed tools into a run-specific directory, never globally. The
recorded build used macOS Go1.27.1 to cross-compile Linux amd64 executables, with
GOMAXPROCS=1, `go install -p=1`, CGO disabled and GOMEMLIMIT=800MiB; this memory
setting is a Go runtime target, not a hard OS limit. Service build and all measured
processes use hard-limited Linux containers. For example, with a temporary GOPATH:

```sh
env GOOS=linux GOARCH=amd64 CGO_ENABLED=0 GOMAXPROCS=1 GOMEMLIMIT=800MiB \
 GOPATH=/path/to/run/gopath go install -p=1 github.com/rakyll/hey@v0.1.4
env GOOS=linux GOARCH=amd64 CGO_ENABLED=0 GOMAXPROCS=1 GOMEMLIMIT=800MiB \
 GOPATH=/path/to/run/gopath go install -p=1 github.com/tsenart/vegeta/v12@v12.12.0
# Copy GOPATH/bin/linux_amd64/{hey,vegeta} into RUN_ROOT/tools on Linux.
```

Official tool documentation: [hey](https://github.com/rakyll/hey),
[Vegeta](https://github.com/tsenart/vegeta). Retain `go version -m` output and
SHA256 of each executable. Do not assume a bare Vegeta `-version` identifies the
module when built with go install.

Set `RUN_ROOT`, `NODE_ROOT`, `GO_ROOT`, `PRIOR_CACHE` (preexisting dependency cache),
`EVIDENCE_ROOT=$RUN_ROOT/evidence`, `SOURCE_SHA` (full frozen execution commit) and
optionally `HV_PROJECT` (default `pi-hv3`). `NODE_ROOT` is an actual Linux Node
distribution. Do not use historical fixed-root scripts against another project.

```sh
sh scripts/hey-vegeta/setup.sh
# In a separate foreground terminal, for continuous Docker CPU/memory samples:
python3 scripts/hey-vegeta/sample.py
# In the experiment foreground terminal:
python3 scripts/hey-vegeta/run.py
python3 scripts/hey-vegeta/summarize.py "$RUN_ROOT/evidence" > "$RUN_ROOT/summary.json"
```

The driver writes before/after process FD, RSS, CPU jiffies, nofile, Docker stats
and existing API goroutine metrics for each run. Continuous sampling is optional;
samples can miss short HTTP bursts and must not be described as exact peaks.
The measured campaign started the continuous sampler after its first 14 hey runs;
before/after snapshots cover every run. `sample.py` exits when stop.json appears
or after 900 seconds. The driver refuses to append a fresh campaign over existing
`runs.jsonl`; per-run exit codes, errors and omitted transport-error samples remain.

`summarize.py` verifies every per-run hash, run identity, primary-raw reuse and the
complete matrix by default. `--allow-partial` is only for isolated probes and never
a complete campaign claim. HTTP non-2xx and absent hey transport-error rows are
failed/unobserved requests; their latency is never fabricated. Failed process exits
cannot become normalSuccess. Native Vegeta interpolated percentiles remain under
nativeReport; the separate P50/P95/P99 values use nearest rank on raw observations.
hey CSV rounds seconds to four decimal places, limiting reported latency precision.

The driver stops only the exact owned Compose project and owned load names, leaves
both volumes intact and writes stop.json. A caller must still inspect the receipt
and confirm no owned process survives before Handoff. A disconnected SSH session
is not a stop receipt. Reuse on a shared host requires the same aggregate 4 CPU /
8 GiB envelope, loopback port ownership, disk floor and bounded deadline.
