@echo off
setlocal
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo Creating virtual environment...
  python -m venv .venv
)

call .venv\Scripts\activate

echo Open http://127.0.0.1:8000 in your browser
python start.py
endlocal
