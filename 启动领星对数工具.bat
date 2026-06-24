@echo off
setlocal

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "PYTHON=C:\Users\Wang\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if not exist "%BACKEND%\app\main.py" (
  echo Backend path not found:
  echo %BACKEND%
  echo.
  pause
  exit /b 1
)

if not exist "%PYTHON%" (
  echo Python runtime not found:
  echo %PYTHON%
  echo.
  pause
  exit /b 1
)

cd /d "%BACKEND%"
set "PYTHONPATH=%BACKEND%"

echo Lingxing reconcile tool is starting...
echo.
echo Open this URL in your browser:
echo http://127.0.0.1:8000/
echo.
echo Keep this window open. Closing it will stop the web page.
echo.
"%PYTHON%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

echo.
echo Server stopped.
pause