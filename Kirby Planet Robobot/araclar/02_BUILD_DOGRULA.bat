@echo off
cd /d "%~dp0.."
py -3 araclar\robobo_verify.py
if errorlevel 1 python araclar\robobo_verify.py
pause
