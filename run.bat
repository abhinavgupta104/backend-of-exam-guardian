@echo off
REM Activate virtual environment and run the ProctorGuard backend
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python app.py
pause
