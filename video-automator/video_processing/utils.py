"""
Video Processing Utilities
Helper functions for system checks and file operations
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List
from utils.resource_path import get_ffmpeg_path, get_ffprobe_path


def check_ffmpeg_installed() -> bool:
    """Check if FFmpeg is installed and available"""
    try:
        ffmpeg_cmd = get_ffmpeg_path()
        subprocess.run([ffmpeg_cmd, '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_gpu_available() -> bool:
    """Check if NVIDIA GPU is available for encoding"""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_audio_duration(audio_path: str) -> float:
    """Get duration of audio file in seconds"""
    ffprobe_cmd = get_ffprobe_path()
    cmd = [
        ffprobe_cmd,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        audio_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def detect_files_in_folder(folder_path: str) -> Dict[str, any]:
    """
    Detect required files in a video folder
    
    Returns:
        dict: {
            'voiceover': path to audio file or None,
            'script': path to script.txt or None,
            'images': list of image paths
        }
    """
    folder = Path(folder_path)
    detected = {
        'voiceover': None,
        'script': None,
        'images': []
    }
    
    # Look for audio files
    audio_exts = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']
    for ext in audio_exts:
        audio_files = list(folder.glob(f'*{ext}')) + list(folder.glob(f'voiceover{ext}'))
        if audio_files:
            detected['voiceover'] = str(audio_files[0])
            break
    
    # Look for script
    script_file = folder / 'script.txt'
    if script_file.exists():
        detected['script'] = str(script_file)
    
    # Look for images
    image_exts = ['.png', '.jpg', '.jpeg', '.webp']
    all_images = []
    for ext in image_exts:
        all_images.extend(folder.glob(f'*{ext}'))
    
    all_images = sorted(all_images, key=lambda x: x.name)
    detected['images'] = [str(img) for img in all_images]
    
    return detected


def validate_folder(folder_path: str) -> tuple[bool, str]:
    """
    Validate if folder has all required files
    
    Returns:
        tuple: (is_valid, info_message)
    """
    detected = detect_files_in_folder(folder_path)
    
    missing = []
    if not detected['voiceover']:
        missing.append('voiceover audio')
    if not detected['images'] or len(detected['images']) == 0:
        missing.append('at least 1 image')
    
    if missing:
        return False, f"Missing files: {', '.join(missing)}"
    
    num_images = len(detected['images'])
    if num_images == 1:
        info = "Found 1 image (will be used throughout entire video)"
    else:
        info = f"Found {num_images} images (will be distributed across video duration)"
    
    return True, info