@echo off
cd /d "%~dp0.."
py -3 araclar/braintrain_tool.py 2>nul || python araclar/braintrain_tool.py
