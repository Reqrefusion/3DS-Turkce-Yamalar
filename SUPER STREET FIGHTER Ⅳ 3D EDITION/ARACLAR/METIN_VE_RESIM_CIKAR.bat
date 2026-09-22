@echo off
chcp 65001 >nul
set /p SOURCE=Kaynak klasor veya archive.zip yolu: 
if "%SOURCE%"=="" exit /b 1
py sf4_tr_tool.py extract-all "%SOURCE%" workspace
pause
