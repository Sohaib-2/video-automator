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
    
    def __init__(self, fps=None, quality=None):
        """
        Initialize video configuration
        
        Args:
            fps: Frames per second (default: 30)
            quality: Quality preset value (default: 28)
        """
        self.fps = fps or self.FPS_STANDARD
        self.quality = quality or self.QUALITY_MEDIUM
        
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
        
        return {
            'fps': self.fps,
            'fps_name': fps_name.get(self.fps, f"{self.fps}fps"),
            'quality': self.quality,
            'quality_name': quality_name.get(self.quality, "Custom")
        }