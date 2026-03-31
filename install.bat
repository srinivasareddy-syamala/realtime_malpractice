@echo off
echo ============================================================
echo   🎯 AI-POWERED STUDENT ATTENTION TRACKER - INSTALLER
echo ============================================================
echo   🚀 Smart Learning Focus Monitor Setup & Configuration
echo.
echo This will install all required packages...
echo.
pause

echo Installing core packages...
C:\Python313\python.exe -m pip install opencv-python "numpy<2.0" pygame pandas matplotlib seaborn scipy

echo.
echo Checking for optional packages...
echo Trying to install mediapipe (may fail on Python 3.13)...
C:\Python313\python.exe -m pip install mediapipe 2>nul
if %errorlevel% neq 0 (
    echo MediaPipe installation failed - this is okay, system will work without it
)

echo.
echo Trying to install dlib (may fail without Visual Studio)...
C:\Python313\python.exe -m pip install dlib 2>nul
if %errorlevel% neq 0 (
    echo Dlib installation failed - this is okay, system will work without it
)

echo.
echo Installing Student Attention Tracker...
python -m pip install --upgrade pip
pip install -r requirements.txt
mkdir static 2>nul
mkdir static\captured_images 2>nul
mkdir templates 2>nul
echo Installation complete!

echo.
echo You can now run:
echo - run_simple.bat (for basic tracking)
echo - run_enhanced.bat (for full tracking with analytics)
echo - generate_graphs.bat (to create analytics graphs)
echo.
pause