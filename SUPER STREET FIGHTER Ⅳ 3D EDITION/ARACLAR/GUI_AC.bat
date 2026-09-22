@echo off
chcp 65001 >nul
py sf4_tr_gui.py
if errorlevel 1 pause
