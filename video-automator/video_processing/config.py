"""
Video Configuration
Defines FPS and quality presets for video rendering
"""


class VideoConfig:
    """Video rendering configuration with FPS and quality presets"""

    # FPS Presets
    FPS_CINEMA = 24
    FPS_STANDARD = 30
    FPS_SMOOTH = 60

    # Quality Presets (CRF/CQ values)
    QUALITY_LOW = 32
    QUALITY_MEDIUM = 28
    QUALITY_HIGH = 23
    QUALITY_MAX = 18

    # Resolution Presets (width, height)
    RESOLUTION_720P = (1280, 720)
    RESOLUTION_1080P = (1920, 1080)
    RESOLUTION_2K = (2560, 1440)
    RESOLUTION_4K = (3840, 2160)

    @staticmethod
    def resolution_from_string(res_str):
        """
        Convert resolution string to tuple

        Args:
            res_str: Resolution string ('720p', '1080p', '2K', '4K')

        Returns:
            Tuple of (width, height)
        """
        resolution_map = {
            '720p': VideoConfig.RESOLUTION_720P,
            '1080p': VideoConfig.RESOLUTION_1080P,
            '2K': VideoConfig.RESOLUTION_2K,
            '4K': VideoConfig.RESOLUTION_4K
        }
        return resolution_map.get(res_str, VideoConfig.RESOLUTION_1080P)

    def __init__(self, fps=None, quality=None, resolution=None):
        """
        Initialize video configuration

        Args:
            fps: Frames per second (default: 30)
            quality: Quality preset value (default: 28)
            resolution: Resolution tuple (width, height) or string (default: 1920x1080)
        """
        self.fps = fps or self.FPS_STANDARD
        self.quality = quality or self.QUALITY_MEDIUM

        # Handle resolution as either tuple or string
        if isinstance(resolution, str):
            self.resolution = self.resolution_from_string(resolution)
        else:
            self.resolution = resolution or self.RESOLUTION_1080P
        
    def get_info(self):
        """Get human-readable info about current settings"""
        fps_name = {
            24: "Cinema (24fps)",
            30: "Standard (30fps)",
            60: "Smooth (60fps)"
        }
        quality_name = {
            32: "Low",
            28: "Medium",
            23: "High",
            18: "Maximum"
        }
        resolution_name = {
            (1280, 720): "720p HD",
            (1920, 1080): "1080p Full HD",
            (2560, 1440): "2K QHD",
            (3840, 2160): "4K Ultra HD"
        }

        return {
            'fps': self.fps,
            'fps_name': fps_name.get(self.fps, f"{self.fps}fps"),
            'quality': self.quality,
            'quality_name': quality_name.get(self.quality, "Custom"),
            'resolution': self.resolution,
            'resolution_name': resolution_name.get(self.resolution, f"{self.resolution[0]}x{self.resolution[1]}")
        }