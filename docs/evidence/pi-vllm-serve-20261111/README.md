# Pi #24 G2 functional integration — candidate

Status: local CPU implementation in progress, not accepted. Baseline `b0ed1c4d6f26d8a3b0c454030606dd598a4f0166`; WorkOrder [#24](https://github.com/pym96/pi-agent-platform/issues/24), C03@1.1/C04@1.2/C01–02@1.0. No new GPU execution or performance conclusion is implied.

The opt-in [adapter](../../../service/inference/vllm_backend.py) preserves the existing single-slot HTTP module and explicit engine selection. Builder CPU red/green originals, including the initial unbounded test-fixture teardown that required stopping the exact owned test process, are retained outside the public checkout. The corrected fixture uses a finite wait. These tests are native-engine fixtures, not real Qwen evidence.

Human sets project direction; Builder implements and records experiments; the independent Regulator alone provides technical acceptance. Native scheduler-abort acknowledgement is distinguished from immediate GPU kernel preemption. Platform SSE disconnection remains a durable-task subscription event and does not cancel model work. Real direct/platform/fallback matrices and final manifests will be added only after their authorized execution.

Local CPU deployment failures remain preserved: missing ignored nested SDK mount target caused the first Docker startup failure; a second run proved container readiness while internal networking left host published ports unavailable. A separate no-GPU exact-owned probe established host access to the internal bridge IPv4. G2.3 therefore preserves internal networking, removes host-port publication and binds the actual endpoint map. These are CPU deployment observations, not GPU/model success. Cleanup success on the original failure receipts is scoped to cleanup; new receipts separate overall and cleanup success.

## November 11 first real startup failure and identity repair

Execution `a5f161b65126d3f5cbd9670bd85099217f38e750` failed before engine construction: the adapter incorrectly compared module `__version__` against the CUDA-tagged distribution string. Official wheel/runtime source sets the module to `0.8.5.post1`, while distribution metadata is `0.8.5.post1+cu118`. The original CPU test had placed the distribution string into a fake module, concealing this defect. Builder owns that implementation/test error; the initial independent source review also missed the distinction. Actual execution corrected the conclusion.

The failed model container exited1, with no readiness, native generation or completion POST. Its conservative created-to-confirmed-removal cost is55.169294118881226 seconds; actual running time is recorded separately. All four owned containers and that lifecycle's network were removed. Raw archive SHA256 `2d7d0b64ecd6306299a6ce09dfb942c2124dda4f0fb09bb697cb3e31f1fa278d` and release SHA256 `31ca559293ed30c69e1f567b5f7273b548e8c17946933c274e319a2c27de93ac` remain in the external workorder evidence; the failure is not replaced by the repair.

SC-VERSION04 authorizes only exact module/distribution checks and [actual wheel identity CPU tests](../../../service/inference/tests/fixtures/vllm_identity/README.md), without changing runtime8399, model, CUDA driver, engine parameters, Go or Pi. Real old-red/new-green and wrong/missing-identity negatives are separate from any later Linux import, source CI, real-model retry or independent acceptance.
