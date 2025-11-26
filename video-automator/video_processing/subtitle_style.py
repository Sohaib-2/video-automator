"""
Subtitle Style Builder
Creates FFmpeg subtitle styling with professional margins and safe caption boundaries
UPDATED: Industry-standard 10% side margins for perfect caption positioning
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class SubtitleStyleBuilder:
    """Builds FFmpeg ASS subtitle style strings with safe margins"""
    
    def __init__(self, settings: Dict):
        """
        Initialize subtitle style builder
        
        Args:
            settings: Dictionary containing style settings
        """
        self.settings = settings
    
    def build(self) -> str:
        """
        Build complete subtitle style string for FFmpeg
        
        Returns:
            ASS style format string
        """
        # Font settings - handle "Font Bold" format
        font = self.settings.get('font', 'Arial Bold')
        
        # Check if font name contains "Bold" and extract base font name
        if ' Bold' in font:
            font_base = font.replace(' Bold', '')
            is_bold = -1  # ASS uses -1 for bold
        else:
            font_base = font
            is_bold = 0
        
        font_safe = font_base.replace(',', '').replace("'", '').replace('"', '')
        font_size = self.settings.get('font_size', 48)
        
        logger.info(f"Using font: {font_safe} (Bold: {is_bold}), Size: {font_size}px for 1080p output")
        
        # Color conversion to ASS format
        text_color = self._convert_color(self.settings.get('text_color', '#FFFF00'))
        bg_color_hex = self.settings.get('bg_color', '#000000')
        
        # Background and outline settings
        has_background = self.settings.get('has_background', True)
        has_outline = self.settings.get('has_outline', not has_background)
        
        if has_background:
            # Background mode
            opacity_percent = self.settings.get('bg_opacity', 80)
            alpha = int((100 - opacity_percent) * 2.55)
            bg_color = self._convert_color(bg_color_hex, alpha)
            border_style = 4  # Background box
            outline_width = 0
            shadow_depth = 0
            outline_color = "&H00000000"
        else:
            # No background - check outline settings
            bg_color = "&HFF000000"  # Fully transparent
            
            if has_outline:
                outline_width = self.settings.get('outline_width', 3)
                outline_color_hex = self.settings.get('outline_color', '#000000')
                outline_color = self._convert_color(outline_color_hex)
                shadow_depth = self.settings.get('shadow_depth', 2)
            else:
                outline_width = 0
                outline_color = "&H00000000"
                shadow_depth = 0
            
            border_style = 1  # Outline + shadow
        
        # Position settings
        caption_pos = self.settings.get('caption_position', {'x': 0.5, 'y': 0.9})
        x_norm = caption_pos['x']
        y_norm = caption_pos['y']
        
        # ============================================================================
        # INDUSTRY-STANDARD SAFE MARGINS - 10% ON EACH SIDE
        # ============================================================================
        # For 1920x1080 video:
        # - 10% left margin = 192px
        # - 10% right margin = 192px
        # - Caption area = 1536px (80% of screen width)
        #
        # This ensures:
        # ✅ Text never touches edges
        # ✅ Safe for all devices/TVs (overscan protection)
        # ✅ Professional look matching YouTube, Netflix, broadcast standards
        # ✅ Natural wrapping at 2-3 lines for long captions
        # ============================================================================
        
        SCREEN_WIDTH = 1920
        MINIMUM_SIDE_MARGIN_PERCENT = 0.10  # 10% minimum on each side
        
        # Calculate absolute minimum margin in pixels
        min_side_margin_px = int(SCREEN_WIDTH * MINIMUM_SIDE_MARGIN_PERCENT)  # 192px
        
        # Apply minimum margins (override user setting if too small)
        margin_l = min_side_margin_px  # Always 192px (10%)
        margin_r = min_side_margin_px  # Always 192px (10%)
        
        # Maximum caption width is now guaranteed: 1920 - 192 - 192 = 1536px (80%)
        max_caption_width = SCREEN_WIDTH - margin_l - margin_r
        
        logger.info(f"🎯 SAFE MARGINS APPLIED:")
        logger.info(f"   Left margin:  {margin_l}px ({MINIMUM_SIDE_MARGIN_PERCENT*100:.0f}%)")
        logger.info(f"   Right margin: {margin_r}px ({MINIMUM_SIDE_MARGIN_PERCENT*100:.0f}%)")
        logger.info(f"   Caption area: {max_caption_width}px ({(max_caption_width/SCREEN_WIDTH)*100:.0f}% of screen)")
        logger.info(f"   ✅ Text will NEVER touch screen edges!")
        
        # Determine vertical alignment based on position
        if y_norm < 0.33:
            # Top alignment
            v_align_base = 6
            margin_v = int(y_norm * 1080)
        elif y_norm > 0.66:
            # Bottom alignment (default)
            v_align_base = 0
            margin_v = int((1.0 - y_norm) * 1080)
        else:
            # Middle alignment
            v_align_base = 3
            margin_v = int((0.5 - y_norm) * 1080)
        
        # Always use center alignment for best wrapping behavior
        h_align = 2  # Center horizontal alignment
        alignment = v_align_base + h_align
        
        # Build style string with safe margins and smart wrapping
        style = (
            f"FontName={font_safe},"
            f"FontSize={font_size},"
            f"Bold={is_bold},"
            f"PrimaryColour={text_color},"
            f"BackColour={bg_color},"
            f"OutlineColour={outline_color},"
            f"BorderStyle={border_style},"
            f"Outline={outline_width},"
            f"Shadow={shadow_depth},"
            f"MarginV={margin_v},"
            f"MarginL={margin_l},"
            f"MarginR={margin_r},"
            f"Alignment={alignment},"
            f"WrapStyle=2"  # Smart wrapping at word boundaries
        )
        
        # Log detailed style info
        logger.info(f"Caption style: Pos=({x_norm:.2f},{y_norm:.2f}), Align={alignment}, MarginV={margin_v}px")
        logger.info(f"Colors: Text={text_color}, BG={bg_color}, Outline={outline_color}, HasBG={has_background}")
        logger.info(f"Border: Style={border_style}, Outline={outline_width}px, Shadow={shadow_depth}px, Bold={is_bold}")
        logger.info(f"Wrapping: WrapStyle=2 (smart word-boundary wrapping enabled)")
        
        return style
    
    def _convert_color(self, hex_color: str, alpha: int = 0) -> str:
        """
        Convert hex color to ASS format (&HAABBGGRR)
        
        Args:
            hex_color: Hex color string (e.g., '#FFFF00')
            alpha: Alpha value (0-255, 0=opaque, 255=transparent)
            
        Returns:
            ASS format color string
        """
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"