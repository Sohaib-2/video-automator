"""
Subtitle Style Builder
Creates FFmpeg subtitle styling with support for fonts, colors, backgrounds, and outlines
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class SubtitleStyleBuilder:
    """Builds FFmpeg ASS subtitle style strings"""
    
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
        # Font settings
        font = self.settings.get('font', 'Arial Bold')
        font_safe = font.replace(',', '').replace("'", '').replace('"', '')
        font_size = self.settings.get('font_size', 48)
        
        logger.info(f"Using font size: {font_size}px for 1080p output")
        
        # Color conversion to ASS format
        text_color = self._convert_color(self.settings.get('text_color', '#FFFF00'))
        bg_color_hex = self.settings.get('bg_color', '#000000')
        
        # Background and outline settings
        has_background = self.settings.get('has_background', True)
        has_outline = self.settings.get('has_outline', not has_background)  # Default: outline when no bg
        
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
        
        # Vertical margin
        margin_v = int((1.0 - y_norm) * 1080)
        
        # Caption width boundaries
        caption_max_width_percent = self.settings.get('caption_width_percent', 0.80)
        side_margin = int((1920 * (1 - caption_max_width_percent)) / 2)
        
        # Horizontal alignment and margins
        if x_norm < 0.33:
            h_align = 1  # Left
            margin_l = int(x_norm * 1920)
            margin_r = side_margin
        elif x_norm > 0.66:
            h_align = 3  # Right
            margin_l = side_margin
            margin_r = int((1.0 - x_norm) * 1920)
        else:
            h_align = 2  # Center
            margin_l = side_margin
            margin_r = side_margin
        
        # Vertical alignment
        if y_norm < 0.33:
            alignment = h_align + 6  # Top
        elif y_norm < 0.66:
            alignment = h_align + 3  # Middle
        else:
            alignment = h_align  # Bottom
        
        # Build style string
        style = (
            f"FontName={font_safe},"
            f"FontSize={font_size},"
            f"PrimaryColour={text_color},"
            f"BackColour={bg_color},"
            f"OutlineColour={outline_color},"
            f"BorderStyle={border_style},"
            f"Outline={outline_width},"
            f"Shadow={shadow_depth},"
            f"MarginV={margin_v},"
            f"MarginL={margin_l},"
            f"MarginR={margin_r},"
            f"Alignment={alignment}"
        )
        
        # Log style details
        logger.info(f"Subtitle style: Pos=({x_norm:.2f},{y_norm:.2f}), Align={alignment}, MarginV={margin_v}px")
        logger.info(f"Caption boundaries: MarginL={margin_l}px, MarginR={margin_r}px (max width: {1920-margin_l-margin_r}px)")
        logger.info(f"Colors: Text={text_color}, BG={bg_color}, Outline={outline_color}, HasBG={has_background}")
        logger.info(f"Border: Style={border_style}, Outline={outline_width}px, Shadow={shadow_depth}px")
        
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