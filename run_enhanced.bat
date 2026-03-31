@echo off
echo ============================================================
echo   🎯 AI-POWERED STUDENT ATTENTION TRACKER - ENHANCED
echo ============================================================
echo   🧠 Advanced Computer Vision Learning Analytics Platform
echo.
echo Features: Full logging + Analytics + Graphs
echo.
echo Session Types:
echo - study: Regular study session
echo - meeting: Virtual meeting
echo - training: Training/course session
echo - exam: Exam preparation
echo.
set /p session_type="Enter session type (or press Enter for 'study'): "
if "%session_type%"=="" set session_type=study

set /p notes="Enter session notes (optional): "

set /p threshold="Enter alert threshold in seconds (default 5): "
if "%threshold%"=="" set threshold=5

echo.
echo Starting Enhanced Tracker...
echo Session Type: %session_type%
echo Alert Threshold: %threshold% seconds
echo Notes: %notes%
echo.
echo Controls during tracking:
echo   'q' = Quit and generate report
echo   'r' = Generate session report
echo   'g' = Show analytics graphs
echo   's' = Take screenshot
echo.
pause

C:\Python313\python.exe enhanced_tracker.py --alert-threshold %threshold% --session-type "%session_type%" --notes "%notes%"

echo.
echo Session completed! Check 'attention_graphs' folder for analytics.
pause