@echo off
cd /d "%~dp0"
set /p ROMFS=Acik RomFS klasoru: 
python hor_tool.py multilang-extract "%ROMFS%" translation_multilang --csv
pause
