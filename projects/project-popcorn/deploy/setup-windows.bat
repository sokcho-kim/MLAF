@echo off
REM Cross-Domain Radar - Windows Setup Script
REM Usage: deploy\setup-windows.bat

echo ========================================
echo Cross-Domain Radar Windows Setup
echo ========================================

REM Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python is not installed
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

python --version

REM Create virtual environment
echo [1/6] Creating virtual environment...
if not exist .venv (
    python -m venv .venv
    echo   Created .venv
) else (
    echo   .venv already exists
)

REM Activate venv
call .venv\Scripts\activate.bat

REM Install dependencies
echo [2/6] Installing dependencies...
pip install --upgrade pip
pip install -r requirements-prod.txt

REM Create directories
echo [3/6] Creating directories...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist output mkdir output

REM Check .env file
echo [4/6] Checking environment file...
if not exist .env (
    if exist .env.example (
        copy .env.example .env
        echo   Created .env from .env.example
        echo   WARNING: Please edit .env and add your API keys!
    )
) else (
    echo   .env file exists
)

REM Check data files
echo [5/6] Checking data files...
if not exist data\bills_master.json (
    if not exist data\bills_merged.json (
        echo   WARNING: No bill data found!
        echo   Copy bills_master.json or bills_merged.json to data folder
    )
)

REM Test run
echo [6/6] Testing...
python run_daily.py --test

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Edit .env with your API keys
echo   2. Copy bill data to data folder
echo   3. Run manually: python run_daily.py
echo   4. Setup Task Scheduler (see docs/OPERATIONS.md)
echo.
pause
