@echo off
REM 🧪 SAQ EVALUATION TEST RUNNER - Windows Batch Script
REM ======================================================
REM
REM This script properly initializes the virtual environment and runs tests.
REM Usage: test_runner.bat [checkpoint_name]
REM
REM Examples:
REM   test_runner.bat                    (run all checkpoints)
REM   test_runner.bat phase_1_models     (run specific checkpoint)

echo 🧪 SAQ Evaluation Test Runner
echo ============================

REM Change to the sensai-ai directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Virtual environment not found at venv\Scripts\activate.bat
    echo Please create the virtual environment first:
    echo    python -m venv venv
    echo    venv\Scripts\activate
    echo    pip install -r requirements.txt
    pause
    exit /b 1
)

echo ✅ Found virtual environment
echo 🔧 Activating virtual environment...

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if activation was successful
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

echo ✅ Virtual environment activated
echo 📦 Installing/updating test dependencies...

REM Install test dependencies
pip install pytest pytest-asyncio pytest-json-report requests psutil

REM Check if dependencies were installed
if errorlevel 1 (
    echo ❌ Failed to install test dependencies
    pause
    exit /b 1
)

echo ✅ Test dependencies ready
echo 🧪 Running tests...

REM Run the checkpoint tests
if "%1"=="" (
    python run_checkpoint_tests.py
) else (
    python run_checkpoint_tests.py %1
)

REM Check test results
if errorlevel 1 (
    echo.
    echo ❌ Tests failed! Check the logs in tests/logs/ directory
    echo 📁 Test reports saved in tests/reports/ directory
) else (
    echo.
    echo ✅ All tests passed!
    echo 📁 Test reports saved in tests/reports/ directory
)

echo.
echo 🏁 Test run complete
pause
