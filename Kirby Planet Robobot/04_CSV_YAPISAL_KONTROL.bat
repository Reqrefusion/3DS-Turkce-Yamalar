@echo off
cd /d "%~dp0"
py -3 04_ARACLAR\kirby_msbt_tool.py repair-malformed 01_CEVIRI\MSBT_CSV --column TR_Turkish --report 05_RAPORLAR\CSV_TOKEN_ONARIMI.csv
py -3 04_ARACLAR\robobo_verify.py
if errorlevel 1 python 04_ARACLAR\robobo_verify.py
pause
