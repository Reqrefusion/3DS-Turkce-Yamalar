@echo off
cd /d "%~dp0.."
py -3 araclar/tomodachi_tr_tool.py
if errorlevel 1 python araclar/tomodachi_tr_tool.py
pause
