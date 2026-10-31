# Proposed Stage B command plan, not an execution GO

Status: not executed. Authorized SSH is currently unavailable. Master must bind a literal execution SHA, config digest, fresh deadline and these commands before use. B/R do not share projects/volumes. The initial planned Builder stack is pi-e2e12-1031-b; Regulator independently prepares its own variant and binary.

Preparation paths and inputs:

- Host root `/media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/builder`; source in source/, originals in evidence/.
- SOURCE_SHA is the literal candidate execution SHA in the future GO; DEADLINE_EPOCH is a literal Master-issued epoch no more than900seconds ahead, never extended by a later command.
- NODE_ROOT `/media/usv012/pjx/pi-agent-platform/experiments/1/toolchains/node-v22.23.3`; PI_MODULES `/media/usv012/pjx/pi-agent-platform/experiments/3/builder/source/service/pi/node_modules` (existing locked SDK).
- Existing Python image `python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`, PostgreSQL digest and model image/config unchanged except explicit GPU0/role/new-stack limits.
- New source arrives through a local git bundle of the candidate branch, cloned under the new host root so HEAD and tracked-clean checks work. A separately identified CGO_ENABLED=0 Linux/amd64 API binary is copied only to ignored service/bin/service. Record go version/buildinfo/hash; do not call the model during compilation.

Before model startup: verify host GPU index0 UUID GPU-3c2dd9d8-e925-9c8e-373e-efc7b1222ead, free≥20GiB, aggregate newdisk≤2GiB, available memory≥40GiB, free18181–18183, no old project objects, exact model/deps manifests and images. Derive the existing inference guard config by adding only container=pi-e2e12-1031-b-model-1 and port=18181 to the exact stage-b.json; retain both hashes and field-equivalence receipt. Run its two checks at least10seconds apart with no foreign target-GPU compute PID. Every actual remote command starts by cd to this authorized root/source and explicitly sets CUDA_VISIBLE_DEVICES=0.

Run the real client permission probe before Stage B, under these exact client container settings (CPU only; no HTTP/model request): read-only root, UID1001:1001, cap-dropALL, no-new-privileges,2CPU/5GiB, /tmp tmpfs256MiB, sourceRO/evidenceRW, same immutable Python image. The probe writes/fsyncs a new evidence file and verifies actual UID/GID1001. Do not chmod shared paths to force success. Record inspect, exit, stdout and cleanup. Host-bind target source/service/pi/node_modules must already exist before mounting sourceRO.

Foreground watchdog command (a separate supervised SSH exec; must be running before compose up):

```sh
cd /media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/builder/source
export CUDA_VISIBLE_DEVICES=0
python3 service/scripts/pi-qwen-e2e/watch.py --project pi-e2e12-1031-b \
  --sha "$SOURCE_SHA" --deadline "$DEADLINE_EPOCH" \
  --root /media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/builder \
  --out /media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/builder/evidence/watch.jsonl
```

After GO/guard/watch, compose command (SOURCE_SHA/DEADLINE_EPOCH/NODE_ROOT/PI_MODULES must be the frozen literal values supplied by the GO):

```sh
cd /media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/builder/source
export CUDA_VISIBLE_DEVICES=0 E2E_PROJECT=pi-e2e12-1031-b
export NODE_ROOT=/media/usv012/pjx/pi-agent-platform/experiments/1/toolchains/node-v22.23.3
export PI_MODULES=/media/usv012/pjx/pi-agent-platform/experiments/3/builder/source/service/pi/node_modules
# Capture config, image identities, ports/resources first; do not pull model weights.
docker compose -p "$E2E_PROJECT" -f service/compose.qwen.yaml config
docker compose -p "$E2E_PROJECT" -f service/compose.qwen.yaml up -d pg model pi api
```

Wait for health endpoints only within the same deadline, stopping on any error. Save raw GET receipts for model18181/health, Pi18182/metrics and API18183/health. No warmup generation. Inspect all four containers; model6CPU/28GiB, PG1/1, API1/2, Pi2/4. Physical GPU UUID and container UUID must match. Then capture device proof on the host:

```sh
cd /media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/builder/source
export CUDA_VISIBLE_DEVICES=0
python3 service/scripts/pi-qwen-e2e/device_proof.py --project pi-e2e12-1031-b \
  --sha "$SOURCE_SHA" --out ../evidence/device-identity
```

Actual client command: its output directory is new and evidence parent passed the permission probe. The client receives no Docker socket or NVIDIA device. It makes exactly three sequential tasks; any failure stops the owned stack and preserves originals, with no retry.

```sh
cd /media/usv012/pjx/pi-agent-platform/experiments/12-pi-qwen-e2e-20261031/builder/source
export CUDA_VISIBLE_DEVICES=0 E2E_PROJECT=pi-e2e12-1031-b
docker run --rm --name "$E2E_PROJECT-client" --network host \
  --label com.docker.compose.project="$E2E_PROJECT" --label workorder=12 \
  --label execution-sha="$SOURCE_SHA" --user 1001:1001 \
  --read-only --tmpfs /tmp:size=256m --cap-drop ALL --security-opt no-new-privileges:true \
  --cpus 2 --memory 5g --memory-swap 5g \
  -v "$PWD:/source:ro" -v "$PWD/../evidence:/evidence" \
  -e PYTHONDONTWRITEBYTECODE=1 -e CUDA_VISIBLE_DEVICES=0 -w /source \
  --entrypoint python \
  python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 \
  service/scripts/pi-qwen-e2e/smoke.py --prefix builder1031 --sha "$SOURCE_SHA" \
  --identity /evidence/device-identity --out /evidence/smoke
```

Stop/collect protocol: keep raw Pi bridge, API logs/parsed Go trace, PostgreSQL ordered row_to_json(events), client tasks/attempts/health, actual inspect/runtime versions and all failures. Stop the exact owned project in a finally path even if collection fails. Retain diagnostic volumes and list them. Verify no owned running containers/watch/client/listeners or target-GPU owned compute remain. Sum all startup→stop lifetimes conservatively with the historical502seconds and all attempts including failures. Seal receipts only after cleanup; copy the resulting external digest to the Handoff before independent recomputation.

Expected inspect proof is enforced by device_proof.validate: image ID, physical host0/UUID, visible container0/sameUUID, CUDA/NVIDIA env, exact execution labels/new project, read-only source/model/deps paths, UID1001, cap-dropALL, hard6CPU/28GiB and3-attempt argv. This is preparation, not a claim that any of these live commands succeeded.
