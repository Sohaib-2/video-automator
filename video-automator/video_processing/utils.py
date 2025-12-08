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


def get_video_duration(video_path: str) -> float:
    """Get duration of video file in seconds"""
    ffprobe_cmd = get_ffprobe_path()
    cmd = [
        ffprobe_cmd,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return 0.0


def detect_intro_videos(folder_path: str, min_duration: float = 6.0, max_duration: float = 12.0) -> List[str]:
    """
    Detect intro video files in folder with duration between min and max seconds

    Args:
        folder_path: Path to folder to search
        min_duration: Minimum video duration in seconds (default 6.0)
        max_duration: Maximum video duration in seconds (default 12.0)

    Returns:
        List of video file paths sorted alphabetically
    """
    folder = Path(folder_path)
    video_exts = ['.mp4', '.mov', '.avi', '.mkv']
    intro_videos = []

    # Find all video files
    all_videos = []
    for ext in video_exts:
        all_videos.extend(folder.glob(f'*{ext}'))

    # Sort alphabetically
    all_videos = sorted(all_videos, key=lambda x: x.name)

    # Filter by duration
    for video_path in all_videos:
        try:
            duration = get_video_duration(str(video_path))
            if min_duration <= duration <= max_duration:
                intro_videos.append(str(video_path))
                print(f"[INTRO] Found intro video: {video_path.name} ({duration:.1f}s)")
        except Exception as e:
            print(f"[INTRO] Skipping {video_path.name}: {e}")
            continue

    if intro_videos:
        print(f"[INTRO] Total intro videos found: {len(intro_videos)}")

    return intro_videos


def detect_files_in_folder(folder_path: str) -> Dict[str, any]:
    """
    Detect required files in a video folder

    Returns:
        dict: {
            'voiceover': path to audio file or None,
            'script': path to script.txt or None,
            'images': list of image paths,
            'intro_videos': list of intro video paths (6-12 seconds)
        }
    """
    folder = Path(folder_path)
    detected = {
        'voiceover': None,
        'script': None,
        'images': [],
        'intro_videos': []
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

    # Look for intro videos (6-12 seconds duration)
    detected['intro_videos'] = detect_intro_videos(folder_path)

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