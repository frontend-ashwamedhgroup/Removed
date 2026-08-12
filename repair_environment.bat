@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo CropCare AI - Repair Python Environment
echo ================================================
echo This removes only the venv folder.
echo Your SQLite database, uploaded media and project code are not deleted.
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Install 64-bit Python 3.11 and select "Add Python to PATH".
    pause
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
    echo Python 3.11 or newer is required.
    python --version
    pause
    exit /b 1
)

if exist venv (
    echo Removing the incompatible virtual environment...
    rmdir /s /q venv
)

python -m venv venv
if errorlevel 1 goto :error
call venv\Scripts\activate.bat
if errorlevel 1 goto :error

python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :error
python -m pip install --upgrade --upgrade-strategy eager -r requirements.txt
if errorlevel 1 goto :error

python manage.py migrate
if errorlevel 1 goto :error
python manage.py seed_treatment_guides
if errorlevel 1 goto :error
python manage.py check_model --archive-only
if errorlevel 1 goto :error

python manage.py check_admin
if errorlevel 1 (
    echo.
    echo A main administrator is mandatory.
    python manage.py createsuperuser
    if errorlevel 1 goto :error
    python manage.py check_admin
    if errorlevel 1 goto :error
)

echo.
echo Repair completed.
echo If labels are not installed yet, run install_updated_model_labels_windows.bat.
echo Then start the project with run_windows.bat.
pause
exit /b 0

:error
echo.
echo Repair failed. Read the command error shown above.
pause
exit /b 1
