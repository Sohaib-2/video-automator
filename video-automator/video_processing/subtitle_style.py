"""
Subtitle Style Builder - IMPROVED
Creates FFmpeg subtitle styling with:
- 10% safe margins (industry standard)
- Smart multi-line wrapping (safety net for long words)
- Optimal caption boundaries for 1080p video
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class SubtitleStyleBuilder:
    """Builds FFmpeg ASS subtitle style with intelligent wrapping boundaries"""

    def __init__(self, settings: Dict, resolution: tuple = (1920, 1080)):
        """
        Initialize subtitle style builder

        Args:
            settings: Dictionary containing style settings
            resolution: Output resolution as tuple (width, height)
        """
        self.settings = settings
        self.resolution = resolution

    def build(self) -> str:
        """
        Build complete subtitle style string for FFmpeg with wrapping safety net

        Returns:
            ASS style format string with optimal wrapping configuration
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

        # Italic setting
        is_italic = -1 if self.settings.get('italic_text', False) else 0

        logger.info(f"Font: {font_safe} (Bold: {is_bold}, Italic: {is_italic}), Size: {font_size}px")
        
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
        caption_pos = self.settings.get('caption_position', {'x': 0.5, 'y': 0.95})
        x_norm = caption_pos['x']
        y_norm = caption_pos['y']
        
        # ============================================================================
        # INDUSTRY-STANDARD SAFE MARGINS - 10% EACH SIDE
        # ============================================================================
        # For any resolution:
        # - Left margin:  10% of width
        # - Right margin: 10% of width
        # - Caption area: 80% of screen width
        #
        # This ensures:
        # ✅ Text never touches edges
        # ✅ Safe for all devices/TVs (overscan protection)
        # ✅ Professional look (YouTube, Netflix standard)
        # ✅ Natural wrapping at 2-3 lines for long captions
        # ============================================================================

        SCREEN_WIDTH, SCREEN_HEIGHT = self.resolution
        MINIMUM_SIDE_MARGIN_PERCENT = 0.10  # 10% minimum on each side

        # Calculate absolute minimum margin in pixels
        min_side_margin_px = int(SCREEN_WIDTH * MINIMUM_SIDE_MARGIN_PERCENT)

        # Apply minimum margins
        margin_l = min_side_margin_px
        margin_r = min_side_margin_px

        # Maximum caption width
        max_caption_width = SCREEN_WIDTH - margin_l - margin_r
        
        logger.info(f"🎯 SAFE MARGINS:")
        logger.info(f"   Left:  {margin_l}px ({MINIMUM_SIDE_MARGIN_PERCENT*100:.0f}%)")
        logger.info(f"   Right: {margin_r}px ({MINIMUM_SIDE_MARGIN_PERCENT*100:.0f}%)")
        logger.info(f"   Caption area: {max_caption_width}px ({(max_caption_width/SCREEN_WIDTH)*100:.0f}%)")
        logger.info(f"   ✅ Invisible boundary enforced - text will auto-wrap!")
        
        # Determine vertical alignment based on position
        if y_norm < 0.33:
            # Top alignment
            v_align_base = 6
            margin_v = int(y_norm * SCREEN_HEIGHT)
        elif y_norm > 0.66:
            # Bottom alignment (default)
            v_align_base = 0
            margin_v = int((1.0 - y_norm) * SCREEN_HEIGHT)
        else:
            # Middle alignment
            v_align_base = 3
            margin_v = int((0.5 - y_norm) * SCREEN_HEIGHT)
        
        # Always use center alignment for best wrapping behavior
        h_align = 2  # Center horizontal alignment
        alignment = v_align_base + h_align
        
        # ============================================================================
        # WRAPPING CONFIGURATION - The Safety Net!
        # ============================================================================
        # WrapStyle=2: Smart wrapping at word boundaries
        #   - Text longer than (screen_width - margin_l - margin_r) will automatically
        #     wrap to the next line
        #   - Wraps at spaces, not mid-word
        #   - This is the SAFETY NET for any captions that slip through splitting
        # ============================================================================
        
        wrap_style = 2  # Smart word-boundary wrapping (CRITICAL!)
        
        # Build style string with optimal wrapping
        style = (
            f"FontName={font_safe},"
            f"FontSize={font_size},"
            f"Bold={is_bold},"
            f"Italic={is_italic},"
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
            f"WrapStyle={wrap_style}"  # SAFETY NET: Auto-wrap at invisible boundary!
        )
        
        # Detailed logging
        logger.info(f"Caption position: ({x_norm:.2f}, {y_norm:.2f}), Alignment: {alignment}")
        logger.info(f"Wrapping: WrapStyle={wrap_style} (smart auto-wrap enabled)")
        logger.info(f"Colors: Text={text_color}, BG={bg_color}, HasBG={has_background}")
        logger.info(f"Border: Style={border_style}, Outline={outline_width}px, Shadow={shadow_depth}px")
        logger.info("✅ HYBRID SYSTEM: Pre-split captions + FFmpeg auto-wrap safety net")
        
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