#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
rm -rf WORKING_MSBT
python3 tools/msbt_batch_inject.py PATCH_READY_TECHNICAL/romfs/Message/EU/EUen comparison_csv WORKING_MSBT --column TR
