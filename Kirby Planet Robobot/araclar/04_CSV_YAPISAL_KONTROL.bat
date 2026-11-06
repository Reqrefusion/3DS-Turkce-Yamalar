@echo off
cd /d "%~dp0.."
py -3 araclar\kirby_msbt_tool.py repair-malformed ceviri\MSBT_CSV --column TR_Turkish --report raporlar\CSV_TOKEN_ONARIMI.csv
py -3 araclar\robobo_verify.py
if errorlevel 1 python araclar\robobo_verify.py
pause
