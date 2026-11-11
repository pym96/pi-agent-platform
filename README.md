# Pi Agent Platform

An independent experimental Go/PostgreSQL service built around the upstream Pi SDK. Submit a text task, follow committed events over SSE, reconnect by cursor, and retrieve persisted history after restart. Pi owns finalized model context; PostgreSQL owns task state and observable events. Uncertain execution is exposed without automatic model resend.

The default endpoint is a deterministic local streaming fixture consumed by **actual Pi 1.3.0**, not an LLM. No paid API, GPU, frontend or Redis is required. This is a private single-owner development stack, not a production or public multi-user service.

## Start on a Linux server

Requires Docker Engine/Compose, Go 1.24+, Node 22.19+ and npm. Host binaries must match the Linux container architecture (measured amd64).

```sh
cd service
./scripts/build.sh
export NODE_ROOT="$(dirname "$(dirname "$(command -v node)")")"
export EVIDENCE_ROOT="$PWD/scratch/evidence"
mkdir -p "$EVIDENCE_ROOT"
docker compose up -d pg pi api
python3 scripts/smoke.py
# API: http://127.0.0.1:18151; executor diagnostics: 18152.
# Stop this project while retaining its two data volumes:
docker compose down
```

`NODE_ROOT` must identify the actual Linux Node installation, not a shim or macOS binary. Read [service setup, APIs and recovery boundaries](service/README.md) before running fault/load probes.

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

## Pi #12 real-Qwen integration candidate

[2026-10-31 E2E1.1 evidence](docs/evidence/pi-qwen-e2e-20261031/README.md): actual SDK/PG CPU chain and strict required-suite/provenance checks. Fresh host physical GPU0 execution and independent acceptance are pending; historical GPU3 samples are preserved with their original identity.

- Issue21 November11 [isolated vLLM compatibility candidate](docs/evidence/vllm-compat-20261111/README.md): CPU preparation/source tests only; runtime and independent GPU compatibility remain unverified.
