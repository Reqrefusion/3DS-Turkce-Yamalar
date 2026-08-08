@echo off
setlocal
if "%~1"=="" (
  echo Temiz lt5_uk.fa dosyasini bu BAT dosyasinin uzerine surukleyin.
  pause
  exit /b 2
)
set "PAKET=%~dp0"
set "CIKTI=%~dpn1_tr.fa"
set "RAPOR=%~dpn1_tr_raporu.json"
py -3 "%PAKET%arac\layton5_tool.py" fa-replace "%~1" "%PAKET%hazir_xs" "%CIKTI%" --report "%RAPOR%"
if errorlevel 1 (
  echo Islem basarisiz. Yukaridaki hata mesajini kontrol edin.
  pause
  exit /b 1
)
echo Hazir: %CIKTI%
echo Rapor: %RAPOR%
pause
