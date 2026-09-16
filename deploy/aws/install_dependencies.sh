#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${1:-/srv/aura/.venv/bin/python}"

"${PYTHON_BIN}" -m pip install --upgrade pip
"${PYTHON_BIN}" -m pip install \
  torch==2.6.0 \
  torchvision==0.21.0 \
  --index-url https://download.pytorch.org/whl/cpu
"${PYTHON_BIN}" -m pip install -r requirements.txt
