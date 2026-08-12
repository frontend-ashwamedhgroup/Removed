@echo off
cd /d "%~dp0"
if not exist venv\Scripts\activate.bat (
    echo Virtual environment not found. Run setup_windows.bat first.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
python manage.py check_admin
if errorlevel 1 (
    echo.
    echo The server will not start until a main administrator exists.
    echo Run create_admin_windows.bat or: python manage.py createsuperuser
    pause
    exit /b 1
)
python manage.py check_model
if errorlevel 1 (
    echo.
    echo Model check failed.
echo If this is the 161-class label error, run install_updated_model_labels_windows.bat.
echo Otherwise run repair_environment.bat.
    pause
    exit /b 1
)
python manage.py runserver
pause
