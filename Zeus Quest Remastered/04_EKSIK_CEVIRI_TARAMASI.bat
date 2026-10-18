@echo off
chcp 65001 >nul
cd /d "%~dp0"
python araclar\ingilizce_denetime_al.py --en "ceviriler\EN_TR.csv" --ui "ceviriler\UI_EN_TR.csv" --out "raporlar"
pause
