@echo off
cd /d "%~dp0.."
chcp 65001 >nul
if exist "calisma/uretim\FONT_TR_V12" rmdir /s /q "calisma/uretim\FONT_TR_V12"
if exist "calisma/uretim\FONT_TR_V12_ONIZLEME" rmdir /s /q "calisma/uretim\FONT_TR_V12_ONIZLEME"
python "araclar\kirby_font_tr_patch.py" patch-all "kaynaklar\FONT_ORIJINAL" "calisma/uretim\FONT_TR_V12" --used-chars-file "araclar\used_chars_all_messages.txt" --report "calisma/uretim\FONT_TR_V12_RAPOR.csv" --previews "calisma/uretim\FONT_TR_V12_ONIZLEME"
echo.
echo v12 fontlari calisma/uretim\FONT_TR_V12 altinda olusturuldu.
pause
