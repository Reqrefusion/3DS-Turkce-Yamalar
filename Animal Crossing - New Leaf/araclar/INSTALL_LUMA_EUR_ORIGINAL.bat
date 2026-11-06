@echo off
cd /d "%~dp0.."
if "%~1"=="" (
  echo SD kart kok yolunu parametre olarak ver. Ornek: araclar/INSTALL_LUMA_EUR_ORIGINAL.bat E:\
  pause
  exit /b 2
)
set "DEST=%~1\luma\titles\0004000000086400\romfs"
echo Kopyalaniyor: 0004000000086400\romfs --^> %DEST%
xcopy /E /I /Y "%~dp0..\0004000000086400\romfs\*" "%DEST%\"
echo Bitti. Luma3DS'te Enable game patching acik olmali.
pause
