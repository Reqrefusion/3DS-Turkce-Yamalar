@echo off
cd /d "%~dp0"
python hor_tool.py language-build "..\ceviri\translation_multilang" built_TR --input-format json
pause
