#!/usr/bin/env bash
set -euo pipefail
: "${INFERENCE_STAGE_B:?Master activation required}"
: "${SOURCE_SHA:?Exact reviewed execution SHA required}"
: "${DEADLINE_EPOCH:?Fresh Master-bound deadline required}"
: "${GUARD_RECEIPT:?New external guard receipt path required}"
test "$INFERENCE_STAGE_B" = yes
repo=$(git rev-parse --show-toplevel)
test "$(git rev-parse HEAD)" = "$SOURCE_SHA"
test -z "$(git status --porcelain)"
python3 - "$DEADLINE_EPOCH" <<'PY'
import sys,time
assert time.time()<float(sys.argv[1])<=time.time()+1800
PY
python3 "$repo/service/inference/scripts/guard.py" --config "$repo/service/inference/config/server.json" --out "$GUARD_RECEIPT"
docker run -d --name pi-inference9-model --label workorder=9 --label "execution-sha=$SOURCE_SHA" \
 --user 1001:1001 --runtime nvidia --gpus device=GPU-dd5fc05f-7d4d-17f7-8d33-2f474b56b74e \
 --network host --cpus 6 --memory 28g --memory-swap 28g --pids-limit 256 \
 --read-only --tmpfs /tmp:size=512m --shm-size 512m --cap-drop ALL --security-opt no-new-privileges \
 -v /media/usv012/pjx/agent/Qwen3-8B:/model:ro \
 -v /media/usv012/pjx/pi-agent-platform/experiments/7-qwen-load-20261021/deps:/deps:ro \
 -v "$repo:/source:ro" -e PYTHONPATH=/source:/deps -e PYTHONDONTWRITEBYTECODE=1 \
 -e CUDA_VISIBLE_DEVICES=0 -e OMP_NUM_THREADS=6 -e TOKENIZERS_PARALLELISM=false \
 -w /source --entrypoint python sha256:7e8449fcd1ce73c68dc35292e94182a3b09ddf155eba052fafcb0b6cf174c1c2 \
 -m service.inference --backend transformers --port 18179 --deadline-epoch "$DEADLINE_EPOCH"
# Remains foreground; operator may stop the owned container earlier after smoke.
python3 "$repo/service/inference/scripts/watch.py" --sha "$SOURCE_SHA" --deadline "$DEADLINE_EPOCH"
