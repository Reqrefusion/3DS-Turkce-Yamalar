@echo off
cd /d "%~dp0.."
setlocal
set /p DUMP=Decrypted Face Raiders CXI veya ZIP yolunu girin: 
python araclar\build_working_universal.py "%DUMP%" ceviri\StgFace_all_languages_TR.csv BUILD_OUT
if errorlevel 1 (
  pause
  exit /b 1
)
python araclar\verify_prebuilt.py ceviri\StgFace_all_languages_TR.csv BUILD_OUT
pause
