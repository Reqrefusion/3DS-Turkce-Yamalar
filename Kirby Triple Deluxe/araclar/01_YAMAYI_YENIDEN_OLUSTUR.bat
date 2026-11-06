@echo off
cd /d "%~dp0.."
chcp 65001 >nul
python "araclar\build_patch.py"
if errorlevel 1 (
  pause
  exit /b 1
)
pause
