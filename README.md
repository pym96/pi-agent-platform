# Pi Agent Platform

Current work is [#28 matched engine measurement](service/scripts/inference-compare/README.md), a Product opt-in measurement candidate based on accepted #24 exact `28a2cf1c5f1d7d692a487d7dd4aae39682f60537`; see [current source and phase status](SOURCE_OF_TRUTH.md). Older pending candidate notes below are historical snapshots. Original Transformers and fixed single-sequence vLLM remain Product inference implementations; local CPU checks are separate from model permission, performance results and independent acceptance.

An independent experimental Go/PostgreSQL service built around the upstream Pi SDK. Submit a text task, follow committed events over SSE, reconnect by cursor, and retrieve persisted history after restart. Pi owns finalized model context; PostgreSQL owns task state and observable events. Uncertain execution is exposed without automatic model resend.

The default endpoint is a deterministic local streaming fixture consumed by **actual Pi 1.3.0**, not an LLM. No paid API, GPU, frontend or Redis is required. This is a private single-owner development stack, not a production or public multi-user service.

## First task on Linux (no GPU)

Use a Linux **amd64** development machine you manage, with Docker Engine and Compose v2, Go 1.24+, Node 22.19+, npm, git, curl and GNU `readlink`. The host-built Go binary and Node installation must match the Linux containers; macOS binaries are not substitutes. First use can download Go modules, npm packages and pinned container images. This is not an offline setup.

These commands use the accepted baseline for the default fixture. They are source-reviewed examples and **were not run on the current machine for this guide**. Use free local ports 18151/18152 and a fresh `pi-onboarding` Compose project; shared experiment servers require their own authorization.

### Build, start and check the API

```sh
git clone https://github.com/pym96/pi-agent-platform.git pi-onboarding
cd pi-onboarding
git checkout --detach 28a2cf1c5f1d7d692a487d7dd4aae39682f60537
cd service
./scripts/build.sh
export NODE_ROOT="$(dirname "$(dirname "$(readlink -f "$(command -v node)")")")"
export EVIDENCE_ROOT="$PWD/scratch/evidence"
mkdir -p "$EVIDENCE_ROOT"
docker compose -p pi-onboarding up -d pg pi api
docker compose -p pi-onboarding ps
curl --ipv4 --noproxy '*' --fail --show-error --max-time 5 \
  http://localhost:18151/health
```

`NODE_ROOT` must contain the actual Linux `bin/node`, not a toolchain shim. `EVIDENCE_ROOT` is required by the Compose file even though this guide does not start the optional load service. API health should return HTTP200 with `ok: true`, `runtime: "actual Pi 1.3.0"` and `model: "synthetic local baseline"`. It checks PostgreSQL, not Pi or model completion.

### Wait for Pi before submitting a task

The API waits for PostgreSQL at startup, but not Pi. Run this GET-only check after API health; it stops after at most30 seconds, with a2-second limit per request:

```sh
node --dns-result-order=ipv4first --input-type=module <<'NODE'
const until = Date.now() + 30_000;
let last = 'Pi executor has not responded';
const hardStop = setTimeout(() => {
  console.error('Pi startup check timed out:', last);
  process.exit(1);
}, 30_000);
while (Date.now() < until) {
  try {
    const response = await fetch('http://localhost:18152/metrics', {
      signal: AbortSignal.timeout(Math.max(1, Math.min(2_000, until - Date.now())))
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const metrics = await response.json();
    if (metrics.pi !== '1.3.0' || metrics.endpointKind !== 'synthetic' ||
        !Number.isInteger(metrics.active) || metrics.active < 0) {
      throw new Error('unexpected Pi fixture metrics');
    }
    console.log('Pi HTTP executor is listening; model completion is not yet verified.', metrics);
    clearTimeout(hardStop);
    process.exit(0);
  } catch (error) {
    last = error.message;
  }
  await new Promise(resolve => setTimeout(resolve, Math.min(500, Math.max(0, until - Date.now()))));
}
clearTimeout(hardStop);
console.error('Pi startup check timed out:', last);
process.exit(1);
NODE
```

If it fails, stop here and inspect `docker compose -p pi-onboarding logs --tail=100 pi`; do not probe readiness by resending tasks. Matching metrics show that Pi is listening after global runtime/provider/model initialization. They do not verify per-task session creation or the separate fixture process. API health and Pi metrics both leave end-to-end completion unproven. See [Pi initialization](service/pi/server.mjs) and [Compose dependencies](service/compose.yaml).

### Submit once, then observe completion

```sh
curl --ipv4 --noproxy '*' --fail --show-error --max-time 10 -i \
  -H 'Content-Type: application/json' \
  -d '{"key":"hello-1","prompt":"Hello"}' \
  http://localhost:18151/sessions/onboarding-1/tasks

curl --ipv4 --noproxy '*' --fail --show-error --max-time 5 \
  http://localhost:18151/sessions/onboarding-1/tasks

curl --ipv4 --noproxy '*' -N --max-time 20 \
  http://localhost:18151/sessions/onboarding-1/events
```

The first POST should return **202** with a task object (`id`, `session`, `key`, `prompt`, `status: "queued"`). Recheck history with GET while it is queued/running. `completed` is the end-to-end completion observation; the fixture's first-turn expected text is `Synthetic reply 1: Hello`, derived from [its source](service/pi/model.mjs), not a new run in this guide. SSE replays committed `queued`, `running`, `text`, `result` and `completed` events, then keeps waiting; curl's20-second timeout or Ctrl-C closes the subscription without cancelling the durable task.

Use a new key for a new turn. Same session/key/prompt returns the original task (HTTP200); changing the prompt under that key returns409. If `onboarding-1` already has history, use a fresh session such as `onboarding-2`. Session/key allow1–64 ASCII letters, digits, `_` or `-`; prompt limit8192 bytes. For reconnects, use your last processed event ID as `Last-Event-ID` and deduplicate IDs. See [service APIs and recovery](service/README.md).

### Stop and retain history

```sh
docker compose -p pi-onboarding logs --tail=100 api pi pg
docker compose -p pi-onboarding down
```

Do not add `-v`: PostgreSQL tasks/events and Pi context live in separate volumes. Interrupted execution can block a session; the platform does not automatically resend model requests. Preserve the volumes and logs before investigating. Keep access private and local. The optional `scripts/smoke.py` sends additional normal and fault tasks; it is not required for this first task.

For real Qwen, read the [inference service](service/inference/README.md) and [opt-in comparison guide](service/scripts/inference-compare/README.md) separately. Its `/v1/chat/completions` differs from the Go task API. Fixture completion proves neither Qwen loading nor GPU scheduling; real-model execution needs compatible cached weights/runtime and separate resource authorization. No new comparison curves or performance claim follow from this onboarding guide.

## Design and evidence

- [Qwen real-model load experiment — Pi #7](docs/evidence/qwen-load-20261021/README.md): opt-in, separately bounded engine measurements; stage status and independent review are explicit.
- [Service](service/README.md): bounded workers, idempotent submission, durable events, SSE replay and failure recovery.
- [Evidence index](docs/evidence/README.md): historical load results and separate independent-repository validation.
- [hey / Vegeta candidate experiment](docs/evidence/hey-vegeta-20261020.md): bounded HTTP measurements and a separately identified SSE connection probe; independent review remains separate.
- [Migration provenance](docs/evidence/MIGRATION.md): source mapping and changed executable/configuration identities.
- [Upstream attribution](service/UPSTREAM.md) and [MIT license](LICENSE).

This repository contains no Pan Runtime/TUI/workbench or Pan Git history. Its initial experimental service source came from an unaccepted archived Pan candidate after Human corrected the repository boundary. Historical results retain their old source SHA and run IDs. They are not new measurements or production capacity evidence for this repository.

- [Inference API pytest QA — Pi #9](service/inference/README.md): opt-in CPU contract/fault tests and separately authorized real-model smoke.

The optional [private Nginx CPU entry](service/scripts/nginx-entry/README.md) tests streaming proxy semantics and labelled fixture routing while preserving the single-controller contract.

## Historical integration evidence

- [Pi #12 E2E1.1 evidence](docs/evidence/pi-qwen-e2e-20261031/README.md): dated actual SDK/PG CPU-chain and real-Qwen provenance. Original source/run identities stay attached to those records.
- [Pi #21 isolated vLLM compatibility evidence](docs/evidence/vllm-compat-20261111/README.md), [CPU preparation](docs/evidence/vllm-compat-20261111/CPU-PREPARATION.md) and [corrected smoke record](docs/evidence/vllm-compat-20261111/gpu-smoke02-summary.json).
- [Pi #24 vLLM adapter evidence](docs/evidence/pi-vllm-serve-20261111/README.md): the accepted baseline is exact `28a2cf1c5f1d7d692a487d7dd4aae39682f60537`, with [final Verdict](https://github.com/pym96/pi-agent-platform/issues/24#issuecomment-6871588663), [merged PR27](https://github.com/pym96/pi-agent-platform/pull/27) and [main CI](https://github.com/pym96/pi-agent-platform/actions/runs/43556161766).

Older pending statements inside dated evidence describe their recorded stage. Follow the current #28 navigation at the top for the active candidate; historical runs do not establish current candidate acceptance or new inference performance.
