@echo off
echo ==========================================
echo Starting PoolGuard Backend Server
echo ==========================================

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found or activation script is missing!
    echo Please make sure you have created the python virtual environment in .venv
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Starting Uvicorn Server...
cd backend
python main.py
pause
