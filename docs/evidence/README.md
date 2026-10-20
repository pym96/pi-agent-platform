# Evidence index

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
