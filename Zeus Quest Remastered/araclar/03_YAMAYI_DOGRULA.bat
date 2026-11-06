@echo off
cd /d "%~dp0.."
chcp 65001 >nul
python araclar\tek_dil_dogrula.py --game "Zeus Quest Remastered.zip" --patch "hazir_yama\ZeusQuest_ASAMA34_EN_TR_Font_LayeredFS.zip" --en "ceviri\EN_TR.csv" --ui "ceviri\UI_EN_TR.csv" --report "raporlar\YAMA_DOGRULAMA.json"
pause
