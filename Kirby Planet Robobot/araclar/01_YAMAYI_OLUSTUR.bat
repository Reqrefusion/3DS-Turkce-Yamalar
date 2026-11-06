@echo off
cd /d "%~dp0.."
py -3 araclar\robobo_build.py
if errorlevel 1 python araclar\robobo_build.py
pause
