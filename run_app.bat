@echo off
REM Real Time Exam Malpractice Detection - Run Application Script
REM This script starts the Flask application

echo.
echo ============================================
echo Real Time Exam Malpractice Detection
echo Application Launcher
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please run install_dependencies.bat first
    pause
    exit /b 1
)

echo Starting Flask application...
echo.
echo ============================================
echo Server Information:
echo ============================================
echo URL: http://localhost:5000
echo Debug Mode: Enabled
echo.
echo Press CTRL+C to stop the server
echo ============================================
echo.

REM Run the Flask app
python -u app.py

if errorlevel 1 (
    echo.
    echo ERROR: Application failed to start!
    echo Make sure all dependencies are installed
    echo Run: install_dependencies.bat
    pause
    exit /b 1
)

pause
