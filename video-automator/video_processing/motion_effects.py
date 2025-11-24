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
        Build FFmpeg filter for motion effect with crop preservation
        
        Args:
            effect: Motion effect name
            time_per_image: Duration for each image in seconds
            fps: Frames per second
            crop_settings: Optional crop region {'x', 'y', 'width', 'height'}
            image_path: Path to image file (needed for crop validation)
            
        Returns:
            FFmpeg filter string
        """
        num_frames = int(time_per_image * fps)
        
        # Build base filter with crop handling
        base_filter = MotionEffectBuilder._build_base_filter(
            crop_settings, image_path
        )
        
        # Apply motion effect
        if effect == "Static":
            return f"{base_filter},fps={fps}"
        
        elif effect == "Zoom In":
            return (
                f"{base_filter},"
                f"zoompan=z='min(zoom+0.001,1.3)':d={num_frames}:s=1920x1080:fps={fps}"
            )
        
        elif effect == "Zoom Out":
            return (
                f"{base_filter},"
                f"zoompan=z='if(eq(on,1),1.3,max(1.0,zoom-0.001))':d={num_frames}:s=1920x1080:fps={fps}"
            )
        
        elif effect == "Pan Right":
            if crop_settings:
                return (
                    f"{base_filter},"
                    f"scale=2304:1296,"
                    f"crop=1920:1080:'min(iw-1920,(iw-1920)*(on/{num_frames}))':0,"
                    f"fps={fps}"
                )
            else:
                return (
                    f"scale=2304:1296:force_original_aspect_ratio=increase,"
                    f"crop=1920:1080:'min(iw-1920,(iw-1920)*(on/{num_frames}))':0,"
                    f"fps={fps}"
                )
        
        elif effect == "Pan Left":
            if crop_settings:
                return (
                    f"{base_filter},"
                    f"scale=2304:1296,"
                    f"crop=1920:1080:'(iw-1920)*(1-on/{num_frames})':0,"
                    f"fps={fps}"
                )
            else:
                return (
                    f"scale=2304:1296:force_original_aspect_ratio=increase,"
                    f"crop=1920:1080:'(iw-1920)*(1-on/{num_frames})':0,"
                    f"fps={fps}"
                )
        
        elif effect == "Ken Burns":
            if crop_settings:
                return (
                    f"{base_filter},"
                    f"scale=2304:1296,"
                    f"zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                    f"d={num_frames}:s=1920x1080:fps={fps}"
                )
            else:
                return (
                    f"scale=2304:1296:force_original_aspect_ratio=increase,"
                    f"zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                    f"d={num_frames}:s=1920x1080:fps={fps}"
                )
        
        else:
            logger.warning(f"Unknown motion effect: {effect}, using Static")
            return f"{base_filter},fps={fps}"
    
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
            
            # Adjust if crop exceeds boundaries
            if crop_x + crop_w > img_w or crop_y + crop_h > img_h:
                logger.warning(
                    f"Crop region {crop_w}x{crop_h} at ({crop_x},{crop_y}) "
                    f"exceeds image dimensions {img_w}x{img_h}"
                )
                crop_w = min(crop_w, img_w - crop_x)
                crop_h = min(crop_h, img_h - crop_y)
                logger.info(f"Adjusted crop to: {crop_w}x{crop_h} at ({crop_x},{crop_y})")
            
            # Build exact crop→scale filter
            filter_str = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale=1920:1080:flags=lanczos"
            logger.info(f"Using custom crop: {crop_w}x{crop_h} at ({crop_x},{crop_y})")
            logger.info("EXACT MATCH: Preview composition will be preserved in video")
            
            return filter_str
            
        except Exception as e:
            logger.error(f"Failed to validate crop settings: {e}")
            logger.warning("Falling back to default auto-crop")
            return "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"