#!/usr/bin/env sh
cd "$(dirname "$0")/.." || exit 1
python3 araclar/kirby_msbt_tool.py repair-malformed ceviri/MSBT_CSV --column TR_Turkish --report raporlar/CSV_TOKEN_ONARIMI.csv
python3 araclar/robobo_verify.py
