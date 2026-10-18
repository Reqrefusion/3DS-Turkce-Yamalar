@echo off
chcp 65001 >nul
cd /d "%~dp0"
python araclar\zeusquest_tool.py font-check --game "Zeus Quest Remastered.zip" --csv "ceviriler\EN_TR.csv" "ceviriler\UI_EN_TR.csv"
pause
