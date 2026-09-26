@echo off
setlocal
cd /d "%~dp0"

echo [1/5] Checking Python...
where py >nul 2>nul
if %errorlevel%==0 (
  py -3.12 --version >nul 2>nul
  if %errorlevel%==0 (
    set "PYTHON=py -3.12"
  ) else (
    set "PYTHON=py"
  )
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python was not found. Install Python 3.12 from https://www.python.org/downloads/windows/ and enable Add Python to PATH.
    exit /b 1
  )
  set "PYTHON=python"
)
%PYTHON% --version
if errorlevel 1 (
  echo Could not run Python. Install Python 3.12 and try again.
  exit /b 1
)

echo [2/5] Creating virtual environment...
if not exist venv\Scripts\python.exe (
  %PYTHON% -m venv venv
  if errorlevel 1 exit /b 1
) else (
  echo Existing venv found; keeping it.
)
call venv\Scripts\activate.bat
if errorlevel 1 exit /b 1

echo [3/5] Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

echo [4/5] Installing Python dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

if not exist data\logs mkdir data\logs
if not exist ai\models mkdir ai\models
if not exist .env copy .env.example .env >nul

echo [5/5] Checking Mosquitto...
where mosquitto >nul 2>nul
if errorlevel 1 (
  echo Mosquitto was not found. Install it separately; see README.md, then run mosquitto -v.
) else (
  echo Mosquitto is available. Start it in a separate terminal with: mosquitto -v
)
echo.
echo Setup complete. Start the dashboard with:
echo   venv\Scripts\activate
echo   python backend\app.py
echo In another terminal, activate venv and run:
echo   python simulator\sensor_simulator.py
endlocal
