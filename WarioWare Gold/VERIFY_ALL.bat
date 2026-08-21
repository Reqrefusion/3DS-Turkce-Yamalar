@echo off
cd /d "%~dp0"
py -3 tools\verify_package.py .
if errorlevel 1 (
  echo.
  echo VERIFY FAILED.
  pause
  exit /b 1
)
echo.
echo ALL TECHNICAL CHECKS PASSED.
pause
