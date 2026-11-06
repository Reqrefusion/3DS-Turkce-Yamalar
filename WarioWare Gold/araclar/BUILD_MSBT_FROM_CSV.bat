@echo off
cd /d "%~dp0.."
if exist WORKING_MSBT rmdir /s /q WORKING_MSBT
py -3 araclar\msbt_batch_inject.py 00040000001D1C00\romfs\Message\EU\EUen ceviri WORKING_MSBT --column TR
pause
