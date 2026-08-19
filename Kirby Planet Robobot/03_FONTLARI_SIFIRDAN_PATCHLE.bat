@echo off
cd /d "%~dp0"
py -3 04_ARACLAR\kirby_font_tr_patch.py patch-all 03_FONTLAR\ORIJINAL_CMP 03_FONTLAR\TR_PATCHED_CMP --used-chars-file 04_ARACLAR\used_chars_all_messages.txt --report 05_RAPORLAR\FONT_PATCH_RAPORU.csv --previews 06_FONT_ONIZLEMELERI
if errorlevel 1 python 04_ARACLAR\kirby_font_tr_patch.py patch-all 03_FONTLAR\ORIJINAL_CMP 03_FONTLAR\TR_PATCHED_CMP --used-chars-file 04_ARACLAR\used_chars_all_messages.txt --report 05_RAPORLAR\FONT_PATCH_RAPORU.csv --previews 06_FONT_ONIZLEMELERI
pause
