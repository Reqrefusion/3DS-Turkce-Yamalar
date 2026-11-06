@echo off
cd /d "%~dp0.."
if not exist Resources.zip (echo Resources.zip bulunamadi.& pause & exit /b 1)
python araclar\build_luma_patch.py Resources.zip --region EUR
pause
