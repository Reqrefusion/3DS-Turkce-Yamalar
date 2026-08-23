@echo off
setlocal
if "%~2"=="" (
 echo Kullanim: YAMA_URET.bat temiz_lt5_a.fa temiz_lt5_uk.fa
 pause
 exit /b 2
)
set ROOT=%~dp0
copy /Y "%ROOT%hazir\romfs\lt5\arc\lt5_a.fa" "%~dp1lt5_a_TR.fa" >nul
py -3 "%ROOT%araclar\layton_xfsa_text_tool.py" "%~2" "%ROOT%ceviri\layton_tr.jsonl" "%~dp2lt5_uk_TR.fa" --report "%~dp2lt5_uk_TR_rapor.json"
if errorlevel 1 exit /b 1
echo Hazir: %~dp1lt5_a_TR.fa
echo Hazir: %~dp2lt5_uk_TR.fa
pause
