@echo off
setlocal
cd /d "%~dp0"

if not exist venv\Scripts\activate.bat (
    echo Virtual environment not found. Run setup_windows.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python manage.py createsuperuser
if errorlevel 1 (
    echo.
    echo Administrator creation was not completed.
    pause
    exit /b 1
)
python manage.py check_admin
pause
