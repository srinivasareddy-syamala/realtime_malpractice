@echo off
REM Real Time Exam Malpractice Detection - Installation Script
REM This script installs all required Python dependencies

echo.
echo ============================================
echo Real Time Exam Malpractice Detection
echo Installation Script
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

echo [1/3] Python installation detected
python --version
echo.

REM Check if pip is available
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not available
    echo Please ensure pip is installed with Python
    pause
    exit /b 1
)

echo [2/3] pip is available
python -m pip --version
echo.

echo [3/3] Installing required packages from requirements.txt...
echo.
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed!
    echo Please check the error messages above
    pause
    exit /b 1
)

echo.
echo ============================================
echo Installation completed successfully!
echo ============================================
echo.
echo You can now run the application using:
echo   - Double-click: run_app.bat
echo   - Or manually: python app.py
echo.
pause
