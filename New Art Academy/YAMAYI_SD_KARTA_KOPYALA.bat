@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if "%~1"=="" (
  echo Kullanim:
  echo   SD kartinizin KOK klasorunu bu BAT dosyasinin uzerine surukleyin.
  echo Ornek: YAMAYI_SD_KARTA_KOPYALA.bat E:\
  pause
  exit /b 1
)
set "SD=%~1"
if not exist "%SD%\" (
  echo HATA: Hedef klasor bulunamadi: %SD%
  pause
  exit /b 1
)
if not exist "%~dp001_LUMA3DS_HAZIR\luma\titles\0004000000084F00\romfs" (
  echo HATA: Hazir yama klasoru bulunamadi.
  pause
  exit /b 1
)
echo.
echo Yama kopyalaniyor:
echo   %SD%\luma\titles\0004000000084F00\romfs
xcopy "%~dp001_LUMA3DS_HAZIR\luma\*" "%SD%\luma\" /E /I /Y /H
if errorlevel 1 (
  echo.
  echo HATA: Kopyalama tamamlanamadi.
  pause
  exit /b 1
)
echo.
echo TAMAM. Luma3DS ayarlarinda Enable game patching acik olmali.
echo Oyun Ingilizce dil dosyalarini yuklemelidir.
pause
