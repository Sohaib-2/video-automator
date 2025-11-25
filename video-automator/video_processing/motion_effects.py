"""
Motion Effects Builder
Generates FFmpeg filter strings for various motion effects with multiple effect support
"""

import logging
from typing import Dict, Optional, List
from PIL import Image

logger = logging.getLogger(__name__)


class MotionEffectBuilder:
    """Builds FFmpeg filter strings for motion effects"""
    
    SUPPORTED_EFFECTS = [
        "Static",
        "Noise",
        "Tilt"
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
    def build_video_level_filters(
        effects: List[str],
        total_duration: float,
        fps: int,
        intensities: Optional[Dict[str, int]] = None
    ) -> Optional[str]:
        """
        Build FFmpeg filters for multiple video-level motion effects with intensity control
        Applied to entire concatenated video
        
        Args:
            effects: List of motion effect names
            total_duration: Total video duration in seconds
            fps: Frames per second
            intensities: Dict mapping effect name to intensity (0-100)
            
        Returns:
            Combined FFmpeg filter string for video-level effects, or None for Static only
        """
        if intensities is None:
            intensities = {}
        
        # Remove "Static" from effects list if present
        active_effects = [e for e in effects if e != "Static"]
        
        if not active_effects:
            logger.info("No motion effects selected (Static)")
            return None
        
        filter_chain = []
        
        for effect in active_effects:
            intensity = intensities.get(effect, 50)  # Default 50% intensity
            effect_filter = MotionEffectBuilder._build_single_effect(
                effect, total_duration, fps, intensity
            )
            if effect_filter:
                filter_chain.append(effect_filter)
        
        if not filter_chain:
            return None
        
        # Combine filters with comma separator
        combined = ",".join(filter_chain)
        logger.info(f"Applied {len(filter_chain)} video-level effect(s): {', '.join(active_effects)}")
        
        return combined
    
    @staticmethod
    def _build_single_effect(
        effect: str,
        total_duration: float,
        fps: int,
        intensity: int = 50
    ) -> Optional[str]:
        """
        Build single effect filter with intensity control
        
        Args:
            effect: Motion effect name
            total_duration: Total video duration in seconds
            fps: Frames per second
            intensity: Effect intensity from 0-100 (50 = default)
            
        Returns:
            FFmpeg filter string for single effect
        """
        
        if effect == "Noise":
            # BIG CHUNKY GRAIN like CapCut noise2 filter
            # Scale intensity: 0-100 maps to grain size
            # Use geq (generic equation) filter for custom large grain
            grain_size = int(5 + (intensity / 100.0) * 15)  # 5-20 pixel grain size
            grain_strength = int(20 + (intensity / 100.0) * 60)  # 20-80 noise strength
            
            logger.info(f"Adding BIG GRAIN Noise effect - Intensity: {intensity}%, Size: {grain_size}px")
            
            # Create large blocky grain using geq with random noise per block
            return (
                f"geq=lum='p(X,Y)+(random(0)*{grain_strength}-{grain_strength/2})*"
                f"(1-mod(X,{grain_size})/(2*{grain_size}))*(1-mod(Y,{grain_size})/(2*{grain_size}))':"
                f"cb=128:cr=128"
            )
        
        elif effect == "Camera Shake":
            # Camera shake with adjustable intensity
            # Scale shake amount based on intensity: 0-100 maps to 0-10px
            shake_amount = int((intensity / 100.0) * 10)  # 0-10px
            if shake_amount < 2:
                shake_amount = 2  # Minimum 2px
            
            crop_w = 1920 - (shake_amount * 2)
            crop_h = 1080 - (shake_amount * 2)
            
            logger.info(f"Adding Camera Shake effect - Intensity: {intensity}%, Amount: {shake_amount}px")
            return (
                f"crop={crop_w}:{crop_h}:"
                f"x='{shake_amount}+{shake_amount}*sin(t*3)':"
                f"y='{shake_amount}+{shake_amount}*cos(t*3)',"
                f"scale=1920:1080:flags=lanczos"
            )
        
        elif effect == "Tilt":
            # Tilt/rotation with adjustable intensity
            # Scale tilt angle based on intensity: 0-100 maps to 0-5 degrees
            tilt_angle = (intensity / 100.0) * 5.0  # 0-5 degrees
            if tilt_angle < 0.5:
                tilt_angle = 0.5  # Minimum 0.5 degree
            
            logger.info(f"Adding Tilt effect - Intensity: {intensity}%, Angle: {tilt_angle:.1f}°")
            
            # Pre-scale to avoid black edges
            scale_factor = 1.15  # Scale up 15% to ensure no black edges during rotation
            return (
                f"scale={int(1920*scale_factor)}:{int(1080*scale_factor)}:flags=lanczos,"
                f"rotate='{tilt_angle}*PI/180*sin(t*0.5)':c=none,"
                f"crop=1920:1080:(iw-1920)/2:(ih-1080)/2"
            )
        
        else:
            logger.warning(f"Unknown motion effect: {effect}, skipping")
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