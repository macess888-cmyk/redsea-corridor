@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: virtual environment not found at .venv\Scripts\python.exe
    exit /b 1
)

echo Running Red Sea corridor test suite...
call ".venv\Scripts\python.exe" -m unittest discover -s tests -v

if errorlevel 1 (
    echo.
    echo TESTS FAILED
    exit /b 1
)

echo.
echo TESTS PASSED
exit /b 0