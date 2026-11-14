#!/bin/sh
set -eu
cd /media/usv012/pjx
export CUDA_VISIBLE_DEVICES=0
cd /media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder
exec taskset -c 0,1 python3 gpu_entry_nov14.py "$@" --phase-contract /media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder/PHASE-CONTRACT.v2.json --phase-contract-sha256 77b6d5aa360e46cdde73fa36bdff344c89769973e56c48733b43ac258d763887
