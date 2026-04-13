@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: virtual environment not found at .venv\Scripts\python.exe
    exit /b 1
)

echo Running Red Sea corridor full cycle...
call ".venv\Scripts\python.exe" -m corridor.cli run-all

if errorlevel 1 (
    echo.
    echo RUN-ALL FAILED
    exit /b 1
)

echo.
echo RUN-ALL PASSED
exit /b 0