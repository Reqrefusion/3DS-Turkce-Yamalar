@echo off
cd /d "%~dp0.."
setlocal EnableExtensions
if "%~1"=="" (
  echo Orijinal romfs.zip dosyanizi bu BAT dosyasinin uzerine surukleyin.
  pause
  exit /b 1
)
set "SRC=%~dp0..\araclar\proje"
set "OUT=%~dp0..\YENIDEN_DERLENEN_PATCH_ROMFS"
if exist "%OUT%" rmdir /S /Q "%OUT%"
py "%SRC%\naa_localizer.py" build "%~1" "%~dp0..\ceviri\translations_tr.tsv" --out "%OUT%" --images "%SRC%\images_edited" --strict-tags --v100-mode fontmap
if errorlevel 1 python "%SRC%\naa_localizer.py" build "%~1" "%~dp0..\ceviri\translations_tr.tsv" --out "%OUT%" --images "%SRC%\images_edited" --strict-tags --v100-mode fontmap
if errorlevel 1 (
  echo HATA: Derleme basarisiz.
  pause
  exit /b 1
)
echo.
echo TAMAM: %OUT%
pause
