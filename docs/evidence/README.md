# Evidence index

## Qwen real-model load experiment — Pi #7

- [Evidence and stage status](qwen-load-20261021/README.md): frozen single-model/runtime workload, streaming measurement and full repetition denominators. Builder candidate; independent Verdict remains separate.

## hey / Vegeta experiment — Pi #3

- [2026-10-20 candidate report](hey-vegeta-20261020.md): real tool matrix, separately identified SSE probe, raw-evidence locators and measurement limits. Builder report; independent Verdict remains separate.
- [Reproduction and verified summary](../../service/scripts/hey-vegeta/README.md): fixed versions, command driver and strict per-run raw-artifact checks.

## Independent repository migration

- [Migration record](MIGRATION.md): new repository/base, ownership, exact source/config deltas and fresh small checks.
- [Source map](migration-map.json): old and new paths/hashes, with reasons for differences.
- [New artifact manifest](migration-manifest.json): migration-only raw evidence. Independent Verdict remains separate.

## Historical experiment — Pan #142

- [Historical report](REPORT.md) and [results](results.json): 13 runs executed under old source aa1d1af, before the repository correction. The old candidate was closed without acceptance/merge.
- [Original 258-artifact manifest](manifest.json), preserved byte-for-byte, SHA256 `41d63495bb54a42e6bb403cb10e519815654521bed40fd7d4abadbc9093cc6fb`.
- [Historical resource arithmetic](summarize-resources.py) and [historical separate suffix-replay probe](replay-suffix.py).

Old run IDs, source SHAs and artifact locators retain their original meaning. Do not rerun historical fixed-root probes against new services or describe these results as a new independent-repository benchmark. No 13-run matrix was repeated for this relocation.

For existing raw receipts, arithmetic remains reproducible:

```sh
python3 service/scripts/analyze.py /path/to/historical/artifacts/raw
python3 docs/evidence/summarize-resources.py /path/to/historical/artifacts/raw
```

Historical database time fields are transaction-start intervals, not exact queue/commit latency. Negative diagnostic values are retained. Separate suffix replay proves recoverability, not that original connections caught up after closure. See the historical report for these and other limits.

## Inference API QA — Pi #9

[CPU evidence and real-stage status](inference-api/README.md): independent HTTP assertions, fault injection and cleanup; real-model review remains separately identified.

- [Nginx CPU entry evidence](nginx-entry-20261025/README.md): Pi #15 candidate receipts, isolated routing/stream contracts and exploratory HTTP measurements; acceptance is separate.

## Pi #12 real-Qwen integration candidate

[2026-10-31 E2E1.1 evidence](pi-qwen-e2e-20261031/README.md): actual SDK/PG CPU chain and strict required-suite/provenance checks. Fresh host physical GPU0 execution and independent acceptance are pending; historical GPU3 samples are preserved with their original identity.

## Pi #12 November2 functional producer delivery

[Fresh GPU0 chain, failed-watch original and narrow correction](pi-qwen-e2e-20261031/20261102-builder/README.md): three successful real tasks at execution source444096, explicit usage/device/PG/SSE provenance, bounded lifecycle and actual CPU watcher controls. Final delivery source/CI and independent Verdict are bound externally; no acceptance or capacity claim is implied. The prior157-entry manifest/source snapshot is preserved unchanged; the dated subtree has a separate inventory.

- [Pi #13 CPU measurement candidate](pi-qwen-load-20261107/README.md): actual HTTP/CLI tests; no GPU capacity or independent acceptance implied.

- Issue21 November11 [isolated vLLM compatibility candidate](vllm-compat-20261111/README.md): CPU preparation/source tests only; runtime and independent GPU compatibility remain unverified.
