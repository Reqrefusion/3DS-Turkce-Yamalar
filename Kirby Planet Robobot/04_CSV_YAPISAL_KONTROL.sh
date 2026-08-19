#!/usr/bin/env sh
cd "$(dirname "$0")" || exit 1
python3 04_ARACLAR/kirby_msbt_tool.py repair-malformed 01_CEVIRI/MSBT_CSV --column TR_Turkish --report 05_RAPORLAR/CSV_TOKEN_ONARIMI.csv
python3 04_ARACLAR/robobo_verify.py
