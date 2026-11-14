#!/bin/sh
set -eu
cd /media/usv012/pjx
export CUDA_VISIBLE_DEVICES=0
cd /media/usv012/pjx/pi-agent-platform/experiments/24-vllm-serve-20261111/builder
exec taskset -c 0,1 python3 gpu_entry.py "$@"
