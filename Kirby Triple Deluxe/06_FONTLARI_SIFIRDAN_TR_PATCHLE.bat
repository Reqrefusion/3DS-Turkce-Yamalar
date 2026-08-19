@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "BUILD_OUTPUT\FONT_TR_V12" rmdir /s /q "BUILD_OUTPUT\FONT_TR_V12"
if exist "BUILD_OUTPUT\FONT_TR_V12_ONIZLEME" rmdir /s /q "BUILD_OUTPUT\FONT_TR_V12_ONIZLEME"
python "03_ARACLAR\kirby_font_tr_patch.py" patch-all "04_ARA_DOSYALAR\FONT_ORIJINAL" "BUILD_OUTPUT\FONT_TR_V12" --used-chars-file "03_ARACLAR\used_chars_all_messages.txt" --report "BUILD_OUTPUT\FONT_TR_V12_RAPOR.csv" --previews "BUILD_OUTPUT\FONT_TR_V12_ONIZLEME"
echo.
echo v12 fontlari BUILD_OUTPUT\FONT_TR_V12 altinda olusturuldu.
pause
