#!/usr/bin/env bash
set -euo pipefail
: "${PI_QWEN7_STAGE_B:?Master StageB activation required}"
: "${PI_QWEN7_CODE_SHA:?Frozen remote execution SHA required}"
test "$PI_QWEN7_STAGE_B" = yes
pi7_root=/media/usv012/pjx/pi-agent-platform/experiments/7-qwen-load-20261021
pi7_gpu=GPU-dd5fc05f-7d4d-17f7-8d33-2f474b56b74e
pi7_image=sha256:7e8449fcd1ce73c68dc35292e94182a3b09ddf155eba052fafcb0b6cf174c1c2
for pi7_observation in 1 2; do
    date -u
    nvidia-smi -i "$pi7_gpu" --query-gpu=uuid,memory.used,utilization.gpu --format=csv,noheader,nounits
    python3 - "$pi7_gpu" <<'PY'
import subprocess,sys
uuid=sys.argv[1]
apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader,nounits'],text=True)
assert not any(line.split(',')[0].strip()==uuid for line in apps.splitlines()), 'GPU has other compute processes'
row=subprocess.check_output(['nvidia-smi','-i',uuid,'--query-gpu=memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True)
memory,util=[float(v.strip()) for v in row.split(',')]
assert memory<1024 and util<=5,(memory,util)
PY
    if test "$pi7_observation" = 1; then sleep 10; fi
done
if ss -ltnH | awk '{print $4}' | grep -q ':18171$'; then
    echo 'Port18171 occupied; refusing startup' >&2;exit 1
fi
docker run -d --name pi-qwen7-model --label workorder=7 --label "execution-sha=$PI_QWEN7_CODE_SHA" \
    --user 1001:1001 \
    --runtime nvidia --gpus "device=$pi7_gpu" --cpus 6 --memory 28g --memory-swap 28g --pids-limit 256 \
    --read-only --tmpfs /tmp:size=512m --shm-size 512m --cap-drop ALL --security-opt no-new-privileges \
    -p 127.0.0.1:18171:18171 -v /media/usv012/pjx/agent/Qwen3-8B:/model:ro \
    -v "$pi7_root:/experiment:ro" -e PYTHONPATH=/experiment/deps -e PYTHONDONTWRITEBYTECODE=1 \
    -e NVIDIA_VISIBLE_DEVICES="$pi7_gpu" -e CUDA_VISIBLE_DEVICES=0 \
    -e "PI_QWEN7_CODE_SHA=$PI_QWEN7_CODE_SHA" -e OMP_NUM_THREADS=6 -e TOKENIZERS_PARALLELISM=false \
    -w /tmp --entrypoint python "$pi7_image" /experiment/code/transformers_server.py
