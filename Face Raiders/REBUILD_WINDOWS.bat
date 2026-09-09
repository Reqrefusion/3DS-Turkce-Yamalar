@echo off
setlocal
set /p DUMP=Decrypted Face Raiders CXI veya ZIP yolunu girin: 
python 02_TOOLS\build_working_universal.py "%DUMP%" 01_TRANSLATION\StgFace_all_languages_TR.csv BUILD_OUT
if errorlevel 1 pause & exit /b 1
python 02_TOOLS\verify_prebuilt.py 01_TRANSLATION\StgFace_all_languages_TR.csv BUILD_OUT
pause
