# Source of truth

- Current #28 Product measurement candidate: [engine comparison source/evidence status](docs/evidence/pi-engine-compare-20261114/README.md), [tool interface and execution gates](service/scripts/inference-compare/README.md). Baseline #24 is accepted exact `28a2cf1c5f1d7d692a487d7dd4aae39682f60537`: [final Verdict](https://github.com/pym96/pi-agent-platform/issues/24#issuecomment-6871588663), [merged PR27](https://github.com/pym96/pi-agent-platform/pull/27), [main CI success](https://github.com/pym96/pi-agent-platform/actions/runs/43556161766), [closure](https://github.com/pym96/pi-agent-platform/issues/24#issuecomment-6871706940). Original TF/vLLM remain the Product inference implementations; #28 only adds an opt-in measurement tool and default-off TF observation. Local CPU development is authorized; server/model/push/CI and independent acceptance remain separately gated. Older "current/pending" entries below record historical states and do not override this entry or their original Evidence.

- Current #12 candidate: [E2E1.1 evidence](docs/evidence/pi-qwen-e2e-20261031/README.md), based on accepted Nginx main870575fe697dbc71c7a4ed13ce3c1d76fdb28fed. Stage A CPU has fresh local receipts; GPU0 Stage B/independent final Verdict remain pending. New source/config/GPU0 binding replaces expired historical GPU3 GO, while original evidence remains unchanged.

- Current opt-in experiment: [Qwen real-model load WorkOrder #7](https://github.com/pym96/pi-agent-platform/issues/7), Criteria1.1; [18-run candidate curves and denominators](docs/evidence/qwen-load-20261021/README.md), [measurement code](service/experiments/qwen-load-20261021/README.md). Execution601918 and post-run analysis8c22f4 are separately bound; owned GPU services stopped. Builder results await independent Verdict. Default business service is unchanged.

- Current candidate: [hey / Vegeta WorkOrder #3](https://github.com/pym96/pi-agent-platform/issues/3), Criteria1.0; [candidate evidence](docs/evidence/hey-vegeta-20261020.md) and [reproduction guide](service/scripts/hey-vegeta/README.md). Independent acceptance is separate; the #1 migration entry below retains its original scope.

- Active scope: [independent migration WorkOrder #1](https://github.com/pym96/pi-agent-platform/issues/1), Criteria1.1.
- Product experimental implementation: [service/](service/README.md).
- Evidence: [docs/evidence/](docs/evidence/README.md); historical Pan #142 records and new migration checks are explicitly separated.
- Governance: [AGENTS.md](AGENTS.md). Builder candidate is not an independent acceptance verdict.

No Pan product development, public deployment, paid model calls or GPU work is implied.

- Private career candidate: [WorkOrder #5](https://github.com/pym96/pi-agent-platform/issues/5), Criteria1.0; [three resume drafts and research pack](docs/career/20261021/README.md). Draft only: no independent verdict or Human disclosure approval is implied; business baseline remains f1d172dda9e578cd1ff773363b14f03ff0a1d18d.

- Pi#12 November2 producer evidence: [fresh GPU0 functional run and watchdog correction](docs/evidence/pi-qwen-e2e-20261031/20261102-builder/README.md). Three tasks executed source444096; final delivery adds only the scoped exact-ID watch/CLI guard and documentation. Original watch failure and temporary-path correction remain visible. Main/integration/independent acceptance remain controlled by the Master/Regulator.

- Pi #12 November 7 scoped analyzer repair: [red/green evidence and execution-versus-analysis identity](docs/evidence/pi-qwen-e2e-20261031/20261107-analyzer/README.md). Original 2d37849 GPU evidence remains unchanged; no new GPU run or acceptance is implied.
- Current #13 Product load measurement: [client and execution guide](service/scripts/pi-qwen-load/README.md), [producer CPU evidence](docs/evidence/pi-qwen-load-20261107/README.md). Baseline76ac647 accepted; GPU and independent acceptance remain separately gated.

- #13 [private learning draft](docs/evidence/pi-qwen-load-20261107/LEARNING-DRAFT.md) records trace-failure ownership and deadline/fixture corrections; no public posting or GPU capacity claim.

- Pi13 November10 [actual watch-freshness startup failure and scoped monitoring repair](docs/evidence/pi-qwen-load-20261107/20261110-watch-repair/README.md). Old execution394 and its29.348931seconds/zeroHTTP remain distinct from repaired source; missing real baseline/formal results and independent acceptance are not waived. [Control/diagnostic implementation](service/scripts/pi-qwen-load/README.md) is opt-in measurement only.

- Pi13 [paired actual input candidate](docs/evidence/pi-qwen-load-20261107/20261110-paired-input/README.md): SDK per-session workspace changes are preserved in full payload vectors; new protocol/CPU evidence is separate from failed pilot04 and remains independently gated.

- Pi13 [interrupted campaign accounting repair](docs/evidence/pi-qwen-load-20261107/20261110-interrupt-repair/README.md): retain measured point metrics across idle failures, separate stopped workload from cleanup, and recover immutable partial originals. Formal01 remains partial; no complete load matrix or acceptance is claimed.

- Pi13 [complete formal02 paired baseline](docs/evidence/pi-qwen-load-20261107/20261110-formal02/README.md): actual240sent/219complete/19direct rejected/2platform failed, original raw archives and denominator-aware curves; Product execution260831 unchanged. Independent measurement review is separate from final candidate acceptance and Human disclosure.

- Issue21 November11 [isolated vLLM compatibility candidate](docs/evidence/vllm-compat-20261111/README.md): CPU152 installation and independent import/file audit are [documented](docs/evidence/vllm-compat-20261111/CPU-PREPARATION.md); first Error804 failure is preserved, and [corrected B GPU smoke](docs/evidence/vllm-compat-20261111/gpu-smoke02-summary.json) produced16 tokens under source d803/native535. Independent R also generated16 tokens; final exact-SHA Handoff and G0 Verdict remain pending.

- Issue21 opt-in loader selection: [module and execution limits](service/scripts/vllm-compat/README.md), SC-LOADER-N11-07. Corrected execution source d803 generated16 tokens on both B and independent R; unchanged runtime8399 was produced under90b. Final Verdict remains pending and any additional GPU execution remains separately gated.

- Current Pi #24 G2 candidate: [functional integration evidence](docs/evidence/pi-vllm-serve-20261111/README.md), baseline accepted b0ed. Native V1 adapter CPU development is in progress; GPU/remote CI/final acceptance remain separately gated. Earlier pending entries above are historical at their recorded scope.

- Pi24 SC-VERSION04: [first startup failure and exact module/distribution identity repair](docs/evidence/pi-vllm-serve-20261111/README.md), with [official wheel CPU fixture provenance](service/inference/tests/fixtures/vllm_identity/README.md). Executiona5 failed before model construction; local repair/CPU evidence is not a new model result or acceptance.

- Pi24 C04@1.3: [retired P1 and explicit fixed P2 entry bounds](service/scripts/vllm-serve/README.md), [failure/provenance notes](docs/evidence/pi-vllm-serve-20261111/README.md). New local control-source/CPU checks remain separate from sourceCI3, future model authorization and final acceptance.

- Pi24 C04@1.4 restoration: [independently bound phase input](service/scripts/vllm-serve/README.md) replaces the expired date constant without renewing P1/P2; [restoration and control red/green record](docs/evidence/pi-vllm-serve-20261111/README.md). SourceCI3, affected Linux CPU, full real-model matrices and final independent acceptance remain pending.

- Pi24 SC06 [legacy-test clock repair](docs/evidence/pi-vllm-serve-20261111/README.md): sourceCI3 actually failed because an old positive test used current time against a retired Nov11 GO. Only its test fixture changes through existing `validate(now=...)`; production expiry remains enforced. Local16G0/zero-skip green is separate from pending sourceCI4, server authorization and real-model acceptance.

- Pi24 SC07 [server-Python fixture correction](docs/evidence/pi-vllm-serve-20261111/README.md): original16G0 tests retain all assertions; a concrete Path fallback avoids the observed Python3.10 test-double failure. CI adds the complete suite under its existing3.10 interpreter. Local3.14 green is not a3.10 or GPU result; new actualCI and independent Linux checks remain gated.

- Pi24 November14 [real Builder delivery](docs/evidence/pi-vllm-serve-20261111/20261114/README.md): source9ea normal/deadline/fresh-engine recovery/original Transformers fallback completed with independent stage reports, immutable raw/failure/CI1–5 and actual ledgers. Evidence-only candidate differs from execution source; independent R own actual7native/9POST matrix now also stagePASS; finalCI/exact-SHA Verdict remain pending. Product remains single active generation; no throughput/C10K/p95 or resume fact claim. Earlier pending notes are historical.

- Pi24 [final inventory evidence](docs/evidence/pi-vllm-serve-20261111/20261114/README.md): independent actual host+8PG and local aggregate snapshots now recorded, both projects owned resources0/allSSH released; global CPU4666.4357385, GPU/POST totals unchanged. New Evidence-only identity preserves execution9ea and all original failures. FinalCI6/exact-SHA Verdict and Master integration remain separately gated; sequential/post-write inventory limits are explicit.

#28 source-repair navigation: [comparison source CPU evidence](docs/evidence/pi-engine-compare-20261114/SOURCE-CPU.md) records the original-clock replay and failed native-truth regressions. Local candidate only; independent review/sourceCI/model evidence remain pending.
