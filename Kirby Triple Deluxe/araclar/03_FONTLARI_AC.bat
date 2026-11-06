@echo off
cd /d "%~dp0.."
chcp 65001 >nul
if exist "kaynaklar\FONT_ACILMIS_YENI" rmdir /s /q "kaynaklar\FONT_ACILMIS_YENI"
python "araclar\kirby_font_tool.py" unpack-all "000400000010C000\romfs\font" "kaynaklar\FONT_ACILMIS_YENI"
pause
