#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 tools/verify_package.py .
