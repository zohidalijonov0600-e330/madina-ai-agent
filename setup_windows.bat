@echo off
setlocal
if not exist .venv (
  py -3 -m venv .venv
  if errorlevel 1 python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo Paketlarni o'rnatishda xatolik. Python 3.11+ borligini tekshiring.
  pause
  exit /b 1
)
if not exist .env copy .env.example .env
echo Tayyor. Endi .env faylini to'ldirib, run_windows.bat ni ishga tushiring.
pause
