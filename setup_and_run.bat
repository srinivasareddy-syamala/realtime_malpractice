@echo off
REM Real Time Exam Malpractice Detection - Complete Setup Script
REM This script installs dependencies and starts the application

setlocal enabledelayedexpansion

echo.
echo ============================================
echo Real Time Exam Malpractice Detection
echo Complete Setup & Run Script
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [OK] Python detected:
python --version
echo.

REM Check if pip is available
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not available
    pause
    exit /b 1
)

echo [OK] pip detected
echo.

REM Check if requirements are already installed
python -c "import flask, cv2, numpy" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Installing required packages...
    echo This may take a few minutes on first run...
    echo.
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install -r requirements.txt
    
    if errorlevel 1 (
        echo.
        echo ERROR: Installation failed!
        pause
        exit /b 1
    )
    echo [OK] All packages installed successfully!
) else (
    echo [OK] All required packages are already installed
)

echo.
echo ============================================
echo Starting Flask Application...
echo ============================================
echo.
echo Server URL: http://localhost:5000
echo Press CTRL+C to stop the server
echo.

REM Create captured_images directory if it doesn't exist
if not exist "static\captured_images" (
    mkdir static\captured_images
    echo [OK] Created captured_images directory
)

echo.

REM Run the Flask app
python -u app.py

endlocal
