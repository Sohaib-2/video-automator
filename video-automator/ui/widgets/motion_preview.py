"""
Motion Effect Preview Widget
Shows animated previews of motion effects
"""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap


class MotionEffectPreview(QLabel):
    """Preview widget for motion effects with animation"""
    
    def __init__(self, effect_name: str, parent=None):
        """
        Initialize motion effect preview
        
        Args:
            effect_name: Name of the motion effect
            parent: Parent widget
        """
        super().__init__(parent)
        self.effect_name = effect_name
        self.setFixedSize(200, 113)  # 16:9 ratio thumbnail
        self.setStyleSheet("border: 2px solid #ccc; background-color: #f0f0f0;")
        self.setAlignment(Qt.AlignCenter)
        
        # Animation state
        self.animation_frame = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        
        self.preview_pixmap = None
        self.is_selected = False
        
    def load_preview(self, image_path: str):
        """Load image for preview"""
        pixmap = QPixmap(image_path)
        # Scale to fit
        self.preview_pixmap = pixmap.scaled(
            200, 113,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        self.update_animation()
        
    def start_animation(self):
        """Start animation preview"""
        self.animation_frame = 0
        self.timer.start(50)  # 20fps preview
        
    def stop_animation(self):
        """Stop animation preview"""
        self.timer.stop()
        self.animation_frame = 0
        
    def update_animation(self):
        """Update animation frame"""
        if not self.preview_pixmap:
            return
        
        # Create animated frame based on effect
        self.animation_frame = (self.animation_frame + 1) % 100
        progress = self.animation_frame / 100.0
        
        # Apply effect
        if self.effect_name == "Zoom In":
            scale = 1.0 + progress * 0.3  # Zoom from 1.0 to 1.3
            pixmap = self._apply_zoom(self.preview_pixmap, scale)
        elif self.effect_name == "Zoom Out":
            scale = 1.3 - progress * 0.3  # Zoom from 1.3 to 1.0
            pixmap = self._apply_zoom(self.preview_pixmap, scale)
        elif self.effect_name == "Pan Right":
            pixmap = self._apply_pan(self.preview_pixmap, progress, 'right')
        elif self.effect_name == "Pan Left":
            pixmap = self._apply_pan(self.preview_pixmap, progress, 'left')
        elif self.effect_name == "Ken Burns":
            scale = 1.0 + progress * 0.3
            pixmap = self._apply_zoom(self.preview_pixmap, scale)
        else:  # Static
            pixmap = self.preview_pixmap
        
        self.setPixmap(pixmap)
    
    def _apply_zoom(self, pixmap: QPixmap, scale: float) -> QPixmap:
        """Apply zoom effect to pixmap"""
        # Scale up
        scaled = pixmap.scaled(
            int(pixmap.width() * scale),
            int(pixmap.height() * scale),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # Crop to center
        x = (scaled.width() - 200) // 2
        y = (scaled.height() - 113) // 2
        return scaled.copy(x, y, 200, 113)
    
    def _apply_pan(self, pixmap: QPixmap, progress: float, direction: str) -> QPixmap:
        """Apply pan effect to pixmap"""
        # Scale up slightly for pan room
        scaled = pixmap.scaled(
            int(pixmap.width() * 1.2),
            int(pixmap.height() * 1.2),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        max_offset = scaled.width() - 200
        
        if direction == 'right':
            x = int(progress * max_offset)
        else:  # left
            x = int((1 - progress) * max_offset)
        
        y = (scaled.height() - 113) // 2
        return scaled.copy(x, y, 200, 113)
    
    def set_selected(self, selected: bool):
        """Set selection state"""
        self.is_selected = selected
        if selected:
            self.setStyleSheet("border: 3px solid #4CAF50; background-color: #e8f5e9;")
            self.start_animation()
        else:
            self.setStyleSheet("border: 2px solid #ccc; background-color: #f0f0f0;")
            self.stop_animation()
            self.update_animation()  # Show first frame