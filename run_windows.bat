@echo off
if not exist .env (
  echo .env topilmadi. Avval setup_windows.bat ni ishga tushiring.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python main.py
pause
