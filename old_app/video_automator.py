import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, 
                             QProgressBar, QComboBox, QColorDialog, QDialog,
                             QGridLayout, QSpinBox, QFileDialog, QListWidgetItem,
                             QFrame, QMessageBox, QGraphicsView, QGraphicsScene,
                             QGraphicsPixmapItem, QGraphicsRectItem, QSlider,
                             QGraphicsTextItem, QCheckBox, QGroupBox, QLineEdit)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRectF, QTimer, QPointF, QSize
from PyQt5.QtGui import (QFont, QColor, QPalette, QPixmap, QPen, QBrush, 
                         QPainter, QTransform, QImage)

# Import video processor
from old_app.video_processor import VideoProcessor, BatchRenderer, check_ffmpeg_installed, check_gpu_available

class DraggableCaptionItem(QGraphicsTextItem):
    """Draggable caption text item for preview"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFlag(QGraphicsTextItem.ItemIsMovable)
        self.setFlag(QGraphicsTextItem.ItemIsSelectable)
        self.setFlag(QGraphicsTextItem.ItemSendsGeometryChanges)
        self.setCursor(Qt.OpenHandCursor)
        
    def mousePressEvent(self, event):
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)


class ImageCropView(QGraphicsView):
    """Interactive image crop/zoom view for 16:9 ratio with draggable image"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Setup view - FIXED: Remove ScrollHandDrag to allow image dragging
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)  # FIXED: Don't drag view
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Image item
        self.image_item = None
        self.original_pixmap = None
        
        # 16:9 crop frame (1920x1080) - center of scene
        self.crop_frame = QGraphicsRectItem(0, 0, 1920, 1080)
        self.crop_frame.setPen(QPen(QColor(255, 0, 0, 200), 4, Qt.SolidLine))
        self.crop_frame.setBrush(QBrush(Qt.transparent))
        self.crop_frame.setZValue(100)  # Always on top
        self.scene.addItem(self.crop_frame)
        
        # Zoom level
        self.zoom_level = 1.0
        self.min_zoom = 0.3
        self.max_zoom = 5.0
        
        # Caption overlay
        self.caption_item = None
        
    def resizeEvent(self, event):
        """Maintain 16:9 aspect ratio on resize"""
        super().resizeEvent(event)
        # FIXED: Always fit to show entire crop frame in 16:9
        if self.crop_frame:
            self.fitInView(self.crop_frame, Qt.KeepAspectRatio)
        
    def load_image(self, image_path: str):
        """Load image into view and auto-fit to 16:9 frame"""
        self.original_pixmap = QPixmap(image_path)
        
        if self.image_item:
            self.scene.removeItem(self.image_item)
        
        self.image_item = QGraphicsPixmapItem(self.original_pixmap)
        self.scene.addItem(self.image_item)
        self.image_item.setZValue(-1)  # Behind crop frame
        
        # FIXED: Make image draggable!
        self.image_item.setFlag(QGraphicsPixmapItem.ItemIsMovable, True)
        self.image_item.setFlag(QGraphicsPixmapItem.ItemIsSelectable, True)
        self.image_item.setCursor(Qt.OpenHandCursor)
        
        # NEW: Auto-fit to fill 16:9 frame perfectly
        self.auto_fit_to_frame()
        
        # FIXED: Fit view to show crop frame properly
        self.fitInView(self.crop_frame, Qt.KeepAspectRatio)

        
    def center_image(self):
        """Center image under crop frame"""
        if self.image_item:
            img_rect = self.image_item.boundingRect()
            crop_rect = self.crop_frame.rect()
            
            # Center position
            x = crop_rect.center().x() - (img_rect.width() * self.zoom_level) / 2
            y = crop_rect.center().y() - (img_rect.height() * self.zoom_level) / 2
            
            self.image_item.setPos(x, y)
    
    def set_zoom(self, zoom: float):
        """Set zoom level"""
        old_zoom = self.zoom_level
        self.zoom_level = max(self.min_zoom, min(self.max_zoom, zoom))
        
        if self.image_item:
            # Get current center position
            img_center_x = self.image_item.x() + (self.image_item.boundingRect().width() * old_zoom) / 2
            img_center_y = self.image_item.y() + (self.image_item.boundingRect().height() * old_zoom) / 2
            
            # Scale image
            self.image_item.setScale(self.zoom_level)
            
            # Recenter around same point
            new_x = img_center_x - (self.image_item.boundingRect().width() * self.zoom_level) / 2
            new_y = img_center_y - (self.image_item.boundingRect().height() * self.zoom_level) / 2
            self.image_item.setPos(new_x, new_y)
    
    def zoom_in(self):
        """Zoom in by 10%"""
        new_zoom = self.zoom_level * 1.1
        self.set_zoom(new_zoom)
        return self.zoom_level
    
    def zoom_out(self):
        """Zoom out by 10%"""
        new_zoom = self.zoom_level / 1.1
        self.set_zoom(new_zoom)
        return self.zoom_level
    
    def reset_view(self):
        """Reset zoom and center image using auto-fit"""
        zoom = self.auto_fit_to_frame()
        return zoom
            
    def get_crop_region(self):
        """Get the crop region in original image coordinates"""
        if not self.image_item:
            return None
        
        # Get crop frame position in scene
        crop_rect = self.crop_frame.sceneBoundingRect()
        
        # Get image position and scale
        img_pos = self.image_item.pos()
        img_scale = self.image_item.scale()
        
        # Get original image dimensions
        orig_width = self.image_item.boundingRect().width()
        orig_height = self.image_item.boundingRect().height()
        
        # Calculate crop in original image coordinates
        x = (crop_rect.x() - img_pos.x()) / img_scale
        y = (crop_rect.y() - img_pos.y()) / img_scale
        w = crop_rect.width() / img_scale
        h = crop_rect.height() / img_scale
        
        # FIXED: Clamp values to valid ranges (must be within image boundaries)
        x = max(0, min(x, orig_width - 1))
        y = max(0, min(y, orig_height - 1))
        
        # Ensure crop doesn't exceed image boundaries
        if x + w > orig_width:
            w = orig_width - x
        if y + h > orig_height:
            h = orig_height - y
        
        # Ensure minimum size (at least 100x100)
        w = max(100, w)
        h = max(100, h)
        
        return {
            'x': int(x),
            'y': int(y),
            'width': int(w),
            'height': int(h)
        }
    
    def add_caption(self, text: str, font: QFont, color: QColor, bg_color: QColor, bg_opacity: int, has_background: bool):
        """Add draggable caption to preview"""
        if self.caption_item:
            self.scene.removeItem(self.caption_item)
        
        self.caption_item = DraggableCaptionItem(text)
        self.caption_item.setFont(font)
        self.caption_item.setDefaultTextColor(color)
        
        # FIXED: Support no background option
        if has_background:
            # Create HTML with background
            html = f"""
            <div style='background-color: rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, {bg_opacity/100.0});
                        padding: 10px; border-radius: 5px;'>
                <span style='color: {color.name()}; font-family: {font.family()}; font-size: {font.pointSize()}pt; font-weight: bold;'>
                    {text}
                </span>
            </div>
            """
        else:
            # No background - text with shadow
            html = f"""
            <span style='color: {color.name()}; font-family: {font.family()}; font-size: {font.pointSize()}pt; font-weight: bold;
                         text-shadow: 2px 2px 4px rgba(0,0,0,0.8);'>
                {text}
            </span>
            """
        
        self.caption_item.setHtml(html)
        
        self.scene.addItem(self.caption_item)
        self.caption_item.setZValue(200)  # On top of everything
        
        # Position at bottom center by default
        caption_rect = self.caption_item.boundingRect()
        crop_rect = self.crop_frame.rect()
        x = crop_rect.center().x() - caption_rect.width() / 2
        y = crop_rect.bottom() - caption_rect.height() - 80
        self.caption_item.setPos(x, y)
    
    def get_caption_position(self):
        """Get caption position relative to crop frame (normalized 0-1)"""
        if not self.caption_item:
            return {'x': 0.5, 'y': 0.9}  # Default bottom center
        
        caption_pos = self.caption_item.pos()
        caption_rect = self.caption_item.boundingRect()
        crop_rect = self.crop_frame.rect()
        
        # Get center point of caption
        caption_center_x = caption_pos.x() + caption_rect.width() / 2
        caption_center_y = caption_pos.y() + caption_rect.height() / 2
        
        # Normalize to 0-1 range
        x = (caption_center_x - crop_rect.x()) / crop_rect.width()
        y = (caption_center_y - crop_rect.y()) / crop_rect.height()
        
        # Clamp to valid range
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        
        return {'x': x, 'y': y}
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        if self.image_item:
            # Zoom in/out
            zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            new_zoom = self.zoom_level * zoom_factor
            self.set_zoom(new_zoom)

    def auto_fit_to_frame(self):
        """
        Automatically fit image to fill 16:9 crop frame
        Calculates optimal zoom and position to fill frame completely
        """
        if not self.image_item or not self.original_pixmap:
            return 1.0
        
        # Get image and frame dimensions
        img_w = self.original_pixmap.width()
        img_h = self.original_pixmap.height()
        frame_w = self.crop_frame.rect().width()  # 1920
        frame_h = self.crop_frame.rect().height()  # 1080
        
        # Calculate zoom needed to fill frame completely
        zoom_x = frame_w / img_w
        zoom_y = frame_h / img_h
        
        # Use LARGER zoom to ensure frame is completely filled (no gaps)
        optimal_zoom = max(zoom_x, zoom_y)
        
        # Clamp to valid range
        optimal_zoom = max(self.min_zoom, min(self.max_zoom, optimal_zoom))
        
        # Apply zoom
        self.zoom_level = optimal_zoom
        self.image_item.setScale(optimal_zoom)
        
        # Center image under frame
        scaled_img_w = img_w * optimal_zoom
        scaled_img_h = img_h * optimal_zoom
        
        x = frame_w / 2 - scaled_img_w / 2
        y = frame_h / 2 - scaled_img_h / 2
        
        self.image_item.setPos(x, y)
        
        print(f"[AUTO-FIT] zoom={optimal_zoom:.2f}x, pos=({x:.1f},{y:.1f})")
        
        return optimal_zoom


class MotionEffectPreview(QLabel):
    """Preview widget for motion effects"""
    
    def __init__(self, effect_name: str, parent=None):
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
        self.preview_pixmap = pixmap.scaled(200, 113, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
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


class EnhancedSettingsDialog(QDialog):
    """Enhanced settings dialog with live preview"""
    
    def __init__(self, parent=None, current_settings=None, sample_folder=None):
        super().__init__(parent)
        self.setWindowTitle("Video Settings - Setup & Preview")
        self.setModal(True)
        self.resize(1400, 850)
        
        # Default settings
        default_settings = {
            'font': 'Arial Bold',
            'font_size': 48,
            'text_color': '#FFFF00',
            'bg_color': '#000000',
            'bg_opacity': 80,
            'has_background': True,
            'position': 'Bottom Center',
            'motion_effect': 'Zoom In',
            'crop_settings': None,
            'caption_position': {'x': 0.5, 'y': 0.9},
            'preview_text': 'Sample Caption Text'
        }
        
        # FIXED: Properly merge current settings with defaults
        if current_settings:
            self.settings = {**default_settings, **current_settings}
            print(f"[DEBUG] Loaded settings with crop: {self.settings.get('crop_settings')}")
            print(f"[DEBUG] Loaded caption position: {self.settings.get('caption_position')}")
            print(f"[DEBUG] Loaded motion effect: {self.settings.get('motion_effect')}")
        else:
            self.settings = default_settings
            print("[DEBUG] Using default settings (no previous settings found)")
        
        self.sample_folder = sample_folder
        self.sample_image = None
        
        # Find sample image
        if sample_folder:
            from old_app.video_processor import VideoProcessor
            processor = VideoProcessor(self.settings)
            files = processor.detect_files_in_folder(sample_folder)
            if files['images']:
                self.sample_image = files['images'][0]
        
        self.init_ui()
        
        # Load preview if available
        if self.sample_image:
            self.load_preview()
            
            # FIXED: Show indicator if settings were loaded from previous save
            if current_settings and current_settings.get('crop_settings'):
                # Settings were previously saved
                self.setWindowTitle("Video Settings - Setup & Preview (Previous settings loaded)")
        else:
            # No sample image
            self.setWindowTitle("Video Settings - Setup & Preview (No preview available)")
    
    def init_ui(self):
        layout = QHBoxLayout()
        
        # Left side - Preview
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)
        
        preview_label = QLabel("📺 Live Preview - 16:9 Video Output")
        preview_label.setFont(QFont('Arial', 14, QFont.Bold))
        preview_label.setStyleSheet("color: #1976D2; padding: 5px;")
        left_panel.addWidget(preview_label)
        
        # Image crop view
        self.crop_view = ImageCropView()
        self.crop_view.setMinimumSize(800, 450)  # 16:9 ratio
        self.crop_view.setStyleSheet("border: 2px solid #ddd; background-color: #fafafa;")
        left_panel.addWidget(self.crop_view, stretch=4)
        
        # Zoom controls with +/- buttons
        zoom_group = QGroupBox("🔍 Zoom & Position Controls")
        zoom_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        zoom_layout = QVBoxLayout()
        
        zoom_buttons_layout = QHBoxLayout()
        zoom_buttons_layout.addWidget(QLabel("Zoom:"))
        
        self.zoom_out_btn = QPushButton("➖")
        self.zoom_out_btn.setFixedSize(50, 50)
        self.zoom_out_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                font-weight: bold;
                background-color: #f44336;
                color: white;
                border-radius: 25px;
                border: none;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self.zoom_out_btn.clicked.connect(self.on_zoom_out)
        zoom_buttons_layout.addWidget(self.zoom_out_btn)
        
        self.zoom_label = QLabel("1.0x")
        self.zoom_label.setMinimumWidth(80)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setStyleSheet("font-weight: bold; font-size: 18px; color: #1976D2;")
        zoom_buttons_layout.addWidget(self.zoom_label)
        
        self.zoom_in_btn = QPushButton("➕")
        self.zoom_in_btn.setFixedSize(50, 50)
        self.zoom_in_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                font-weight: bold;
                background-color: #4CAF50;
                color: white;
                border-radius: 25px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #388E3C;
            }
        """)
        self.zoom_in_btn.clicked.connect(self.on_zoom_in)
        zoom_buttons_layout.addWidget(self.zoom_in_btn)
        
        # Reset button
        reset_btn = QPushButton("🔄 Reset")
        reset_btn.setFixedSize(80, 50)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        reset_btn.clicked.connect(self.on_reset_view)
        autofit_btn = QPushButton("📐 Auto-Fit")
        autofit_btn.setFixedSize(100, 50)
        autofit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        autofit_btn.clicked.connect(self.on_auto_fit)
        zoom_buttons_layout.addWidget(autofit_btn)
        zoom_buttons_layout.addWidget(reset_btn)
        
        zoom_buttons_layout.addStretch()
        zoom_layout.addLayout(zoom_buttons_layout)
        
        # Instructions
        instructions = QLabel(
            "💡 <b>How to use:</b><br>"
            "• Drag the <b>image</b> to reposition it<br>"
            "• Use <b>+/- buttons</b> or <b>mouse wheel</b> to zoom<br>"
            "• Drag the <b>caption</b> to change its position<br>"
            "• Red frame shows final 16:9 video output"
        )
        instructions.setStyleSheet("color: #666; font-size: 11px; padding: 8px; background-color: #fffde7; border-radius: 5px;")
        instructions.setWordWrap(True)
        zoom_layout.addWidget(instructions)
        
        zoom_group.setLayout(zoom_layout)
        left_panel.addWidget(zoom_group)
        
        # Motion effects
        effects_label = QLabel("🎬 Motion Effects")
        effects_label.setFont(QFont('Arial', 12, QFont.Bold))
        effects_label.setStyleSheet("color: #1976D2;")
        left_panel.addWidget(effects_label)
        
        self.effect_previews = {}
        effects_layout = QHBoxLayout()
        effects = ["Static", "Zoom In", "Zoom Out", "Pan Right", "Pan Left"]
        
        for effect in effects:
            preview = MotionEffectPreview(effect)
            preview.mousePressEvent = lambda e, eff=effect: self.select_effect(eff)
            self.effect_previews[effect] = preview
            
            container = QVBoxLayout()
            container.addWidget(preview)
            label = QLabel(effect)
            label.setAlignment(Qt.AlignCenter)
            label.setFont(QFont('Arial', 9, QFont.Bold))
            container.addWidget(label)
            
            effects_layout.addLayout(container)
        
        left_panel.addLayout(effects_layout)
        
        # Right side - Settings
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)
        
        settings_title = QLabel("⚙️ Caption Settings")
        settings_title.setFont(QFont('Arial', 14, QFont.Bold))
        settings_title.setStyleSheet("color: #1976D2; padding: 5px;")
        right_panel.addWidget(settings_title)
        
        # Settings grid
        grid = QGridLayout()
        grid.setSpacing(15)
        
        row = 0
        
        # Font
        grid.addWidget(QLabel("Font:"), row, 0)
        self.font_combo = QComboBox()
        fonts = ['Arial', 'Arial Bold', 'Helvetica', 'Roboto', 'Montserrat', 
                 'Open Sans', 'Lato', 'Poppins', 'Oswald', 'Raleway']
        self.font_combo.addItems(fonts)
        self.font_combo.setCurrentText(self.settings['font'])
        self.font_combo.currentTextChanged.connect(self.update_preview)
        grid.addWidget(self.font_combo, row, 1)
        row += 1
        
        # Font size
        grid.addWidget(QLabel("Font Size:"), row, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(20, 120)
        self.font_size_spin.setValue(self.settings['font_size'])
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.valueChanged.connect(self.update_preview)
        grid.addWidget(self.font_size_spin, row, 1)
        row += 1
        
        # Text color
        grid.addWidget(QLabel("Text Color:"), row, 0)
        self.text_color_btn = QPushButton(self.settings['text_color'])
        self.text_color_btn.setStyleSheet(f"background-color: {self.settings['text_color']}; color: white; font-weight: bold;")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        grid.addWidget(self.text_color_btn, row, 1)
        row += 1
        
        # Text color presets
        grid.addWidget(QLabel("Presets:"), row, 0)
        text_preset_layout = QHBoxLayout()
        text_colors = [('#FFFFFF', 'White'), ('#000000', 'Black'), ('#FF0000', 'Red'), 
                      ('#0000FF', 'Blue'), ('#FFFF00', 'Yellow'), ('#00FF00', 'Green')]
        for color, name in text_colors:
            btn = QPushButton()
            btn.setFixedSize(35, 35)
            btn.setToolTip(name)
            btn.setStyleSheet(f"background-color: {color}; border: 2px solid #999; border-radius: 3px;")
            btn.clicked.connect(lambda checked, c=color: self.set_text_color(c))
            text_preset_layout.addWidget(btn)
        text_preset_layout.addStretch()
        grid.addLayout(text_preset_layout, row, 1)
        row += 1
        
        # FIXED: Add "Use Background" checkbox with saved state
        grid.addWidget(QLabel("Background:"), row, 0)
        self.has_bg_checkbox = QCheckBox("Enable Background")
        # FIXED: Load saved state
        saved_has_bg = self.settings.get('has_background', True)
        self.has_bg_checkbox.setChecked(saved_has_bg)
        self.has_bg_checkbox.stateChanged.connect(self.on_bg_toggle)
        grid.addWidget(self.has_bg_checkbox, row, 1)
        row += 1
        
        # Background color
        grid.addWidget(QLabel("BG Color:"), row, 0)
        self.bg_color_btn = QPushButton(self.settings['bg_color'])
        self.bg_color_btn.setStyleSheet(f"background-color: {self.settings['bg_color']}; color: white; font-weight: bold;")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        # FIXED: Set enabled state based on checkbox
        self.bg_color_btn.setEnabled(saved_has_bg)
        grid.addWidget(self.bg_color_btn, row, 1)
        row += 1
        
        # Background opacity
        grid.addWidget(QLabel("BG Opacity:"), row, 0)
        opacity_layout = QHBoxLayout()
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(self.settings['bg_opacity'])
        self.opacity_spin.setSuffix(" %")
        self.opacity_spin.valueChanged.connect(self.update_preview)
        # FIXED: Set enabled state based on checkbox
        self.opacity_spin.setEnabled(saved_has_bg)
        opacity_layout.addWidget(self.opacity_spin)
        grid.addLayout(opacity_layout, row, 1)
        row += 1
        
        right_panel.addLayout(grid)
        
        # Preview sample text input
        sample_group = QGroupBox("📝 Preview Text")
        sample_layout = QVBoxLayout()
        # FIXED: Load saved preview text if available
        preview_text = self.settings.get('preview_text', 'Sample Caption Text')
        self.sample_text_input = QLineEdit(preview_text)
        self.sample_text_input.textChanged.connect(self.update_preview)
        self.sample_text_input.setPlaceholderText("Type preview text here...")
        sample_layout.addWidget(self.sample_text_input)
        sample_group.setLayout(sample_layout)
        right_panel.addWidget(sample_group)
        
        right_panel.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("✅ Save Settings")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 15px;
                font-weight: bold;
                font-size: 14px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 15px;
                font-size: 14px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        right_panel.addLayout(button_layout)
        
        # Add panels to main layout
        layout.addLayout(left_panel, stretch=3)
        layout.addLayout(right_panel, stretch=2)
        
        self.setLayout(layout)
    
    def load_preview(self):
        """Load preview image and setup view with saved settings"""
        if self.sample_image:
            # Load image into crop view
            self.crop_view.load_image(self.sample_image)
            
            # FIXED: Apply saved crop settings if available
            crop_settings = self.settings.get('crop_settings', None)
            if crop_settings:
                # Calculate zoom and position from crop settings
                self.apply_crop_settings_to_preview(crop_settings)
            
            # Load into effect previews
            for preview in self.effect_previews.values():
                preview.load_preview(self.sample_image)
            
            # FIXED: Select current effect and highlight it
            current_effect = self.settings.get('motion_effect', 'Zoom In')
            self.select_effect(current_effect)
            
            # FIXED: Update caption preview with saved position
            self.update_preview()
            
            # FIXED: Apply saved caption position
            caption_pos = self.settings.get('caption_position', None)
            if caption_pos and self.crop_view.caption_item:
                # Convert normalized position back to scene coordinates
                crop_rect = self.crop_view.crop_frame.rect()
                x = crop_rect.x() + caption_pos['x'] * crop_rect.width()
                y = crop_rect.y() + caption_pos['y'] * crop_rect.height()
                
                # Adjust for caption center point
                caption_rect = self.crop_view.caption_item.boundingRect()
                x = x - caption_rect.width() / 2
                y = y - caption_rect.height() / 2
                
                self.crop_view.caption_item.setPos(x, y)
    
    def apply_crop_settings_to_preview(self, crop_settings: dict):
        """Apply saved crop settings to preview by calculating required zoom and position"""
        try:
            if not self.crop_view.image_item or not self.crop_view.original_pixmap:
                print("[DEBUG] Cannot apply crop: no image loaded")
                return
            
            # Get original image dimensions
            orig_width = self.crop_view.original_pixmap.width()
            orig_height = self.crop_view.original_pixmap.height()
            
            print(f"[DEBUG] Original image: {orig_width}x{orig_height}")
            
            # Get crop dimensions from settings
            crop_x = crop_settings.get('x', 0)
            crop_y = crop_settings.get('y', 0)
            crop_w = crop_settings.get('width', orig_width)
            crop_h = crop_settings.get('height', orig_height)
            
            print(f"[DEBUG] Applying crop: {crop_w}x{crop_h} at ({crop_x},{crop_y})")
            
            # Validate crop settings
            if crop_w <= 0 or crop_h <= 0:
                print(f"[DEBUG] Invalid crop dimensions: {crop_w}x{crop_h}")
                return
            
            # Get crop frame dimensions (1920x1080 in scene coordinates)
            crop_frame_rect = self.crop_view.crop_frame.rect()
            frame_w = crop_frame_rect.width()
            frame_h = crop_frame_rect.height()
            
            # Calculate required zoom
            # The crop region should fill the frame
            zoom_x = frame_w / crop_w
            zoom_y = frame_h / crop_h
            zoom = max(zoom_x, zoom_y)  # Use larger zoom to ensure full coverage
            
            print(f"[DEBUG] Calculated zoom: {zoom:.2f}x (from zoom_x={zoom_x:.2f}, zoom_y={zoom_y:.2f})")
            
            # Clamp zoom to valid range
            zoom = max(self.crop_view.min_zoom, min(self.crop_view.max_zoom, zoom))
            
            print(f"[DEBUG] Clamped zoom: {zoom:.2f}x")
            
            # Apply zoom
            self.crop_view.image_item.setScale(zoom)
            self.crop_view.zoom_level = zoom
            self.zoom_label.setText(f"{zoom:.1f}x")
            
            # Calculate image position
            # The crop region (crop_x, crop_y) should align with frame's top-left
            scaled_crop_x = crop_x * zoom
            scaled_crop_y = crop_y * zoom
            
            img_x = crop_frame_rect.x() - scaled_crop_x
            img_y = crop_frame_rect.y() - scaled_crop_y
            
            print(f"[DEBUG] Setting image position: ({img_x:.1f}, {img_y:.1f})")
            
            self.crop_view.image_item.setPos(img_x, img_y)
            
            print("[DEBUG] Crop settings applied successfully!")
            
        except Exception as e:
            print(f"[ERROR] Failed to apply crop settings: {e}")
            import traceback
            traceback.print_exc()
    
    def on_zoom_in(self):
        """Handle zoom in button"""
        zoom = self.crop_view.zoom_in()
        self.zoom_label.setText(f"{zoom:.1f}x")
    
    def on_zoom_out(self):
        """Handle zoom out button"""
        zoom = self.crop_view.zoom_out()
        self.zoom_label.setText(f"{zoom:.1f}x")
    
    def on_reset_view(self):
        """Reset view to default"""
        zoom = self.crop_view.reset_view()
        self.zoom_label.setText(f"{zoom:.1f}x")
    
    def on_bg_toggle(self):
        """Handle background toggle"""
        has_bg = self.has_bg_checkbox.isChecked()
        self.bg_color_btn.setEnabled(has_bg)
        self.opacity_spin.setEnabled(has_bg)
        self.settings['has_background'] = has_bg
        self.update_preview()
    
    def select_effect(self, effect_name: str):
        """Select motion effect"""
        # Update all previews
        for name, preview in self.effect_previews.items():
            preview.set_selected(name == effect_name)
        
        self.settings['motion_effect'] = effect_name
    
    def update_preview(self):
        """Update caption preview on image"""
        font = QFont(self.font_combo.currentText(), self.font_size_spin.value())
        text_color = QColor(self.settings['text_color'])
        bg_color = QColor(self.settings['bg_color'])
        bg_opacity = self.opacity_spin.value()
        has_bg = self.has_bg_checkbox.isChecked()
        
        # Get sample text
        sample_text = self.sample_text_input.text() or "Sample Caption Text"
        
        self.crop_view.add_caption(
            sample_text,
            font,
            text_color,
            bg_color,
            bg_opacity,
            has_bg
        )
    
    def choose_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.set_text_color(color.name())

    def on_auto_fit(self):
        """Handle auto-fit button click"""
        zoom = self.crop_view.auto_fit_to_frame()
        self.zoom_label.setText(f"{zoom:.1f}x")


    
    def set_text_color(self, color):
        self.settings['text_color'] = color
        self.text_color_btn.setText(color)
        self.text_color_btn.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold;")
        self.update_preview()
    
    def choose_bg_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings['bg_color'] = color.name()
            self.bg_color_btn.setText(color.name())
            self.bg_color_btn.setStyleSheet(f"background-color: {color.name()}; color: white; font-weight: bold;")
            self.update_preview()
    
    def save_and_close(self):
        """Save all settings and close"""
        # Get crop settings
        crop_region = self.crop_view.get_crop_region()
        caption_pos = self.crop_view.get_caption_position()
        
        # Validate crop settings
        if crop_region:
            if crop_region['x'] < 0 or crop_region['y'] < 0:
                reply = QMessageBox.question(
                    self,
                    "⚠️ Invalid Crop Position",
                    "The image position resulted in an invalid crop.\n\n"
                    "The crop has been adjusted to valid boundaries.\n"
                    f"Adjusted crop: {crop_region['width']}x{crop_region['height']} at ({crop_region['x']},{crop_region['y']})\n\n"
                    "Continue saving?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
        
        # Update all settings
        self.settings.update({
            'font': self.font_combo.currentText(),
            'font_size': self.font_size_spin.value(),
            'bg_opacity': self.opacity_spin.value(),
            'has_background': self.has_bg_checkbox.isChecked(),
            'crop_settings': crop_region,
            'caption_position': caption_pos,
            'preview_text': self.sample_text_input.text()  # FIXED: Save preview text
        })
        
        # Show success message
        QMessageBox.information(
            self,
            "✅ Settings Saved",
            f"Your settings have been saved successfully!\n\n"
            f"📝 Font: {self.settings['font']} ({self.settings['font_size']}px)\n"
            f"🎨 Caption Position: ({caption_pos['x']:.2f}, {caption_pos['y']:.2f})\n"
            f"🖼️ Crop: {crop_region['width']}x{crop_region['height']} at ({crop_region['x']},{crop_region['y']})\n"
            f"🎬 Motion: {self.settings['motion_effect']}\n\n"
            "These settings will be used for all videos."
        )
        
        self.accept()
    
    def get_settings(self):
        """Return all settings"""
        return self.settings


class VideoListItem(QWidget):
    """Custom widget for video queue items"""
    
    def __init__(self, folder_name, num_images=2, parent=None):
        super().__init__(parent)
        self.folder_name = folder_name
        self.num_images = num_images
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Folder name with image count
        name_label = QLabel(f"📁 {self.folder_name} ({self.num_images} image{'s' if self.num_images != 1 else ''})")
        name_label.setFont(QFont('Arial', 11, QFont.Bold))
        layout.addWidget(name_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ccc;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("⏳ Queued")
        self.status_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def update_progress(self, value, status="Processing..."):
        self.progress_bar.setValue(value)
        self.status_label.setText(f"⚙️ {status}")
    
    def set_complete(self):
        self.progress_bar.setValue(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4CAF50;
                border-radius: 5px;
                text-align: center;
                background-color: #e8f5e9;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        self.status_label.setText("✅ Complete!")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
    
    def set_error(self, error_msg="Error"):
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #f44336;
                border-radius: 5px;
                text-align: center;
                background-color: #ffebee;
            }
        """)
        self.status_label.setText(f"❌ {error_msg}")
        self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")


class RenderThread(QThread):
    """Thread for rendering videos without blocking UI"""
    
    # Signals
    progress_update = pyqtSignal(str, int, str)  # folder_path, progress, status
    render_complete = pyqtSignal(str, bool, str)  # folder_path, success, output_path
    all_complete = pyqtSignal()
    
    def __init__(self, video_folders, settings, max_workers=2):
        super().__init__()
        self.video_folders = video_folders
        self.settings = settings
        self.max_workers = max_workers
    
    def run(self):
        """Run the batch rendering process"""
        # Create progress callbacks
        progress_callbacks = {}
        for folder in self.video_folders:
            def make_callback(folder_path):
                def callback(progress, status):
                    self.progress_update.emit(folder_path, progress, status)
                return callback
            progress_callbacks[folder] = make_callback(folder)
        
        # Create batch renderer
        renderer = BatchRenderer(self.settings, max_workers=self.max_workers)
        
        # Process videos
        results = renderer.process_queue(
            self.video_folders,
            progress_callbacks
        )
        
        # Emit completion signals
        for folder_path, success, output_path in results:
            self.render_complete.emit(folder_path, success, output_path)
        
        self.all_complete.emit()


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎬 Video Automator - Batch Video Editor")
        self.setGeometry(100, 100, 1000, 750)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Load or create default settings
        self.config_file = os.path.join(os.path.expanduser('~'), '.video_automator_config.json')
        self.settings = self.load_settings()
        
        # Video queue
        self.video_queue = []
        
        # Rendering thread
        self.render_thread = None
        
        # Check if this is first run
        self.is_first_run = not os.path.exists(self.config_file)
        
        # Check system requirements
        self.check_system_requirements()
        
        self.init_ui()
        
        # Show first-time setup if needed
        if self.is_first_run:
            QTimer.singleShot(500, self.show_first_time_setup)
    
    def show_first_time_setup(self):
        """Show first-time setup wizard"""
        msg = QMessageBox()
        msg.setWindowTitle("🎉 Welcome to Video Automator!")
        msg.setIcon(QMessageBox.Information)
        msg.setText(
            "<h3>Welcome to Video Automator!</h3>"
            "<p>Let's configure your video settings.</p>"
            "<p>First, select a <b>sample video project folder</b> (with audio + images)<br>"
            "so you can preview and configure your captions and effects.</p>"
        )
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        
        if msg.exec_() == QMessageBox.Ok:
            # Ask user to select sample folder
            folder = QFileDialog.getExistingDirectory(self, "Select Sample Video Project Folder")
            if folder:
                # Validate it
                from old_app.video_processor import VideoProcessor
                processor = VideoProcessor(self.settings)
                is_valid, error_msg = processor.validate_folder(folder)
                
                if is_valid:
                    # Open enhanced settings with this sample
                    self.open_enhanced_settings(folder)
                else:
                    QMessageBox.warning(
                        self,
                        "Invalid Folder",
                        f"This folder is not a valid video project:\n\n{error_msg}\n\n"
                        "Please select a folder with audio + images."
                    )
    
    def check_system_requirements(self):
        """Check if FFmpeg and GPU are available"""
        if not check_ffmpeg_installed():
            QMessageBox.warning(
                self,
                "⚠️ FFmpeg Not Found",
                "FFmpeg is not installed or not in PATH.\n\n"
                "Please install FFmpeg to use this application.\n"
                "Visit: https://ffmpeg.org/download.html"
            )
        
        gpu_available = check_gpu_available()
        if gpu_available:
            print("✅ NVIDIA GPU detected - will use hardware acceleration")
        else:
            print("ℹ️  No NVIDIA GPU detected - will use CPU encoding")
    
    def load_settings(self):
        """Load settings from config file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
                    # Add new keys if missing
                    if 'has_background' not in settings:
                        settings['has_background'] = True
                    if 'caption_position' not in settings:
                        settings['caption_position'] = {'x': 0.5, 'y': 0.9}
                    return settings
            except:
                pass
        
        # Default settings
        return {
            'font': 'Arial Bold',
            'font_size': 48,
            'text_color': '#FFFF00',
            'bg_color': '#000000',
            'bg_opacity': 80,
            'has_background': True,
            'position': 'Bottom Center',
            'motion_effect': 'Zoom In',
            'crop_settings': None,
            'caption_position': {'x': 0.5, 'y': 0.9}
        }
    
    def save_settings(self):
        """Save settings to config file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f, indent=2)
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("🎬 Video Automator")
        title.setFont(QFont('Arial', 28, QFont.Bold))
        title.setStyleSheet("color: #1976D2;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Settings button
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.setFixedSize(140, 45)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(settings_btn)
        
        main_layout.addLayout(header_layout)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #ddd; max-height: 2px;")
        main_layout.addWidget(line)
        
        # Add folders section
        add_section = QLabel("📂 Add Video Folders")
        add_section.setFont(QFont('Arial', 16, QFont.Bold))
        add_section.setStyleSheet("color: #1976D2;")
        main_layout.addWidget(add_section)
        
        info_label = QLabel("💡 Drag & drop folders here, or click button below • Each folder needs: voiceover audio + at least 1 image")
        info_label.setStyleSheet("color: #666; font-style: italic; font-size: 12px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
        
        # Add folder button
        add_folder_btn = QPushButton("➕ Add Folders (or drag & drop)")
        add_folder_btn.setFixedHeight(70)
        add_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 3px dashed #45a049;
                border-radius: 12px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
                border: 3px dashed #388E3C;
            }
        """)
        add_folder_btn.clicked.connect(self.add_folders)
        main_layout.addWidget(add_folder_btn)
        
        # Queue section
        queue_label = QLabel("📋 Video Queue")
        queue_label.setFont(QFont('Arial', 16, QFont.Bold))
        queue_label.setStyleSheet("color: #1976D2;")
        main_layout.addWidget(queue_label)
        
        self.queue_list = QListWidget()
        self.queue_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #ddd;
                border-radius: 8px;
                background-color: #fafafa;
            }
            QListWidget::item {
                border-bottom: 1px solid #eee;
                padding: 5px;
            }
        """)
        main_layout.addWidget(self.queue_list)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Start Batch Render")
        self.start_btn.setFixedHeight(55)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #999;
            }
        """)
        self.start_btn.clicked.connect(self.start_rendering)
        
        clear_btn = QPushButton("🗑️ Clear Queue")
        clear_btn.setFixedHeight(55)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        clear_btn.clicked.connect(self.clear_queue)
        
        button_layout.addWidget(self.start_btn, 3)
        button_layout.addWidget(clear_btn, 1)
        
        main_layout.addLayout(button_layout)
        
        # Status bar
        self.status_label = QLabel("✨ Ready to automate your videos!")
        self.status_label.setStyleSheet("color: #666; padding: 10px; font-size: 12px; background-color: #f5f5f5; border-radius: 5px;")
        main_layout.addWidget(self.status_label)
        
        central_widget.setLayout(main_layout)
        
        self.setStyleSheet("QMainWindow { background-color: white; }")
    
    def open_settings(self):
        """Open settings dialog"""
        # Use enhanced settings if we have a sample, otherwise basic
        if self.video_queue:
            # Use first video in queue as sample
            sample_folder = self.video_queue[0]['path']
            dialog = EnhancedSettingsDialog(self, self.settings, sample_folder)
        else:
            # No sample available, ask user
            msg = QMessageBox.question(
                self,
                "Settings Preview",
                "To preview settings, we need a sample video folder.\n\n"
                "Would you like to select a sample folder?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if msg == QMessageBox.Yes:
                folder = QFileDialog.getExistingDirectory(self, "Select Sample Video Project Folder")
                if folder:
                    dialog = EnhancedSettingsDialog(self, self.settings, folder)
                else:
                    return
            else:
                QMessageBox.information(self, "💡 Tip", "Add a video folder first to access full preview settings!")
                return
        
        if dialog.exec_() == QDialog.Accepted:
            self.settings = dialog.get_settings()
            self.save_settings()
            self.status_label.setText("✅ Settings saved successfully!")
    
    def open_enhanced_settings(self, sample_folder):
        """Open enhanced settings with sample folder"""
        dialog = EnhancedSettingsDialog(self, self.settings, sample_folder)
        if dialog.exec_() == QDialog.Accepted:
            self.settings = dialog.get_settings()
            self.save_settings()
            self.status_label.setText("✅ Settings configured!")
    
    def add_folders(self):
        """Add video folders to queue"""
        reply = QMessageBox.question(
            self,
            "📂 Add Folders",
            "<b>How would you like to add folders?</b><br><br>"
            "• <b>Individual:</b> Select one video project folder<br>"
            "• <b>Batch Scan:</b> Select a parent folder, app will scan for all valid video projects inside",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Cancel:
            return
        
        if reply == QMessageBox.Yes:
            folder = QFileDialog.getExistingDirectory(self, "Select Video Project Folder")
            if folder:
                self.add_folder_to_queue(folder)
        else:
            parent_folder = QFileDialog.getExistingDirectory(self, "Select Parent Folder to Scan")
            if parent_folder:
                self.scan_and_add_folders(parent_folder)
    
    def scan_and_add_folders(self, parent_folder: str):
        """Scan parent folder for valid video projects"""
        from pathlib import Path
        from old_app.video_processor import VideoProcessor
        
        self.status_label.setText(f"🔍 Scanning {parent_folder}...")
        QApplication.processEvents()
        
        found_folders = []
        skipped_folders = []
        
        parent_path = Path(parent_folder)
        for subfolder in parent_path.iterdir():
            if subfolder.is_dir():
                processor = VideoProcessor(self.settings)
                is_valid, msg = processor.validate_folder(str(subfolder))
                
                if is_valid:
                    found_folders.append(str(subfolder))
                else:
                    skipped_folders.append((subfolder.name, msg))
        
        if found_folders:
            for folder in found_folders:
                self.add_folder_to_queue(folder, silent=True)
            
            summary = f"✅ Added {len(found_folders)} video project(s)\n\n"
            
            if skipped_folders:
                summary += f"⚠️ Skipped {len(skipped_folders)} folder(s):\n"
                for name, reason in skipped_folders[:5]:
                    summary += f"  • {name}: {reason}\n"
                if len(skipped_folders) > 5:
                    summary += f"  ... and {len(skipped_folders) - 5} more"
            
            QMessageBox.information(self, "✅ Scan Complete", summary)
            self.status_label.setText(f"✅ Added {len(found_folders)} videos from scan")
        else:
            QMessageBox.warning(
                self,
                "❌ No Valid Projects Found",
                f"No valid video projects found in:\n{parent_folder}\n\n"
                "Each video project folder must contain:\n"
                "• Audio file (voiceover)\n"
                "• At least 1 image file"
            )
            self.status_label.setText("❌ No valid projects found")
    
    def add_folder_to_queue(self, folder_path, silent=False):
        """Add a folder to the video queue"""
        from old_app.video_processor import VideoProcessor
        
        folder_name = os.path.basename(folder_path)
        
        processor = VideoProcessor(self.settings)
        is_valid, error_msg = processor.validate_folder(folder_path)
        
        if not is_valid:
            if not silent:
                QMessageBox.warning(
                    self,
                    "❌ Invalid Folder",
                    f"Folder '{folder_name}' is missing required files:\n\n{error_msg}\n\n"
                    "Each folder must contain:\n"
                    "• Voiceover audio (.mp3, .wav, etc.)\n"
                    "• At least 1 image (.png, .jpg, etc.)"
                )
            return
        
        detected = processor.detect_files_in_folder(folder_path)
        num_images = len(detected['images'])
        
        item_widget = VideoListItem(folder_name, num_images)
        item = QListWidgetItem(self.queue_list)
        item.setSizeHint(item_widget.sizeHint())
        
        self.queue_list.addItem(item)
        self.queue_list.setItemWidget(item, item_widget)
        
        self.video_queue.append({
            'path': folder_path,
            'name': folder_name,
            'item': item,
            'widget': item_widget
        })
        
        self.start_btn.setEnabled(True)
        
        if not silent:
            self.status_label.setText(f"✅ Added: {folder_name} ({num_images} image(s)) • Total: {len(self.video_queue)} video(s)")
    
    def clear_queue(self):
        """Clear all items from queue"""
        if not self.video_queue:
            return
            
        reply = QMessageBox.question(
            self,
            "Clear Queue?",
            f"Are you sure you want to remove all {len(self.video_queue)} video(s) from the queue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.queue_list.clear()
            self.video_queue = []
            self.start_btn.setEnabled(False)
            self.status_label.setText("🗑️ Queue cleared")
    
    def start_rendering(self):
        """Start batch rendering process"""
        if not self.video_queue:
            return
        
        from PyQt5.QtWidgets import QInputDialog
        workers, ok = QInputDialog.getInt(
            self,
            "⚙️ Parallel Rendering",
            "Number of simultaneous renders:\n(More = faster, but uses more resources)",
            value=2,
            min=1,
            max=4
        )
        
        if not ok:
            return
        
        self.status_label.setText(f"🚀 Starting batch render: {len(self.video_queue)} videos with {workers} parallel worker(s)...")
        self.start_btn.setEnabled(False)
        
        folder_paths = [video['path'] for video in self.video_queue]
        
        self.render_thread = RenderThread(
            folder_paths,
            self.settings,
            max_workers=workers
        )
        
        self.render_thread.progress_update.connect(self.on_progress_update)
        self.render_thread.render_complete.connect(self.on_render_complete)
        self.render_thread.all_complete.connect(self.on_all_complete)
        
        self.render_thread.start()
    
    def on_progress_update(self, folder_path, progress, status):
        """Handle progress updates"""
        for video in self.video_queue:
            if video['path'] == folder_path:
                video['widget'].update_progress(progress, status)
                break
    
    def on_render_complete(self, folder_path, success, output_path):
        """Handle individual video completion"""
        for video in self.video_queue:
            if video['path'] == folder_path:
                if success:
                    video['widget'].set_complete()
                    self.status_label.setText(f"✅ Completed: {video['name']} → {output_path}")
                else:
                    video['widget'].set_error("Rendering failed")
                    self.status_label.setText(f"❌ Failed: {video['name']}")
                break
    
    def on_all_complete(self):
        """Handle completion of all videos"""
        self.start_btn.setEnabled(True)
        
        output_list = "\n".join([f"  • {video['name']}.mp4" 
                                 for video in self.video_queue])
        
        QMessageBox.information(
            self,
            "🎉 Rendering Complete!",
            f"<h3>All videos have been rendered!</h3>"
            f"<p>Videos saved in their project folders:</p>"
            f"<pre>{output_list}</pre>"
            f"<p><b>You can now upload your videos to YouTube! 🚀</b></p>"
        )
        
        self.status_label.setText(f"🎉 All {len(self.video_queue)} video(s) complete! Check your project folders for MP4 files.")
    
    def dragEnterEvent(self, event):
        """Handle drag enter"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if os.path.isdir(url.toLocalFile()):
                    event.acceptProposedAction()
                    self.setStyleSheet("QMainWindow { background-color: #E3F2FD; }")
                    return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave"""
        self.setStyleSheet("QMainWindow { background-color: white; }")
    
    def dropEvent(self, event):
        """Handle drop"""
        from old_app.video_processor import VideoProcessor
        
        self.setStyleSheet("QMainWindow { background-color: white; }")
        
        folders = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                folders.append(path)
        
        if not folders:
            return
        
        if len(folders) == 1:
            folder = folders[0]
            processor = VideoProcessor(self.settings)
            is_valid, msg = processor.validate_folder(folder)
            
            if is_valid:
                self.add_folder_to_queue(folder)
            else:
                reply = QMessageBox.question(
                    self,
                    "Folder Type",
                    f"The folder you dropped is not a valid video project.\n\n"
                    f"Reason: {msg}\n\n"
                    "Would you like to scan it for video projects inside?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.scan_and_add_folders(folder)
        else:
            reply = QMessageBox.question(
                self,
                "Multiple Folders Dropped",
                f"You dropped {len(folders)} folders.\n\n"
                "How would you like to add them?\n\n"
                "• <b>Add All:</b> Add each folder as a video project\n"
                "• <b>Scan Each:</b> Scan each folder for video projects inside",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                added = 0
                skipped = []
                
                for folder in folders:
                    processor = VideoProcessor(self.settings)
                    is_valid, msg = processor.validate_folder(folder)
                    
                    if is_valid:
                        self.add_folder_to_queue(folder, silent=True)
                        added += 1
                    else:
                        skipped.append((os.path.basename(folder), msg))
                
                summary = f"✅ Added {added} folder(s)\n\n"
                if skipped:
                    summary += f"⚠️ Skipped {len(skipped)} folder(s):\n"
                    for name, reason in skipped[:5]:
                        summary += f"  • {name}: {reason}\n"
                    if len(skipped) > 5:
                        summary += f"  ... and {len(skipped) - 5} more"
                
                QMessageBox.information(self, "Drop Complete", summary)
                self.status_label.setText(f"✅ Added {added} videos via drag & drop")
                
            elif reply == QMessageBox.No:
                total_added = 0
                
                for folder in folders:
                    before = len(self.video_queue)
                    self.scan_and_add_folders(folder)
                    after = len(self.video_queue)
                    total_added += (after - before)
                
                self.status_label.setText(f"✅ Added {total_added} videos from {len(folders)} parent folder(s)")
        
        event.acceptProposedAction()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont('Arial', 10))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()