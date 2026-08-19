@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "04_ARA_DOSYALAR\FONT_ACILMIS_YENI" rmdir /s /q "04_ARA_DOSYALAR\FONT_ACILMIS_YENI"
python "03_ARACLAR\kirby_font_tool.py" unpack-all "01_HAZIR_YAMA\ROMFS_ONLY\romfs\font" "04_ARA_DOSYALAR\FONT_ACILMIS_YENI"
pause
