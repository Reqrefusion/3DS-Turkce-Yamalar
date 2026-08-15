@echo off
cd /d "%~dp0"
if "%~1"=="" (
  echo Kullanim: Bu BAT dosyasinin ustune romfs.zip dosyasini surukleyip birakin.
  echo Ornek: 02_yamayi_olustur.bat romfs.zip
  pause
  exit /b 1
)
py naa_localizer.py build "%~1" translations_tr.tsv --out patch_romfs --images images_edited
if errorlevel 1 python naa_localizer.py build "%~1" translations_tr.tsv --out patch_romfs --images images_edited
pause
