@echo off
cd /d "%~dp0.."
chcp 65001 >nul
if not exist "kaynaklar\FONT_ACILMIS" (
  echo FONT_ACILMIS klasoru bulunamadi.
  pause
  exit /b 1
)
if exist "calisma/uretim\CUSTOM_FONT" rmdir /s /q "calisma/uretim\CUSTOM_FONT"
python "araclar\kirby_font_tool.py" pack-all "kaynaklar\FONT_ACILMIS" "calisma/uretim\CUSTOM_FONT"
pause
