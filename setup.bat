@echo off
title Handwritten OCR Setup
echo ============================
echo Handwritten OCR Setup
echo ============================

python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH. Please install Python 3.11.
    rem pause
    exit /b 1
)

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing CPU-only PyTorch...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

echo Installing requirements...
pip install -r requirements.txt

echo Creating directories...
mkdir models input output test_images evaluation\images evaluation\ground_truth evaluation\results logs 2>nul

echo Downloading model...
python download_model.py
if errorlevel 1 (
    echo MODEL DOWNLOAD FAILED
    rem pause
    exit /b 1
)

echo Setup complete!
rem pause
