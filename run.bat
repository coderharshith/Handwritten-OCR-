@echo off
title Booklet Evaluation System
echo =======================================================
echo         Booklet Evaluation System - Starting...
echo =======================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if not exist ".venv" (
    echo [ERROR] Virtual environment not found in %SCRIPT_DIR%.venv!
    echo Please run setup.bat first.
    pause
    exit /b 1
)

if not exist "models\trocr-large-handwritten" (
    echo [ERROR] TrOCR AI model not found in models\trocr-large-handwritten!
    echo Please run setup.bat to download the model first.
    pause
    exit /b 1
)

echo [INFO] Checking MySQL Database status on port 3306...
netstat -ano | findstr ":3306" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] MySQL is not running. Starting MySQL service...
    if exist "D:\xampp\mysql_start.bat" (
        start "" /B "D:\xampp\mysql_start.bat"
        timeout /t 3 /nobreak >nul
    ) else if exist "D:\xampp\mysql\bin\mysqld.exe" (
        start "" /B cmd.exe /c "cd /D D:\xampp && mysql\bin\mysqld --defaults-file=mysql\bin\my.ini --console"
        timeout /t 3 /nobreak >nul
    ) else if exist "C:\xampp\mysql_start.bat" (
        start "" /B "C:\xampp\mysql_start.bat"
        timeout /t 3 /nobreak >nul
    ) else if exist "C:\xampp\mysql\bin\mysqld.exe" (
        start "" /B cmd.exe /c "cd /D C:\xampp && mysql\bin\mysqld --defaults-file=mysql\bin\my.ini --console"
        timeout /t 3 /nobreak >nul
    ) else (
        echo [WARNING] Could not locate XAMPP MySQL automatically.
        echo Please ensure MySQL is started on port 3306.
    )
) else (
    echo [OK] MySQL is active on port 3306.
)

call .venv\Scripts\activate.bat

echo.
echo =======================================================
echo  [OK] Starting Booklet Evaluation System Server
echo =======================================================
echo.
echo   Web Application : http://127.0.0.1:8000
echo   Teacher Portal  : http://127.0.0.1:8000 (Faculty Evaluation)
echo   Student Portal  : http://127.0.0.1:8000 (Student Results)
echo.
echo   Teacher Login   : gsssteacher / gsss@23
echo   Student Login   : 4GW23AI001 / stu@123
echo.
echo =======================================================
echo  Opening browser at http://127.0.0.1:8000...
echo  Press Ctrl+C in this window to stop the server.
echo =======================================================
echo.

start "" http://127.0.0.1:8000

cd /d "%SCRIPT_DIR%backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
