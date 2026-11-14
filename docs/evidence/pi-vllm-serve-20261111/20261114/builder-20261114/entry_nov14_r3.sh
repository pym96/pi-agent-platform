#!/bin/sh
set -eu
cd /media/usv012/pjx
export CUDA_VISIBLE_DEVICES=0
cd /media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder
exec taskset -c 0,1 python3 gpu_entry_nov14_r3.py "$@" --phase-contract /media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/PHASE-CONTRACT.v3.json --phase-contract-sha256 82f15dcf6523c8bbea36bd79741fc8c9745fd838024004ad592979ad2b6830ec
