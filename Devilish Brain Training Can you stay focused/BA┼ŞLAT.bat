@echo off
cd /d "%~dp0"
py -3 braintrain_tool.py 2>nul || python braintrain_tool.py
