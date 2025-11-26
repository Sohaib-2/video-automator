@echo off
echo ============================================
echo Video Automator - Windows Build Script
echo ============================================
echo.

echo [1/5] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)
echo.

echo [2/5] Checking dependencies...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)
echo.

echo [3/5] Checking Whisper model...
if not exist "video-automator\models\base.pt" (
    echo Downloading Whisper model...
    python download_whisper_model.py
)
echo.

echo [4/5] Building executable...
pyinstaller VideoAutomator.spec
if errorlevel 1 (
    echo ERROR: Build failed!
    pause
    exit /b 1
)
echo.

echo [5/5] Adding FFmpeg binaries...
copy /Y ffmpeg.exe dist\VideoAutomator\ >nul
copy /Y ffprobe.exe dist\VideoAutomator\ >nul
echo.

echo ============================================
echo BUILD COMPLETE!
echo ============================================
echo.
echo Output: dist\VideoAutomator\
echo.
echo Next steps:
echo 1. Test: dist\VideoAutomator\VideoAutomator.exe
echo 2. If working, ZIP the folder for distribution
echo.
pause
