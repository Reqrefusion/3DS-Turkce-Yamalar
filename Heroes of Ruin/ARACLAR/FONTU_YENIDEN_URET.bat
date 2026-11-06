@echo off
cd /d "%~dp0"
python hor_font_patch.py patch "..\varliklar/fontlar\demo_font_orijinal.bcfnt_" "..\varliklar/fontlar\demo_font.bcfnt_" --raw-output "..\varliklar/fontlar\demo_font.bcfnt"
pause
