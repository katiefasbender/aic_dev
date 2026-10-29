#!/usr/bin/env bash

set -e
source ~/hdps/.venv/bin/activate
export PYTHONUNBUFFERED=1
uv run ~/aic_dev/minipix_counting/minipix_per_mag.py --catalog panstarrs 