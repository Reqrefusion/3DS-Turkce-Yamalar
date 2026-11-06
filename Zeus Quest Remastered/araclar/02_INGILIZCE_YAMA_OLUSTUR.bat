@echo off
cd /d "%~dp0.."
chcp 65001 >nul
python araclar\zeusquest_tool.py build --game "Zeus Quest Remastered.zip" --csv "ceviri\EN_TR.csv" --slot en --ui-csv "ceviri\UI_EN_TR.csv" --out "ZeusQuest_ASAMA34_EN_TR_Font_LayeredFS.zip"
if errorlevel 1 goto problem
python araclar\tek_dil_dogrula.py --game "Zeus Quest Remastered.zip" --patch "ZeusQuest_ASAMA34_EN_TR_Font_LayeredFS.zip" --en "ceviri\EN_TR.csv" --ui "ceviri\UI_EN_TR.csv" --report "raporlar\YAMA_DOGRULAMA.json"
:problem
pause
