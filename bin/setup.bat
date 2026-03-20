@echo off
echo Setting up project...

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed! Please install Python 3.11+
    pause
    exit /b
)

:: Create venv if not exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate
call venv\Scripts\activate

:: Upgrade pip (important)
python -m pip install --upgrade pip

:: Install deps
pip install -r requirements.txt

:: Run app
echo Starting app...
python main.py

pause