"""
Motion Effects Builder
Generates FFmpeg filter strings for various motion effects with intensity control
UPDATED: 4 effects - Static, Noise (BIG CHUNKY RANDOM GRAIN), Tilt, Dynamic Tilt
"""

import logging
from typing import Dict, Optional, List
from PIL import Image
from utils.resource_path import get_resource_path

logger = logging.getLogger(__name__)


class MotionEffectBuilder:
    """Builds FFmpeg filter strings for motion effects"""
    
    SUPPORTED_EFFECTS = [
        "Static",
        "Noise",
        "Tilt",
        "Dynamic Tilt"
    ]

    DEFAULT_INTENSITIES = {
        "Noise": 50,
        "Tilt": 50,
        "Dynamic Tilt": 50
    }
    
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
        
        # Separate video overlay effects from filter effects
        video_overlay_result = None
        filter_chain = []
        
        for effect in active_effects:
            intensity = intensities.get(effect, 50)  # Default 50% intensity
            effect_filter = MotionEffectBuilder._build_single_effect(
                effect, total_duration, fps, intensity
            )
            
            if effect_filter:
                # Check if this is a video overlay instruction
                if isinstance(effect_filter, str) and effect_filter.startswith("VIDEO_OVERLAY|"):
                    if video_overlay_result is None:
                        video_overlay_result = effect_filter
                    else:
                        logger.warning(f"Multiple video overlays detected, using first one only")
                else:
                    # Regular filter string
                    filter_chain.append(effect_filter)
        
        # NEW: Return BOTH video overlay AND filters if both present
        if video_overlay_result and filter_chain:
            # Combine them with special separator
            combined_filters = ",".join(filter_chain)
            result = f"{video_overlay_result}|FILTERS|{combined_filters}"
            logger.info(f"Combining video overlay + {len(filter_chain)} other effect(s)")
            return result
        
        # Return video overlay alone if present
        if video_overlay_result:
            logger.info(f"Returning video overlay instruction (no other filters)")
            return video_overlay_result
        
        # Return combined filters if no overlay
        if not filter_chain:
            return None
        
        # Combine filters with comma separator
        combined = ",".join(filter_chain)
        logger.info(f"Applied {len(filter_chain)} video-level effect(s): {', '.join([e for e in active_effects if e != 'Noise'])}")
        
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
            # REAL FILM GRAIN OVERLAY - Uses actual noise2.mp4 video file
            # This is how CapCut does it - overlay real grain footage!
            
            # Opacity based on intensity: 0-100% maps to 0.1-0.5 alpha
            # Range: 0.1 (10% - very subtle) to 0.5 (50% - strong)
            opacity = 0.1 + (intensity / 100.0) * 0.4
            
            logger.info(f"Adding REAL FILM GRAIN overlay - Intensity: {intensity}%, Opacity: {opacity:.2f}")
            
            # Path to grain overlay video (3 second loop)
            grain_video_path = get_resource_path("resources/noise2.mp4")
            
            # Check if grain overlay exists
            import os
            if not os.path.exists(grain_video_path):
                logger.error(f"Grain overlay not found at: {grain_video_path}")
                logger.warning("Skipping noise effect - file missing")
                return None
            
            logger.info(f"Using grain overlay: {grain_video_path}")
            
            # Normalize path for cross-platform compatibility
            grain_video_path_normalized = grain_video_path.replace('\\', '/')
            
            # Return special marker + instructions for video overlay
            # FFmpegCommandBuilder will handle this specially
            # Use | delimiter to avoid conflicts with Windows drive letters (C:)
            return f"VIDEO_OVERLAY|{grain_video_path_normalized}|{opacity}|{total_duration}"
        
        
        elif effect == "Tilt":
            # Tilt/rotation with adjustable intensity
            # Scale tilt angle based on intensity: 0-100 maps to 0-5 degrees

            # Tilt angle: subtle at low intensity, more dramatic at high
            # Range: 0.3° (barely noticeable) to 5° (quite dramatic)
            tilt_angle = 0.3 + (intensity / 100.0) * 4.7

            logger.info(f"Adding Tilt effect - Intensity: {intensity}%, Max Angle: {tilt_angle:.1f}°")

            # Pre-scale to avoid black edges during rotation
            scale_factor = 1.15  # Scale up 15% to ensure no black edges
            return (
                f"scale={int(1920*scale_factor)}:{int(1080*scale_factor)}:flags=lanczos,"
                f"rotate='{tilt_angle}*PI/180*sin(t*0.5)':c=none,"
                f"crop=1920:1080:(iw-1920)/2:(ih-1080)/2"
            )

        elif effect == "Dynamic Tilt":
            # DYNAMIC TILT: Oscillating tilt + smooth zoom in/out animation
            # Creates dynamic movement with rotation

            # Tilt angle based on intensity: 0-100% maps to max tilt angle
            # At 0%: ±1° oscillation (very subtle)
            # At 50%: ±5.5° oscillation (medium - comfortable viewing)
            # At 100%: ±10° oscillation (dramatic but not excessive)
            max_tilt_angle = 1 + (intensity / 100.0) * 9  # Range: 1 to 10 degrees

            # Zoom range based on intensity
            # At 50%: zoom between 1.0x and 1.15x
            # At 100%: zoom between 1.0x and 1.30x
            max_zoom = 0.15 + (intensity / 100.0) * 0.15  # Range: 0.15 to 0.30

            logger.info(f"Adding Dynamic Tilt effect - Intensity: {intensity}%, Tilt: ±{max_tilt_angle:.1f}°, Zoom: 1.0x-{1.0+max_zoom:.2f}x")

            # Base scale factor to prevent black corners (1.3x for 20° rotation)
            base_scale = 1.3

            # Zoom formula: smooth sine wave completing one cycle over duration
            # zoom(t) = 1.0 + max_zoom * (0.5 - 0.5*cos(2*PI*t/duration))
            # This gives: t=0: 1.0x, t=duration/2: 1.0+max_zoom, t=duration: 1.0x

            zoom_expr = f"1.0+{max_zoom}*(0.5-0.5*cos(2*PI*t/{total_duration}))"

            return (
                # Apply base scale + animated zoom
                f"scale='1920*{base_scale}*({zoom_expr})':'1080*{base_scale}*({zoom_expr})':flags=lanczos:eval=frame,"
                # Oscillating rotation between -max_tilt and +max_tilt degrees
                f"rotate='{max_tilt_angle}*PI/180*sin(t*0.5)':c=none,"
                # Crop to final 1920x1080
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