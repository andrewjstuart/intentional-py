@echo off
REM Double-click to build and open the web version. Equivalent to: python web\serve.py
cd /d "%~dp0"
python serve.py
if errorlevel 1 (
    echo.
    echo Something went wrong ^(see above^).
    pause
)
