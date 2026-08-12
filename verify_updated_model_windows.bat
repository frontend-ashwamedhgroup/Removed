@echo off
call venv\Scripts\activate.bat
python manage.py check_model --archive-only
pause
