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


def get_available_fonts():
    """
    Get list of all available bundled fonts by auto-discovering .ttf files

    Returns:
        Dictionary mapping font display names to font file paths
    """
    fonts_dir = get_resource_path('resources/fonts')
    available_fonts = {}

    if not os.path.exists(fonts_dir):
        return available_fonts

    # Scan for all .ttf files in fonts directory
    for filename in os.listdir(fonts_dir):
        if filename.lower().endswith('.ttf'):
            font_path = os.path.join(fonts_dir, filename)

            # Extract font display name from filename
            # Example: "EBGaramond-Bold.ttf" -> "EB Garamond Bold"
            # Example: "Roboto-Regular.ttf" -> "Roboto"
            font_name = filename[:-4]  # Remove .ttf extension

            # Replace hyphens with spaces and format nicely
            font_name = font_name.replace('-', ' ')

            # Store in dictionary
            available_fonts[font_name] = font_path

    return available_fonts


def get_font_path(font_name):
    """
    Get bundled font file path by auto-discovering from fonts directory

    Args:
        font_name: Font name (e.g., 'EB Garamond Bold', 'Roboto Regular')

    Returns:
        Absolute path to font file if found, None otherwise
    """
    # Get all available fonts
    available_fonts = get_available_fonts()

    # Direct match first
    if font_name in available_fonts:
        return available_fonts[font_name]

    # Try case-insensitive match
    font_name_lower = font_name.lower()
    for name, path in available_fonts.items():
        if name.lower() == font_name_lower:
            return path

    # Not found
    return None