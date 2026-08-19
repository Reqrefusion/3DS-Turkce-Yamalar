@echo off
cd /d "%~dp0"
py -3 04_ARACLAR\robobo_verify.py
if errorlevel 1 python 04_ARACLAR\robobo_verify.py
pause
