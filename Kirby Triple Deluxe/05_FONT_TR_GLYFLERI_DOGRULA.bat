@echo off
chcp 65001 >nul
cd /d "%~dp0"
python "03_ARACLAR\verify_package.py"
pause
