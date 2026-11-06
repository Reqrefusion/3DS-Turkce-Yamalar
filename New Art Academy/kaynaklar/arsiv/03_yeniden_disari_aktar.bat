@echo off
cd /d "%~dp0"
if "%~1"=="" (
  echo Kullanim: Bu BAT dosyasinin ustune romfs.zip dosyasini surukleyip birakin.
  pause
  exit /b 1
)
copy /y translations_tr.tsv translations_tr.backup.tsv >nul 2>nul
py naa_localizer.py extract "%~1" --tsv translations_tr.YENI.tsv
if errorlevel 1 python naa_localizer.py extract "%~1" --tsv translations_tr.YENI.tsv
pause
