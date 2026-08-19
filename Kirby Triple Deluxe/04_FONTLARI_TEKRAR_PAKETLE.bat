@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "04_ARA_DOSYALAR\FONT_ACILMIS" (
  echo FONT_ACILMIS klasoru bulunamadi.
  pause
  exit /b 1
)
if exist "BUILD_OUTPUT\CUSTOM_FONT" rmdir /s /q "BUILD_OUTPUT\CUSTOM_FONT"
python "03_ARACLAR\kirby_font_tool.py" pack-all "04_ARA_DOSYALAR\FONT_ACILMIS" "BUILD_OUTPUT\CUSTOM_FONT"
pause
