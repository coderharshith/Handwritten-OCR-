@echo off
title Booklet Evaluation System - Setup
echo ============================================
echo   Booklet Evaluation System - Setup
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10 or newer from https://python.org
    pause
    exit /b 1
)

echo [OK] Python found.

:: Create virtual environment
if not exist .venv (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

call .venv\Scripts\activate.bat

:: Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip --quiet

:: Install CPU-only PyTorch
echo [INFO] Installing CPU-only PyTorch (this may take a while)...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu --quiet

:: Install all other requirements
echo [INFO] Installing project requirements...
pip install -r requirements.txt --quiet

:: Create required directories
echo [INFO] Creating project directories...
mkdir models 2>nul
mkdir input 2>nul
mkdir output 2>nul
mkdir test_images 2>nul
mkdir assets 2>nul
mkdir result 2>nul
mkdir student_results 2>nul
mkdir logs 2>nul
mkdir evaluation\images 2>nul
mkdir evaluation\ground_truth 2>nul
mkdir evaluation\results 2>nul

:: Download AI model
echo.
echo [INFO] Downloading TrOCR model (approx. 2.2 GB)...
echo       This is a one-time download. Please wait...
echo.
python download_model.py
if errorlevel 1 (
    echo.
    echo [ERROR] Model download failed!
    echo        Please check your internet connection and try again.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Setup Complete!
echo ============================================
echo.
echo  Run the app:     Double-click run.bat
echo  Web Application: http://127.0.0.1:8000
echo  Teacher Login:   gsssteacher / gsss@23
echo  Student Login:   4GW23AI001 / stu@123
echo.
pause
