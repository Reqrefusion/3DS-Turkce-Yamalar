@echo off
cd /d "%~dp0.."
setlocal
if "%~1"=="" (
  echo Orijinal Avrupa ROM ZIP dosyasini bu BAT dosyasinin ustune surukleyin.
  pause
  exit /b 1
)
py -3 "%~dp0..\araclar\build_final.py" "%~1" -o "%~dp0..\build_final"
if errorlevel 1 (
  echo.
  echo OLUSTURMA BASARISIZ.
  pause
  exit /b 1
)
echo.
echo Yama basariyla yeniden olusturuldu: build_final\luma
pause
