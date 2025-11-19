@echo off
REM Video Automator - Windows Setup Script

echo ==================================
echo Video Automator - Setup Script
echo ==================================
echo.

REM Check Python
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python is not installed!
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)
python --version
echo.

REM Check FFmpeg
echo Checking FFmpeg installation...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] FFmpeg is not installed!
    echo.
    echo Please install FFmpeg:
    echo   1. Download from https://ffmpeg.org/download.html
    echo   2. Extract to C:\ffmpeg
    echo   3. Add C:\ffmpeg\bin to PATH
    echo.
    pause
) else (
    echo [OK] FFmpeg found
)
echo.

REM Check GPU
echo Checking for NVIDIA GPU...
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] NVIDIA GPU detected - will use GPU acceleration
    nvidia-smi --query-gpu=name --format=csv,noheader
) else (
    echo [i] No NVIDIA GPU detected - will use CPU rendering
)
echo.

REM Install dependencies
echo Installing Python packages...
echo (This may take a few minutes on first run)
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% equ 0 (
    echo.
    echo ==================================
    echo [OK] Installation Complete!
    echo ==================================
    echo.
    echo To run the app:
    echo   python video_automator.py
    echo.
    echo Or double-click: run.bat
    echo.
) else (
    echo.
    echo [X] Installation failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)

pause
