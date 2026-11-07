# Pi #12 — Python 3.10 analyzer repair, November 7

Builder candidate; independent Regulator acceptance remains required. Scope is the [Master repair GO](https://github.com/pym96/pi-agent-platform/issues/12#issuecomment-6700285893), following [independent rejection](https://github.com/pym96/pi-agent-platform/issues/12#issuecomment-6700289563). No model, API, client, watchdog, container, SDK, config or runtime behavior changed. No new GPU task was started.

## Failure and minimal fix

The independent Regulator's three-task GPU run used execution commit `2d37849daf7f9b90e4299acafa9e079728ed9a15`. Its analyzer then failed on Python 3.10.12 at the legitimate PostgreSQL timestamp `2026-11-07T01:20:48.25993+00:00`. Python 3.14 accepted the same bytes. The distinction matters: reporting failed after inference completed; it is not evidence of model failure or permission to label the whole delivery accepted.

The Builder reproduced the exact failure through `analyze(root)` against unchanged Regulator originals before editing the parser. A regression reaches that same public interface using the existing CPU fixture. The server also exposed a five-digit timestamp in that older fixture: four preexisting tests failed before reaching their mutations. See [red traceback](red-stderr.txt).

The fix parses the documented timezone-aware PostgreSQL representation with `datetime.strptime`, which accepts one through six fractional digits on Python 3.10. Explicit shape validation rejects naive timestamps, excessive precision, malformed values and trailing text; datetime still validates calendar and offset ranges. Original bytes are not changed. Queue spans still subtract only two PostgreSQL timestamps and reject negative values. No clamping, fallback timestamp or skipped row was added.

Cause was already isolated by the Regulator's cross-version replay; the Builder reproduced that result rather than inventing a broad debugging history. Root cause: the analysis entry relied on the newer `fromisoformat` acceptance behavior without testing the actual host Python version. Existing CI Python 3.12 did not expose it.

## Checks and evidence

- Server Python 3.10.12: [10 required measurement tests](server-final-gate.log) pass, with no missing required IDs/skips. The four new tests cover the exact failure, 0–6 fractional digits across UTC/Z/positive/negative offsets, malformed and naive values, and a negative interval.
- Local Python 3.14: [10 measurement tests](local-measurements.json) pass. [Five required-entry tests](local-required-existing-venv.txt) pass using the preexisting pinned Builder venv. The first attempt with default Python lacked pytest and failed; [that receipt](local-required.txt) is retained. No dependency was installed to hide that result.
- [Exact comparison](cross-version-comparison.json): old analyzer on 3.14, repaired analyzer on 3.14, and repaired analyzer on server 3.10 return identical objects on unchanged November 7 raw. All three task outcomes remain completed; the original execution SHA remains in each result. `integrity_verified=false` remains correct for the producer-only entry; independent externally anchored recomputation is separate.
- The original Regulator `server-final-manifest.json` and its 138 files were rehashed successfully. Originals remain in the Regulator evidence root and were not copied into or rewritten by this candidate. The Builder's full check receipt is `~/.local/state/pi-agent-platform/e2e12-builder-20261107/raw-inventory-verified.json`.
- Existing CI now runs the strict measurement gate under Python 3.10 before restoring Python 3.12 for all existing required suites. CI 3 is authorized once at the final candidate SHA; its result is attached to the external Handoff, not anticipated here.

The [manifest](manifest.json) hashes the small committed receipts. Full red/green source archives, replay programs and command receipts remain at `~/.local/state/pi-agent-platform/e2e12-builder-20261107/`. Server CPU replay copies and outputs are only under `/media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/builder/resume-20261107/`; each replay used an external 60-second SSH bound and a 55-second remote timeout. No server dependency download, service launch or GPU call was performed.

## Handoff identity and limits

The external Handoff binds the final complete candidate SHA, CI 3 and this evidence manifest digest. The new SHA describes analysis repair, not newly executed inference. Regulator evidence remains execution-SHA 2d37849; all service execution files are byte-identical, as shown by the complete base-to-candidate file diff. Independent review must verify this identity separation before reusing the completed GPU evidence.

This work establishes parser portability and preservation of the existing evidence oracle. Three functional tasks do not establish model quality, throughput, latency distributions, C10K or production reliability. Human set scope and resource limits; Builder implemented and tested this repair; Regulator independently found the bug and owns acceptance. Nothing here promotes a resume fact or changes main.
