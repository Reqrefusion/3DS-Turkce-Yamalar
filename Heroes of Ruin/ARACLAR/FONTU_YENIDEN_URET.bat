@echo off
cd /d "%~dp0"
python hor_font_patch.py patch "..\FONT\demo_font_orijinal.bcfnt_" "..\FONT\demo_font.bcfnt_" --raw-output "..\FONT\demo_font.bcfnt"
pause
