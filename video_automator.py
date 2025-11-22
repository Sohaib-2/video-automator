import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, 
                             QProgressBar, QComboBox, QColorDialog, QDialog,
                             QGridLayout, QSpinBox, QFileDialog, QListWidgetItem,
                             QFrame, QMessageBox, QGraphicsView, QGraphicsScene,
                             QGraphicsPixmapItem, QGraphicsRectItem, QSlider,
                             QGraphicsTextItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRectF, QTimer, QPointF
from PyQt5.QtGui import (QFont, QColor, QPalette, QPixmap, QPen, QBrush, 
                         QPainter, QTransform, QImage)

# Import video processor
from video_processor import VideoProcessor, BatchRenderer, check_ffmpeg_installed, check_gpu_available

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
    """Interactive image crop/zoom view for 16:9 ratio"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Setup view
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Image item
        self.image_item = None
        self.original_pixmap = None
        
        # 16:9 crop frame (1920x1080)
        self.crop_frame = QGraphicsRectItem(0, 0, 1920, 1080)
        self.crop_frame.setPen(QPen(QColor(255, 0, 0, 200), 3, Qt.SolidLine))
        self.crop_frame.setBrush(QBrush(Qt.transparent))
        self.scene.addItem(self.crop_frame)
        
        # Zoom level
        self.zoom_level = 1.0
        self.min_zoom = 0.5
        self.max_zoom = 3.0
        
        # Caption overlay
        self.caption_item = None
        
    def load_image(self, image_path: str):
        """Load image into view"""
        self.original_pixmap = QPixmap(image_path)
        
        if self.image_item:
            self.scene.removeItem(self.image_item)
        
        self.image_item = QGraphicsPixmapItem(self.original_pixmap)
        self.scene.addItem(self.image_item)
        self.image_item.setZValue(-1)  # Behind crop frame
        
        # Center image
        self.center_image()
        
        # Fit view to show crop frame
        self.fitInView(self.crop_frame, Qt.KeepAspectRatio)
        
    def center_image(self):
        """Center image under crop frame"""
        if self.image_item:
            img_rect = self.image_item.boundingRect()
            crop_rect = self.crop_frame.rect()
            
            # Center position
            x = crop_rect.center().x() - img_rect.width() / 2
            y = crop_rect.center().y() - img_rect.height() / 2
            
            self.image_item.setPos(x, y)
    
    def set_zoom(self, zoom: float):
        """Set zoom level"""
        self.zoom_level = max(self.min_zoom, min(self.max_zoom, zoom))
        
        if self.image_item:
            # Scale image
            scale = self.zoom_level
            self.image_item.setScale(scale)
            
    def get_crop_region(self):
        """Get the crop region in original image coordinates"""
        if not self.image_item:
            return None
        
        # Get crop frame position in scene
        crop_rect = self.crop_frame.sceneBoundingRect()
        
        # Get image position and scale
        img_pos = self.image_item.pos()
        img_scale = self.image_item.scale()
        
        # Calculate crop in original image coordinates
        x = (crop_rect.x() - img_pos.x()) / img_scale
        y = (crop_rect.y() - img_pos.y()) / img_scale
        w = crop_rect.width() / img_scale
        h = crop_rect.height() / img_scale
        
        return {
            'x': int(x),
            'y': int(y),
            'width': int(w),
            'height': int(h)
        }
    
    def add_caption(self, text: str, font: QFont, color: QColor, bg_color: QColor, bg_opacity: int):
        """Add draggable caption to preview"""
        if self.caption_item:
            self.scene.removeItem(self.caption_item)
        
        self.caption_item = DraggableCaptionItem(text)
        self.caption_item.setFont(font)
        self.caption_item.setDefaultTextColor(color)
        
        # Add background
        # Create HTML with background
        html = f"""
        <div style='background-color: rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, {bg_opacity/100.0});
                    padding: 10px; border-radius: 5px;'>
            <span style='color: {color.name()}; font-family: {font.family()}; font-size: {font.pointSize()}pt;'>
                {text}
            </span>
        </div>
        """
        self.caption_item.setHtml(html)
        
        self.scene.addItem(self.caption_item)
        self.caption_item.setZValue(10)  # On top
        
        # Position at bottom center
        caption_rect = self.caption_item.boundingRect()
        crop_rect = self.crop_frame.rect()
        x = crop_rect.center().x() - caption_rect.width() / 2
        y = crop_rect.bottom() - caption_rect.height() - 50
        self.caption_item.setPos(x, y)
    
    def get_caption_position(self):
        """Get caption position relative to crop frame (normalized 0-1)"""
        if not self.caption_item:
            return {'x': 0.5, 'y': 0.85}  # Default bottom center
        
        caption_pos = self.caption_item.pos()
        crop_rect = self.crop_frame.rect()
        
        # Normalize to 0-1 range
        x = (caption_pos.x() - crop_rect.x()) / crop_rect.width()
        y = (caption_pos.y() - crop_rect.y()) / crop_rect.height()
        
        return {'x': x, 'y': y}
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        if self.image_item:
            # Zoom in/out
            zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            new_zoom = self.zoom_level * zoom_factor
            self.set_zoom(new_zoom)


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
            # Could add pan here too
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
            self.setStyleSheet("border: 3px solid #4CAF50; background-color: #f0f0f0;")
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
        self.resize(1200, 800)
        
        # Default settings
        self.settings = current_settings or {
            'font': 'Arial',
            'font_size': 48,
            'text_color': '#FFFFFF',
            'bg_color': '#000000',
            'bg_opacity': 80,
            'position': 'Bottom Center',
            'motion_effect': 'Zoom In',  # NEW
            'crop_settings': None  # NEW
        }
        
        self.sample_folder = sample_folder
        self.sample_image = None
        
        # Find sample image
        if sample_folder:
            from video_processor import VideoProcessor
            processor = VideoProcessor(self.settings)
            files = processor.detect_files_in_folder(sample_folder)
            if files['images']:
                self.sample_image = files['images'][0]
        
        self.init_ui()
        
        # Load preview if available
        if self.sample_image:
            self.load_preview()
    
    def init_ui(self):
        layout = QHBoxLayout()
        
        # Left side - Preview
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)
        
        preview_label = QLabel("Live Preview - 16:9 Video Output")
        preview_label.setFont(QFont('Arial', 14, QFont.Bold))
        left_panel.addWidget(preview_label)
        
        # Image crop view
        self.crop_view = ImageCropView()
        self.crop_view.setMinimumSize(640, 360)
        left_panel.addWidget(self.crop_view, stretch=3)
        
        # Zoom slider
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(50, 300)  # 0.5x to 3.0x
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        self.zoom_label = QLabel("1.0x")
        zoom_layout.addWidget(self.zoom_label)
        left_panel.addLayout(zoom_layout)
        
        # Instructions
        instructions = QLabel("Drag image to position | Scroll to zoom | Drag caption to reposition")
        instructions.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        instructions.setWordWrap(True)
        left_panel.addWidget(instructions)
        
        # Motion effects
        effects_label = QLabel("Motion Effects")
        effects_label.setFont(QFont('Arial', 12, QFont.Bold))
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
            label.setFont(QFont('Arial', 9))
            container.addWidget(label)
            
            effects_layout.addLayout(container)
        
        left_panel.addLayout(effects_layout)
        
        # Right side - Settings
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)
        
        settings_title = QLabel("Caption Settings")
        settings_title.setFont(QFont('Arial', 14, QFont.Bold))
        right_panel.addWidget(settings_title)
        
        # Settings grid
        grid = QGridLayout()
        grid.setSpacing(15)
        
        # Font
        grid.addWidget(QLabel("Font:"), 0, 0)
        self.font_combo = QComboBox()
        fonts = ['Arial', 'Arial Bold', 'Helvetica', 'Roboto', 'Montserrat', 
                 'Open Sans', 'Lato', 'Poppins', 'Oswald', 'Raleway']
        self.font_combo.addItems(fonts)
        self.font_combo.setCurrentText(self.settings['font'])
        self.font_combo.currentTextChanged.connect(self.update_preview)
        grid.addWidget(self.font_combo, 0, 1)
        
        # Font size
        grid.addWidget(QLabel("Font Size:"), 1, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(20, 100)
        self.font_size_spin.setValue(self.settings['font_size'])
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.valueChanged.connect(self.update_preview)
        grid.addWidget(self.font_size_spin, 1, 1)
        
        # Text color
        grid.addWidget(QLabel("Text Color:"), 2, 0)
        self.text_color_btn = QPushButton(self.settings['text_color'])
        self.text_color_btn.setStyleSheet(f"background-color: {self.settings['text_color']}; color: white;")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        grid.addWidget(self.text_color_btn, 2, 1)
        
        # Text color presets
        text_preset_layout = QHBoxLayout()
        text_colors = [('#FFFFFF', 'White'), ('#000000', 'Black'), ('#FF0000', 'Red'), 
                      ('#0000FF', 'Blue'), ('#FFFF00', 'Yellow'), ('#00FF00', 'Green')]
        for color, name in text_colors:
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(f"background-color: {color}; border: 1px solid #ccc;")
            btn.clicked.connect(lambda checked, c=color: self.set_text_color(c))
            text_preset_layout.addWidget(btn)
        grid.addLayout(text_preset_layout, 3, 1)
        
        # Background color
        grid.addWidget(QLabel("Background Color:"), 4, 0)
        self.bg_color_btn = QPushButton(self.settings['bg_color'])
        self.bg_color_btn.setStyleSheet(f"background-color: {self.settings['bg_color']}; color: white;")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        grid.addWidget(self.bg_color_btn, 4, 1)
        
        # Background opacity
        grid.addWidget(QLabel("Background Opacity:"), 5, 0)
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(self.settings['bg_opacity'])
        self.opacity_spin.setSuffix(" %")
        self.opacity_spin.valueChanged.connect(self.update_preview)
        grid.addWidget(self.opacity_spin, 5, 1)
        
        right_panel.addLayout(grid)
        right_panel.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 12px; font-weight: bold; font-size: 14px;")
        cancel_btn.setStyleSheet("background-color: #f44336; color: white; padding: 12px; font-size: 14px;")
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        right_panel.addLayout(button_layout)
        
        # Add panels to main layout
        layout.addLayout(left_panel, stretch=2)
        layout.addLayout(right_panel, stretch=1)
        
        self.setLayout(layout)
    
    def load_preview(self):
        """Load preview image and setup view"""
        if self.sample_image:
            # Load image into crop view
            self.crop_view.load_image(self.sample_image)
            
            # Load into effect previews
            for preview in self.effect_previews.values():
                preview.load_preview(self.sample_image)
            
            # Select current effect
            current_effect = self.settings.get('motion_effect', 'Zoom In')
            self.select_effect(current_effect)
            
            # Update caption preview
            self.update_preview()
    
    def on_zoom_changed(self, value):
        """Handle zoom slider change"""
        zoom = value / 100.0
        self.zoom_label.setText(f"{zoom:.1f}x")
        self.crop_view.set_zoom(zoom)
    
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
        
        self.crop_view.add_caption(
            "Sample Caption Text",
            font,
            text_color,
            bg_color,
            bg_opacity
        )
    
    def choose_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.set_text_color(color.name())
    
    def set_text_color(self, color):
        self.settings['text_color'] = color
        self.text_color_btn.setText(color)
        self.text_color_btn.setStyleSheet(f"background-color: {color}; color: white;")
        self.update_preview()
    
    def choose_bg_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings['bg_color'] = color.name()
            self.bg_color_btn.setText(color.name())
            self.bg_color_btn.setStyleSheet(f"background-color: {color.name()}; color: white;")
            self.update_preview()
    
    def save_and_close(self):
        """Save all settings and close"""
        # Get crop settings
        crop_region = self.crop_view.get_crop_region()
        caption_pos = self.crop_view.get_caption_position()
        
        self.settings.update({
            'font': self.font_combo.currentText(),
            'font_size': self.font_size_spin.value(),
            'bg_opacity': self.opacity_spin.value(),
            'crop_settings': crop_region,
            'caption_position': caption_pos
        })
        
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
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Folder name with image count
        name_label = QLabel(f"[Folder] {self.folder_name} ({self.num_images} image{'s' if self.num_images != 1 else ''})")
        name_label.setFont(QFont('Arial', 11, QFont.Bold))
        layout.addWidget(name_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Queued")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def update_progress(self, value, status="Processing..."):
        self.progress_bar.setValue(value)
        self.status_label.setText(status)
    
    def set_complete(self):
        self.progress_bar.setValue(100)
        self.status_label.setText("[OK] Complete")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
    
    def set_error(self, error_msg="Error"):
        self.progress_bar.setValue(0)
        self.status_label.setText(f"[X] {error_msg}")
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
        self.setWindowTitle("Video Automator - Batch Video Editor")
        self.setGeometry(100, 100, 900, 700)
        
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
        msg.setWindowTitle("Welcome to Video Automator!")
        msg.setIcon(QMessageBox.Information)
        msg.setText(
            "Welcome! Let's set up your video settings.\n\n"
            "First, add a sample video project folder (with audio + images)\n"
            "so you can preview and configure your captions and effects."
        )
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        
        if msg.exec_() == QMessageBox.Ok:
            # Ask user to select sample folder
            folder = QFileDialog.getExistingDirectory(self, "Select Sample Video Project Folder")
            if folder:
                # Validate it
                from video_processor import VideoProcessor
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
                "FFmpeg Not Found",
                "FFmpeg is not installed or not in PATH.\n\n"
                "Please install FFmpeg to use this application.\n"
                "Visit: https://ffmpeg.org/download.html"
            )
        
        gpu_available = check_gpu_available()
        if gpu_available:
            print("[OK] NVIDIA GPU detected - will use hardware acceleration")
        else:
            print("ℹ No NVIDIA GPU detected - will use CPU encoding")
    
    def load_settings(self):
        """Load settings from config file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default settings
        return {
            'font': 'Arial',
            'font_size': 48,
            'text_color': '#FFFFFF',
            'bg_color': '#000000',
            'bg_opacity': 80,
            'position': 'Bottom Center',
            'motion_effect': 'Zoom In',
            'crop_settings': None,
            'caption_position': {'x': 0.5, 'y': 0.85}
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
        
        title = QLabel("Video Automator")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Settings button
        settings_btn = QPushButton("Settings")
        settings_btn.setFixedSize(120, 40)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
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
        line.setStyleSheet("background-color: #ccc;")
        main_layout.addWidget(line)
        
        # Add folders section
        add_section = QLabel("Add Video Folders")
        add_section.setFont(QFont('Arial', 14, QFont.Bold))
        main_layout.addWidget(add_section)
        
        info_label = QLabel("Drag & drop folders here, or click button below - Each folder: voiceover audio + at least 1 image")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(info_label)
        
        # Add folder button
        add_folder_btn = QPushButton("Add Folders (or drag & drop)")
        add_folder_btn.setFixedHeight(60)
        add_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 2px dashed #45a049;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        add_folder_btn.clicked.connect(self.add_folders)
        main_layout.addWidget(add_folder_btn)
        
        # Queue section
        queue_label = QLabel("Video Queue")
        queue_label.setFont(QFont('Arial', 14, QFont.Bold))
        main_layout.addWidget(queue_label)
        
        self.queue_list = QListWidget()
        self.queue_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
        """)
        main_layout.addWidget(self.queue_list)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Batch Render")
        self.start_btn.setFixedHeight(50)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.start_btn.clicked.connect(self.start_rendering)
        
        clear_btn = QPushButton("Clear Queue")
        clear_btn.setFixedHeight(50)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
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
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; padding: 10px;")
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
                # Use basic dialog without preview
                from PyQt5.QtWidgets import QInputDialog
                QMessageBox.information(self, "Basic Settings", "Add a video folder first to access full preview settings.")
                return
        
        if dialog.exec_() == QDialog.Accepted:
            self.settings = dialog.get_settings()
            self.save_settings()
            self.status_label.setText("Settings saved successfully!")
    
    def open_enhanced_settings(self, sample_folder):
        """Open enhanced settings with sample folder"""
        dialog = EnhancedSettingsDialog(self, self.settings, sample_folder)
        if dialog.exec_() == QDialog.Accepted:
            self.settings = dialog.get_settings()
            self.save_settings()
            self.status_label.setText("Settings configured!")
    
    def add_folders(self):
        """Add video folders to queue"""
        reply = QMessageBox.question(
            self,
            "Add Folders",
            "How would you like to add folders?\n\n"
            "- Individual: Select one video project folder\n"
            "- Batch Scan: Select a parent folder, app will scan for all valid video projects inside\n\n"
            "Choose method:",
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
        from video_processor import VideoProcessor
        
        self.status_label.setText(f"Scanning {parent_folder}...")
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
            
            summary = f"[OK] Added {len(found_folders)} video project(s)\n\n"
            
            if skipped_folders:
                summary += f"⚠ Skipped {len(skipped_folders)} folder(s):\n"
                for name, reason in skipped_folders[:5]:
                    summary += f"  - {name}: {reason}\n"
                if len(skipped_folders) > 5:
                    summary += f"  ... and {len(skipped_folders) - 5} more"
            
            QMessageBox.information(self, "Scan Complete", summary)
            self.status_label.setText(f"Added {len(found_folders)} videos from scan")
        else:
            QMessageBox.warning(
                self,
                "No Valid Projects Found",
                f"No valid video projects found in:\n{parent_folder}\n\n"
                "Each video project folder must contain:\n"
                "- Audio file (voiceover)\n"
                "- At least 1 image file"
            )
            self.status_label.setText("No valid projects found")
    
    def add_folder_to_queue(self, folder_path, silent=False):
        """Add a folder to the video queue"""
        from video_processor import VideoProcessor
        
        folder_name = os.path.basename(folder_path)
        
        processor = VideoProcessor(self.settings)
        is_valid, error_msg = processor.validate_folder(folder_path)
        
        if not is_valid:
            if not silent:
                QMessageBox.warning(
                    self,
                    "Invalid Folder",
                    f"Folder '{folder_name}' is missing required files:\n\n{error_msg}\n\n"
                    "Each folder must contain:\n"
                    "- Voiceover audio (.mp3, .wav, etc.)\n"
                    "- At least 1 image (.png, .jpg, etc.)"
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
            self.status_label.setText(f"Added: {folder_name} ({num_images} image(s)) | Total videos: {len(self.video_queue)}")
    
    def clear_queue(self):
        """Clear all items from queue"""
        self.queue_list.clear()
        self.video_queue = []
        self.start_btn.setEnabled(False)
        self.status_label.setText("Queue cleared")
    
    def start_rendering(self):
        """Start batch rendering process"""
        if not self.video_queue:
            return
        
        from PyQt5.QtWidgets import QInputDialog
        workers, ok = QInputDialog.getInt(
            self,
            "Parallel Rendering",
            "Number of simultaneous renders:",
            value=2,
            min=1,
            max=4
        )
        
        if not ok:
            return
        
        self.status_label.setText(f"Starting batch render for {len(self.video_queue)} videos with {workers} parallel workers...")
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
                    self.status_label.setText(f"[OK] Completed: {video['name']} → {output_path}")
                else:
                    video['widget'].set_error("Rendering failed")
                    self.status_label.setText(f"[X] Failed: {video['name']}")
                break
    
    def on_all_complete(self):
        """Handle completion of all videos"""
        self.start_btn.setEnabled(True)
        
        output_list = "\n".join([f"- {video['name']}: {video['path']}/{video['name']}.mp4" 
                                 for video in self.video_queue])
        
        QMessageBox.information(
            self,
            "Rendering Complete",
            f"All videos have been rendered!\n\n"
            f"Videos saved in their project folders:\n{output_list}\n\n"
            "You can now upload your videos to YouTube!"
        )
        
        self.status_label.setText(f"All videos complete! Check your project folders for the MP4 files.")
    
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
        from video_processor import VideoProcessor
        
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
                "- Add All: Add each folder as a video project\n"
                "- Scan Each: Scan each folder for video projects inside",
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
                
                summary = f"[OK] Added {added} folder(s)\n\n"
                if skipped:
                    summary += f"⚠ Skipped {len(skipped)} folder(s):\n"
                    for name, reason in skipped[:5]:
                        summary += f"  - {name}: {reason}\n"
                    if len(skipped) > 5:
                        summary += f"  ... and {len(skipped) - 5} more"
                
                QMessageBox.information(self, "Drop Complete", summary)
                self.status_label.setText(f"Added {added} videos via drag & drop")
                
            elif reply == QMessageBox.No:
                total_added = 0
                
                for folder in folders:
                    before = len(self.video_queue)
                    self.scan_and_add_folders(folder)
                    after = len(self.video_queue)
                    total_added += (after - before)
                
                self.status_label.setText(f"Added {total_added} videos from {len(folders)} parent folder(s)")
        
        event.acceptProposedAction()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont('Arial', 10))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()