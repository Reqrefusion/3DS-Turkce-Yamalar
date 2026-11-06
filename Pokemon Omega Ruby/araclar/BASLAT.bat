@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 ORAS_TR_Text_Tool.py gui
) else (
    python ORAS_TR_Text_Tool.py gui
)
if errorlevel 1 pause
