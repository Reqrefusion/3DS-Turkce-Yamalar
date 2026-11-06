@echo off
cd /d "%~dp0.."
chcp 65001 >nul
python araclar\ingilizce_denetime_al.py --en "ceviri\EN_TR.csv" --ui "ceviri\UI_EN_TR.csv" --out "raporlar"
pause
