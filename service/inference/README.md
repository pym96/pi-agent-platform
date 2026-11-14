# Inference HTTP API and pytest QA — Pi #9

Pi28 adds default-off `TF_TOKEN_TRACE` observation and [invariance/error tests](tests/test_transformers_observation.py) for the existing Transformers Streamer. The [comparison guide](../scripts/inference-compare/README.md) defines actual-ID provenance, staged execution permission and raw replay. Default generation/template/decode/cancel behavior remains the accepted implementation; CPU observation fixtures do not establish a real-model result.

Opt-in Product module derived from the frozen #7 Transformers adapter. It does not replace the Go/Pi service or deploy by default. CPU fixtures are deterministic; real Qwen verification is a separate, explicitly authorized stage.

## CPU reproduction

Python 3.10+; install only in a dedicated environment. From repository root:

```sh
python3 -m venv /tmp/pi-inference-venv
/tmp/pi-inference-venv/bin/python -m pip install -r service/inference/requirements-test.txt
/tmp/pi-inference-venv/bin/python service/inference/scripts/run_tests.py --out /tmp/pi-inference-result-new
/tmp/pi-inference-venv/bin/python service/inference/scripts/seed_defect.py --out /tmp/pi-inference-defect-new
python3 -m unittest discover -s service/experiments/qwen-load-20261021 -p test_measure.py
```

Output directories must be new and outside the checkout. The wrapper writes JUnit, pytest output, raw HTTP request/response and backend lifecycle receipts, and a machine summary. Zero tests, required skips, failures, errors and nonzero process exit cannot pass. Tests use actual loopback TCP listeners; fixtures close listeners even when assertions fail. Torch/Transformers are lazy imports and are not installed in the CPU environment. Linux systems without ensurepip may bootstrap a dedicated venv from a reviewed wheel bundle; the evidence records all wheel hashes and resolved versions, including Python 3.10 conditional dependencies.

## Supported HTTP contract

`GET /health` reports backend identity, readiness and active/queued counts. Unknown GET routes return 404. `POST /v1/chat/completions` accepts only `model`, `messages`, `stream`, `max_tokens`. Required values: model `Qwen3-8B`, stream `true`, nonempty messages with exactly role/content; role is system/user/assistant and content is a string. Optional max_tokens defaults to 128; it must be an integer 1–128, excluding booleans. Unknown fields are rejected. Malformed or invalid requests return structured 400; body >16384 bytes returns 413. Invalid requests do not generate. Real backend checks actual prompt tokens plus requested generation budget <=1024 before headers.

Success is HTTP 200 `text/event-stream`, ordered deltas, exactly one stop/length terminal with nonnegative integer usage and consistent total, then exactly one `[DONE]`. Post-header backend failure emits an error then `[DONE]`, without a success terminal. The independent oracle rejects partial/error streams, malformed JSON, invalid usage and events after termination. This is a deliberately small compatible subset, not a full OpenAI API or authenticated public service.

One generation slot is held until cooperative backend settlement. Queue capacity is 8; timeout/full returns 503 before headers. Unavailable backend returns 503. Generation deadline emits an explicit stream error. Disconnect signals cancellation and joins the backend before allowing the next generation. A noncooperative native backend may not settle promptly; the external owned-container monitor provides the separate hard stop. No universal in-process forced GPU cancellation guarantee is claimed.

## Real-model stage (Master activation required)

Builder CPU delivery does not claim real-model smoke success. See [evidence](../../docs/evidence/inference-api/README.md) and the later independent Verdict on [Pi #9](https://github.com/pym96/pi-agent-platform/issues/9).

On the authorized Linux host, use a clean checkout of the bound SHA. `config/server.json` pins the existing image, model/dependency locations, manifests and GPU UUID. `guard.py` hashes every manifest entry, checks name/port collisions, then observes the selected GPU idle twice, ten seconds apart. It never starts a model. `launch.sh` repeats this guard before its single owned container and requires explicit activation variables:

```sh
export INFERENCE_STAGE_B=yes SOURCE_SHA=<bound-full-SHA>
export DEADLINE_EPOCH=<fresh-bound-epoch> GUARD_RECEIPT=<new-external-path>
bash service/inference/scripts/launch.sh
```

Run in an observable foreground terminal. This is not an approval mechanism by itself; the WorkOrder and Master activation remain authoritative. The exact container is `pi-inference9-model`, with workorder/source labels. Model allocation is 6 CPU/28 GiB, only the pinned GPU3 UUID, read-only image inputs and source, no changes to shared Docker settings. Linux host networking is used because the application itself binds only `127.0.0.1:18179`; no public listener is configured. Lifetime <=1800 seconds includes startup and guard time. The foreground monitor stops only that exact container on deadline, unrelated GPU compute, interruption or monitor failure.

Independent Regulator performs at most six sequential calls with `scripts/smoke.py --out <new-path> --requests 3` (configurable 1–6), under the authorized client 2 CPU/4 GiB envelope. Requests are recorded before sending; failures stop the script without retry. Capture container logs/inspect and monitor output, stop the owned container early after smoke, verify stopped/listener closed, then remove only that container. Preserve receipts. Do not terminate unrelated processes or reuse #7's expired deadline. No model-quality, throughput or production SLA conclusion follows from this smoke.

## Pi #24 opt-in vLLM adapter (candidate)

`--backend vllm` explicitly selects vLLM0.8.5.post1+cu118 V1/uni; `VLLM_USE_V1=1` is required. The default Transformers choice remains explicit and unchanged. The adapter preserves the existing HTTP contract, BF16/TP1/eager/context1024/maxseq1/prefix-off settings and derives usage from native cumulative token IDs. CPU tests inject only the native engine/tokenizer seam; they are not GPU verification.

Cancellation awaits the fixed-version EngineCore utility response for `abort_requests` after the normal abort IPC. That response establishes scheduler handling, followed by iterator closure. It does not establish immediate GPU kernel preemption. Failed acknowledgements quarantine readiness and retain an unknown active request until the external owned-container stop; they are never reported as settled. The public adapter holds its single slot through this process.

Run the full existing inference wrapper (it includes `tests/test_vllm.py`) in a dedicated CPU environment. [Candidate evidence](../../docs/evidence/pi-vllm-serve-20261111/README.md) distinguishes CPU tests from separately authorized real-model stages.

Pi24 SC-VERSION04: the adapter checks exact module `0.8.5.post1` and exact distribution `0.8.5.post1+cu118` separately. The [official wheel identity fixture](tests/fixtures/vllm_identity/README.md) executes the real version source and distribution metadata; its documented native seams remain CPU substitutes.
