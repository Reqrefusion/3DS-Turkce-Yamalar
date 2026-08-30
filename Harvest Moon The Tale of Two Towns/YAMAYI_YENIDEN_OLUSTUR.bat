@echo off
setlocal
if "%~1"=="" (
  echo Orijinal Avrupa ROM ZIP dosyasini bu BAT dosyasinin ustune surukleyin.
  pause
  exit /b 1
)
py -3 "%~dp0tools\build_final.py" "%~1" -o "%~dp0build_final"
if errorlevel 1 (
  echo.
  echo OLUSTURMA BASARISIZ.
  pause
  exit /b 1
)
echo.
echo Yama basariyla yeniden olusturuldu: build_final\luma
pause
