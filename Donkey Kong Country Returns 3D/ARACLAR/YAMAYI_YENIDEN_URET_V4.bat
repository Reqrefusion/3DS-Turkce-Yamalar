@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "euenglish_original.res" (
  echo Temiz EUR euenglish.res dosyasini bu klasore euenglish_original.res adiyla koyun.
  pause
  exit /b 1
)
if exist "_work_v4" rmdir /s /q "_work_v4"
python dkcr3d_tool_v4_safe.py make-workspace euenglish_original.res _work_v4
if errorlevel 1 goto fail
copy /y "FONT_METRIC_FIX\uifnt_o.fnt" "_work_v4\resources\uifnt_o.fnt" >nul
copy /y "FONT_METRIC_FIX\ouifnt_o.fnt" "_work_v4\resources\ouifnt_o.fnt" >nul
python dkcr3d_tool_v4_safe.py build _work_v4 translation_turkish_ready.csv euenglish_turkish_v4_safe.res --compression lz
if errorlevel 1 goto fail
echo.
echo BASARILI: euenglish_turkish_v4_safe.res
pause
exit /b 0
:fail
echo HATA.
pause
exit /b 1
