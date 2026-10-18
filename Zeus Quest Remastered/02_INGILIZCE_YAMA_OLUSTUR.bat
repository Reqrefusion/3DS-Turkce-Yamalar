@echo off
chcp 65001 >nul
cd /d "%~dp0"
python araclar\zeusquest_tool.py build --game "Zeus Quest Remastered.zip" --csv "ceviriler\EN_TR.csv" --slot en --ui-csv "ceviriler\UI_EN_TR.csv" --out "ZeusQuest_ASAMA34_EN_TR_Font_LayeredFS.zip"
if errorlevel 1 goto problem
python araclar\tek_dil_dogrula.py --game "Zeus Quest Remastered.zip" --patch "ZeusQuest_ASAMA34_EN_TR_Font_LayeredFS.zip" --en "ceviriler\EN_TR.csv" --ui "ceviriler\UI_EN_TR.csv" --report "raporlar\YAMA_DOGRULAMA.json"
:problem
pause
