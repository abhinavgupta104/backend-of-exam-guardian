# ProctorGuard Backend Startup Script
# Activate virtual environment and start Flask server

Set-Location (Split-Path -Parent $MyInvocation.MyCommand.Path)
& .\.venv\Scripts\Activate.ps1
python app.py
