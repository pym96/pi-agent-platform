# Pi #24 G2 functional integration — candidate

Status: local CPU implementation in progress, not accepted. Baseline `b0ed1c4d6f26d8a3b0c454030606dd598a4f0166`; WorkOrder [#24](https://github.com/pym96/pi-agent-platform/issues/24), C03@1.1/all other Criteria@1.0. No new GPU execution or performance conclusion is implied.

The opt-in [adapter](../../../service/inference/vllm_backend.py) preserves the existing single-slot HTTP module and explicit engine selection. Builder CPU red/green originals, including the initial unbounded test-fixture teardown that required stopping the exact owned test process, are retained outside the public checkout. The corrected fixture uses a finite wait. These tests are native-engine fixtures, not real Qwen evidence.

Human sets project direction; Builder implements and records experiments; the independent Regulator alone provides technical acceptance. Native scheduler-abort acknowledgement is distinguished from immediate GPU kernel preemption. Platform SSE disconnection remains a durable-task subscription event and does not cancel model work. Real direct/platform/fallback matrices and final manifests will be added only after their authorized execution.
