@echo off
chcp 65001 >nul
cd /d "%~dp0"
python araclar\tek_dil_dogrula.py --game "Zeus Quest Remastered.zip" --patch "hazir_yama\ZeusQuest_ASAMA34_EN_TR_Font_LayeredFS.zip" --en "ceviriler\EN_TR.csv" --ui "ceviriler\UI_EN_TR.csv" --report "raporlar\YAMA_DOGRULAMA.json"
pause
