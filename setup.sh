#!/bin/bash
# Video Automator - Setup Script

echo "=================================="
echo "Video Automator - Setup Script"
echo "=================================="
echo ""

# Check Python
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi
echo "✓ Python found: $(python3 --version)"
echo ""

# Check FFmpeg
echo "Checking FFmpeg installation..."
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg is not installed!"
    echo ""
    echo "Please install FFmpeg:"
    echo "  macOS:   brew install ffmpeg"
    echo "  Linux:   sudo apt install ffmpeg"
    echo "  Windows: Download from https://ffmpeg.org/download.html"
    echo ""
    read -p "Press Enter to continue anyway (app will warn you)..."
else
    echo "✓ FFmpeg found: $(ffmpeg -version | head -n 1)"
fi
echo ""

# Check GPU (optional)
echo "Checking for NVIDIA GPU..."
if command -v nvidia-smi &> /dev/null; then
    echo "✓ NVIDIA GPU detected!"
    nvidia-smi --query-gpu=name --format=csv,noheader
    echo "  → Will use GPU acceleration for faster rendering"
else
    echo "ℹ No NVIDIA GPU detected"
    echo "  → Will use CPU rendering (slower but works fine)"
fi
echo ""

# Install Python dependencies
echo "Installing Python packages..."
echo "(This may take a few minutes, especially on first run)"
echo ""

pip3 install --upgrade pip
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✓ Installation Complete!"
    echo "=================================="
    echo ""
    echo "To run the app:"
    echo "  python3 video_automator.py"
    echo ""
    echo "Or use the run script:"
    echo "  ./run.sh"
    echo ""
else
    echo ""
    echo "❌ Installation failed!"
    echo "Please check the error messages above."
    exit 1
fi
