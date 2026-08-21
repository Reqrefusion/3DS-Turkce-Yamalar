@echo off
cd /d "%~dp0"
if exist WORKING_MSBT rmdir /s /q WORKING_MSBT
py -3 tools\msbt_batch_inject.py PATCH_READY_TECHNICAL\romfs\Message\EU\EUen comparison_csv WORKING_MSBT --column TR
pause
