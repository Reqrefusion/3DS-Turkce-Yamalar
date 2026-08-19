@echo off
chcp 65001 >nul
cd /d "%~dp0"
python "03_ARACLAR\build_patch.py"
if errorlevel 1 pause & exit /b 1
pause
