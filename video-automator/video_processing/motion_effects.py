"""
Motion Effects Builder
Generates FFmpeg filter strings for various motion effects
"""

import logging
from typing import Dict, Optional
from PIL import Image

logger = logging.getLogger(__name__)


class MotionEffectBuilder:
    """Builds FFmpeg filter strings for motion effects"""
    
    SUPPORTED_EFFECTS = [
        "Static",
        "Zoom In",
        "Zoom Out",
        "Pan Right",
        "Pan Left",
        "Ken Burns"
    ]
    
    @staticmethod
    def build_filter(
        effect: str,
        time_per_image: float,
        fps: int,
        crop_settings: Optional[Dict] = None,
        image_path: Optional[str] = None
    ) -> str:
        """
        Build FFmpeg filter for per-image processing (crop and scale only)
        
        Args:
            effect: Motion effect name (not used here, kept for compatibility)
            time_per_image: Duration for each image in seconds
            fps: Frames per second
            crop_settings: Optional crop region {'x', 'y', 'width', 'height'}
            image_path: Path to image file (needed for crop validation)
            
        Returns:
            FFmpeg filter string for image preparation
        """
        # Build base filter with crop handling - no motion effects here
        base_filter = MotionEffectBuilder._build_base_filter(
            crop_settings, image_path
        )
        
        # Just apply base filter and fps - motion will be applied at video level
        return f"{base_filter},fps={fps}"
    
    @staticmethod
    def build_video_level_filter(
        effect: str,
        total_duration: float,
        fps: int
    ) -> Optional[str]:
        """
        Build FFmpeg filter for video-level motion effects
        Applied to entire concatenated video
        
        Args:
            effect: Motion effect name
            total_duration: Total video duration in seconds
            fps: Frames per second
            
        Returns:
            FFmpeg filter string for video-level effect, or None for Static
        """
        if effect == "Static":
            # No effect needed
            return None
        
        elif effect == "Zoom In":
            # Zoom in across entire video duration - use time-based formula
            logger.info(f"Applying video-level Zoom In over {total_duration:.1f}s")
            return (
                f"scale=2496:1404:force_original_aspect_ratio=increase,"
                f"zoompan=z='min(1.0+0.3*t/{total_duration:.2f},1.3)':s=1920x1080:fps={fps}:d=1"
            )
        
        elif effect == "Zoom Out":
            # Zoom out across entire video duration - use time-based formula
            logger.info(f"Applying video-level Zoom Out over {total_duration:.1f}s")
            return (
                f"scale=2496:1404:force_original_aspect_ratio=increase,"
                f"zoompan=z='max(1.3-0.3*t/{total_duration:.2f},1.0)':s=1920x1080:fps={fps}:d=1"
            )
        
        elif effect == "Pan Right":
            # Pan right across entire video duration
            logger.info(f"Applying video-level Pan Right over {total_duration:.1f}s")
            return (
                f"scale=2304:1296:force_original_aspect_ratio=increase,"
                f"crop=1920:1080:'min(iw-1920,(iw-1920)*t/{total_duration:.2f})':0"
            )
        
        elif effect == "Pan Left":
            # Pan left across entire video duration
            logger.info(f"Applying video-level Pan Left over {total_duration:.1f}s")
            return (
                f"scale=2304:1296:force_original_aspect_ratio=increase,"
                f"crop=1920:1080:'(iw-1920)*max(0,1-t/{total_duration:.2f})':0"
            )
        
        elif effect == "Ken Burns":
            # Ken Burns effect across entire video duration
            logger.info(f"Applying video-level Ken Burns over {total_duration:.1f}s")
            return (
                f"scale=2496:1404:force_original_aspect_ratio=increase,"
                f"zoompan=z='min(1.0+0.5*t/{total_duration:.2f},1.5)':"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"s=1920x1080:fps={fps}:d=1"
            )
        
        else:
            logger.warning(f"Unknown motion effect: {effect}, no effect applied")
            return None
    
    @staticmethod
    def _build_base_filter(
        crop_settings: Optional[Dict],
        image_path: Optional[str]
    ) -> str:
        """
        Build base filter with crop handling
        
        Args:
            crop_settings: Crop region or None
            image_path: Path to validate crop against
            
        Returns:
            Base FFmpeg filter string
        """
        if not crop_settings or not image_path:
            return "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
        
        try:
            # Validate crop settings
            with Image.open(image_path) as img:
                img_w, img_h = img.size
                
            crop_x = crop_settings['x']
            crop_y = crop_settings['y']
            crop_w = crop_settings['width']
            crop_h = crop_settings['height']
            
            # Validate coordinates
            if crop_x < 0 or crop_y < 0 or crop_w <= 0 or crop_h <= 0:
                logger.warning(f"Invalid crop coordinates: {crop_settings}. Using default auto-crop.")
                return "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
            
            # CRITICAL FIX: Clamp crop dimensions to image boundaries BEFORE using
            if crop_x >= img_w or crop_y >= img_h:
                logger.warning(f"Crop position ({crop_x},{crop_y}) outside image {img_w}x{img_h}. Using default.")
                return "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
            
            # Adjust if crop exceeds boundaries
            if crop_x + crop_w > img_w:
                crop_w = img_w - crop_x
                logger.warning(f"Crop width adjusted to {crop_w} to fit image width {img_w}")
            
            if crop_y + crop_h > img_h:
                crop_h = img_h - crop_y
                logger.warning(f"Crop height adjusted to {crop_h} to fit image height {img_h}")
            
            # Ensure minimum size
            if crop_w < 100 or crop_h < 100:
                logger.warning(f"Crop too small ({crop_w}x{crop_h}). Using default.")
                return "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"
            
            # Build exact crop→scale filter
            filter_str = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale=1920:1080:flags=lanczos"
            logger.info(f"Using custom crop: {crop_w}x{crop_h} at ({crop_x},{crop_y}) from {img_w}x{img_h}")
            logger.info("EXACT MATCH: Preview composition will be preserved in video")
            
            return filter_str
            
        except Exception as e:
            logger.error(f"Failed to validate crop settings: {e}")
            logger.warning("Falling back to default auto-crop")
            return "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"