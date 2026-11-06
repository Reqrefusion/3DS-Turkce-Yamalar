@echo off
cd /d "%~dp0"
py translator_gui.py ..\..\ceviri\translations_tr.tsv
if errorlevel 1 python translator_gui.py ..\..\ceviri\translations_tr.tsv
pause
