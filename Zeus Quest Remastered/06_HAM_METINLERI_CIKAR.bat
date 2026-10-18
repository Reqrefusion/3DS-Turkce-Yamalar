@echo off
chcp 65001 >nul
cd /d "%~dp0"
python araclar\zeusquest_tool.py extract --game "Zeus Quest Remastered.zip" --out "kaynak_cikti"
pause
