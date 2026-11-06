@echo off
setlocal
if "%~3"=="" (
  echo Kullanim: REBUILD_FINAL.bat 3DS_ORIGINAL_loctext_eng.pak STEAM_TR_loctext_eng.pak OUTPUT.pak
  pause
  exit /b 1
)
python "%~dp0shovel_knight_3ds_v41_tr_tool.py" convert-steam "%~1" "%~2" "%~3" --report "%~dp3verification_report.json"
pause
