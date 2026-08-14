@echo off
if "%~1"=="" (
  echo SD kart kok yolunu parametre olarak ver. Ornek: INSTALL_LUMA_EUR_ORIGINAL.bat E:\
  pause
  exit /b 2
)
set "DEST=%~1\luma\titles\0004000000086400\romfs"
echo Kopyalaniyor: PATCH\romfs --^> %DEST%
xcopy /E /I /Y "%~dp0PATCH\romfs\*" "%DEST%\"
echo Bitti. Luma3DS'te Enable game patching acik olmali.
pause
