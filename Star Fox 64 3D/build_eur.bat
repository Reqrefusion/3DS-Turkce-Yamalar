@echo off
if not exist Resources.zip (echo Resources.zip bulunamadi.& pause & exit /b 1)
python scripts\build_luma_patch.py Resources.zip --region EUR
pause
