@echo off
cd /d "%~dp0.."
chcp 65001 >nul
python araclar\zeusquest_tool.py font-check --game "Zeus Quest Remastered.zip" --csv "ceviri\EN_TR.csv" "ceviri\UI_EN_TR.csv"
pause
