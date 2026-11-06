#!/usr/bin/env sh

set -eu

cd "$(dirname "$0")/.."

rm -rf WORKING_MSBT

python3 araclar/msbt_batch_inject.py 00040000001D1C00/romfs/Message/EU/EUen ceviri WORKING_MSBT --column TR

