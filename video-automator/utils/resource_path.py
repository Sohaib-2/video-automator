"""
Resource Path Helper
Resolves file paths for both development and PyInstaller bundled modes
"""

import os
import sys


def get_resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and PyInstaller bundle
    
    Args:
        relative_path: Relative path to resource (e.g., 'resources/noise2.mp4')
    
    Returns:
        Absolute path to resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Development mode - use project root
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relative_path)


def get_ffmpeg_path():
    """
    Get FFmpeg executable path, checks bundled location first
    
    Returns:
        Path to ffmpeg executable or 'ffmpeg' (system PATH)
    """
    # Check bundled location first
    bundled_ffmpeg = get_resource_path('ffmpeg.exe')
    if os.path.exists(bundled_ffmpeg):
        return bundled_ffmpeg
    
    # Fallback to system PATH
    return 'ffmpeg'


def get_ffprobe_path():
    """
    Get FFprobe executable path, checks bundled location first
    
    Returns:
        Path to ffprobe executable or 'ffprobe' (system PATH)
    """
    # Check bundled location first
    bundled_ffprobe = get_resource_path('ffprobe.exe')
    if os.path.exists(bundled_ffprobe):
        return bundled_ffprobe
    
    # Fallback to system PATH
    return 'ffprobe'