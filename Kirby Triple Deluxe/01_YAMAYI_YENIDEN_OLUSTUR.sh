#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 03_ARACLAR/build_patch.py
