@echo off
cd /d "%~dp0"
python hor_tool.py language-build "..\CEVIRI\translation_multilang" built_TR --input-format csv
pause
