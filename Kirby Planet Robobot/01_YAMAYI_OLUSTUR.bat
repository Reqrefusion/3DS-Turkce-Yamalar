@echo off
cd /d "%~dp0"
py -3 04_ARACLAR\robobo_build.py
if errorlevel 1 python 04_ARACLAR\robobo_build.py
pause
