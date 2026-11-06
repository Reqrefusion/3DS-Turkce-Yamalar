@echo off
cd /d "%~dp0.."
chcp 65001 >nul
python araclar\zeusquest_tool.py extract --game "Zeus Quest Remastered.zip" --out "kaynak_cikti"
pause
