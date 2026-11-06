@echo off
if "%~4"=="" (
  echo Kullanim: 02_BUILD_PATCH.bat ^<Script_klasoru^> ^<Translations_klasoru^> ^<Font_klasoru^> ^<Cikti_klasoru^>
  pause
  exit /b 2
)
python build_patch.py --script "%~1" --translations "%~2" --font "%~3" --out "%~4" --target EN
pause
