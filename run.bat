@echo off
cd /d "%~dp0voice_dispatch"
set PYTHONPATH=%~dp0deps
python main.py
pause
