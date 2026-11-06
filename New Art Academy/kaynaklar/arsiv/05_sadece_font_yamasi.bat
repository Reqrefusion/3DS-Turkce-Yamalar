@echo off
cd /d "%~dp0"
if "%~1"=="" (
  echo Kullanim: Bu BAT dosyasinin ustune romfs.zip dosyasini surukleyip birakin.
  pause
  exit /b 1
)
py font_tool.py patch "%~1" --out font_patch_romfs
if errorlevel 1 python font_tool.py patch "%~1" --out font_patch_romfs
pause
