@echo off
setlocal
cd /d "%~dp0"
echo ========================================
echo    FRAMECRAFT THUMBNAIL STUDIO
echo ========================================
if not exist "backend\.env" copy /y "backend\.env.example" "backend\.env" >nul
if not exist "backend\.venv\Scripts\python.exe" (
  echo Creating Python environment...
  py -3 -m venv "backend\.venv" 2>nul
  if errorlevel 1 python -m venv "backend\.venv"
  if not exist "backend\.venv\Scripts\python.exe" goto :error
)
echo Installing Python dependencies...
"backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt"
if errorlevel 1 goto :error
if not exist "frontend\node_modules" (
  echo Installing frontend dependencies...
  call npm --prefix frontend install
  if errorlevel 1 goto :error
)
echo.
echo Opening backend and frontend terminals...
start "Framecraft API - DO NOT CLOSE" "%~dp0backend\run_windows.bat"
start "Framecraft WEB - DO NOT CLOSE" "%~dp0frontend\run_windows.bat"
echo.
echo Open http://localhost:5173 in your browser.
echo Leave both new terminal windows running.
pause
exit /b 0
:error
echo Setup failed. Check Python 3.11+ and Node.js 20+ are installed and internet is available.
pause
exit /b 1
