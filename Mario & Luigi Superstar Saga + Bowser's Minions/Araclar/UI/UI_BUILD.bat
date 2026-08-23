@echo off
chcp 65001 >nul
setlocal EnableExtensions
if "%~1"=="" goto USAGE
if "%~2"=="" goto USAGE
set "BASE=%~dp0"
python -c "import numpy, PIL" >nul 2>nul
if errorlevel 1 (
  echo Gerekli Python paketleri eksik.
  echo Bu klasorde: pip install -r requirements_ui.txt
  exit /b 2
)
python "%BASE%mlss_ui_tool.py" "%~1" "%BASE%ui_translations.csv" "%~2" --preview "%~2\_onizleme"
exit /b %ERRORLEVEL%
:USAGE
echo Kullanim: UI_BUILD.bat "kaynak Obj\EU" "cikti Obj\EU"
exit /b 1
