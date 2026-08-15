@echo off
cd /d "%~dp0"
if "%~1"=="" (
  echo Kullanim: Bu BAT dosyasinin ustune romfs.zip dosyasini surukleyip birakin.
  pause
  exit /b 1
)
py font_tool.py analyze "%~1" --out TURKISH_FONT_REPORT.txt
if errorlevel 1 python font_tool.py analyze "%~1" --out TURKISH_FONT_REPORT.txt
if exist TURKISH_FONT_REPORT.txt type TURKISH_FONT_REPORT.txt
pause
