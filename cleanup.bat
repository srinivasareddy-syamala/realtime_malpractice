@echo off
echo Cleaning up project files...

:: Remove Python cache files
del /s /q *.pyc
rmdir /s /q __pycache__

:: Remove temporary files
del /s /q *.tmp
del /s /q *.log

:: Keep only necessary directories
if not exist static mkdir static
if not exist static\captured_images mkdir static\captured_images
if not exist templates mkdir templates

echo Cleanup complete!
pause
