@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo CropCare AI - First Time Setup
echo ================================================

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found.
    echo Install 64-bit Python 3.11 and select "Add Python to PATH".
    pause
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
    echo.
    echo This model was saved with Keras 3.15 and requires Python 3.11 or newer.
    echo Install 64-bit Python 3.11, then run this file again.
    python --version
    pause
    exit /b 1
)

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 goto :error
)

call venv\Scripts\activate.bat
if errorlevel 1 goto :error

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
    echo The existing venv uses an older Python version.
    echo Run repair_environment.bat to recreate it safely.
    pause
    exit /b 1
)

python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :error

python -m pip install --upgrade --upgrade-strategy eager -r requirements.txt
if errorlevel 1 goto :error

python manage.py migrate
if errorlevel 1 goto :error

python manage.py seed_treatment_guides
if errorlevel 1 goto :error

python manage.py check_model --archive-only
if errorlevel 1 goto :model_error

python manage.py check_admin
if errorlevel 1 (
    echo.
    echo A main administrator is mandatory.
    echo Create the administrator username and password now.
    python manage.py createsuperuser
    if errorlevel 1 goto :error
    python manage.py check_admin
    if errorlevel 1 goto :error
)

echo.
echo Setup completed successfully.
echo The administrator can sign in and register farmer accounts.
echo Next: run install_updated_model_labels_windows.bat
echo Then start the app with: run_windows.bat
pause
exit /b 0

:model_error
echo.
echo The website packages installed, but the model test failed.
echo Run repair_environment.bat and read the error shown above.
pause
exit /b 1

:error
echo.
echo Setup stopped because a command failed. Read the error shown above.
pause
exit /b 1
