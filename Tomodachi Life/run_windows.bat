@echo off
cd /d "%~dp0"
py -3 tomodachi_tr_tool.py
if errorlevel 1 python tomodachi_tr_tool.py
pause
