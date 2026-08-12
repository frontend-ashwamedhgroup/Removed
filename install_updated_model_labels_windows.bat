@echo off
setlocal
cd /d "%~dp0"

if not exist venv\Scripts\activate.bat (
    echo Virtual environment not found. Run setup_windows.bat first.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

python manage.py check_model --archive-only
if errorlevel 1 goto :error

echo.
echo The updated model has 161 output classes.
echo You MUST install the matching class-name order from the same training run.
echo.
echo Enter either:
echo   1. Full path to the class_names.json generated with this model, OR
echo   2. Full path to the exact dataset folder used for this training run.
echo.
set /p SOURCE=Path: 

if "%SOURCE%"=="" goto :error

if exist "%SOURCE%\*" (
    python manage.py install_model_labels --dataset "%SOURCE%"
) else (
    python manage.py install_model_labels --json "%SOURCE%"
)
if errorlevel 1 goto :error

python manage.py check_model
if errorlevel 1 goto :error

echo.
echo Label installation and model validation completed successfully.
pause
exit /b 0

:error
echo.
echo The label installation was not completed. Read the message above.
pause
exit /b 1
