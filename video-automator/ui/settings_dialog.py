"""
Enhanced Settings Dialog
Live preview of caption settings with multiple effect selection
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox,
    QPushButton, QGridLayout, QCheckBox, QGroupBox, QLineEdit, QMessageBox,
    QColorDialog, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from video_processing import VideoProcessor
from .widgets.crop_view import ImageCropView
from .widgets.motion_preview import MotionEffectPreview
from .styles import Styles


class EnhancedSettingsDialog(QDialog):
    """Enhanced settings dialog with live preview and multi-effect selection"""
    
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
            'has_outline': False,
            'outline_color': '#000000',
            'outline_width': 3,
            'shadow_depth': 2,
            'position': 'Bottom Center',
            'motion_effects': ['Static'],  # Changed to list
            'crop_settings': None,
            'caption_position': {'x': 0.5, 'y': 0.9},
            'preview_text': 'Sample Caption Text',
            'caption_width_percent': 0.80
        }
        
        # Merge current settings with defaults
        if current_settings:
            self.settings = {**default_settings, **current_settings}
            
            # Handle backward compatibility for old 'motion_effect' key
            if 'motion_effect' in self.settings and 'motion_effects' not in self.settings:
                old_effect = self.settings['motion_effect']
                self.settings['motion_effects'] = [old_effect]
            
            print(f"[DEBUG] Loaded settings with crop: {self.settings.get('crop_settings')}")
            print(f"[DEBUG] Loaded caption position: {self.settings.get('caption_position')}")
            print(f"[DEBUG] Loaded motion effects: {self.settings.get('motion_effects')}")
        else:
            self.settings = default_settings
            print("[DEBUG] Using default settings (no previous settings found)")
        
        self.sample_folder = sample_folder
        self.sample_image = None
        
        # Find sample image
        if sample_folder:
            processor = VideoProcessor(self.settings)
            files = processor.detect_files(sample_folder)
            if files['images']:
                self.sample_image = files['images'][0]
        
        self.init_ui()
        
        # Load preview if available
        if self.sample_image:
            self.load_preview()
            
            # Show indicator if settings were loaded
            if current_settings and current_settings.get('crop_settings'):
                self.setWindowTitle("Video Settings - Setup & Preview (Previous settings loaded)")
        else:
            self.setWindowTitle("Video Settings - Setup & Preview (No preview available)")
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QHBoxLayout()
        
        # Left side - Preview
        left_panel = self._create_preview_panel()
        
        # Right side - Settings (with scroll)
        right_panel = self._create_settings_panel()
        
        # Add panels to main layout
        layout.addLayout(left_panel, stretch=3)
        layout.addWidget(right_panel, stretch=2)
        
        self.setLayout(layout)
    
    def _create_preview_panel(self):
        """Create left preview panel"""
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
        
        # Zoom controls
        zoom_group = self._create_zoom_controls()
        left_panel.addWidget(zoom_group)
        
        # Motion effects
        effects_section = self._create_motion_effects()
        left_panel.addLayout(effects_section)
        
        return left_panel
    
    def _create_zoom_controls(self):
        """Create zoom control group"""
        zoom_group = QGroupBox("🔍 Zoom & Position Controls")
        zoom_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        zoom_layout = QVBoxLayout()
        
        # Zoom buttons
        zoom_buttons_layout = QHBoxLayout()
        zoom_buttons_layout.addWidget(QLabel("Zoom:"))
        
        self.zoom_out_btn = QPushButton("➖")
        self.zoom_out_btn.setFixedSize(50, 50)
        self.zoom_out_btn.setStyleSheet(Styles.BUTTON_ZOOM_OUT)
        self.zoom_out_btn.clicked.connect(self.on_zoom_out)
        zoom_buttons_layout.addWidget(self.zoom_out_btn)
        
        self.zoom_label = QLabel("1.0x")
        self.zoom_label.setMinimumWidth(80)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setStyleSheet("font-weight: bold; font-size: 18px; color: #1976D2;")
        zoom_buttons_layout.addWidget(self.zoom_label)
        
        self.zoom_in_btn = QPushButton("➕")
        self.zoom_in_btn.setFixedSize(50, 50)
        self.zoom_in_btn.setStyleSheet(Styles.BUTTON_ZOOM_IN)
        self.zoom_in_btn.clicked.connect(self.on_zoom_in)
        zoom_buttons_layout.addWidget(self.zoom_in_btn)
        
        # Auto-fit and Reset buttons
        autofit_btn = QPushButton("📐 Auto-Fit")
        autofit_btn.setFixedSize(100, 50)
        autofit_btn.setStyleSheet(Styles.BUTTON_AUTO_FIT)
        autofit_btn.clicked.connect(self.on_auto_fit)
        zoom_buttons_layout.addWidget(autofit_btn)
        
        reset_btn = QPushButton("🔄 Reset")
        reset_btn.setFixedSize(80, 50)
        reset_btn.setStyleSheet(Styles.BUTTON_RESET)
        reset_btn.clicked.connect(self.on_reset_view)
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
        instructions.setStyleSheet(
            "color: #666; font-size: 11px; padding: 8px; "
            "background-color: #fffde7; border-radius: 5px;"
        )
        instructions.setWordWrap(True)
        zoom_layout.addWidget(instructions)
        
        zoom_group.setLayout(zoom_layout)
        return zoom_group
    
    def _create_motion_effects(self):
        """Create motion effects section with checkboxes for multi-selection"""
        effects_layout = QVBoxLayout()
        
        effects_label = QLabel("🎬 Motion Effects (Select Multiple)")
        effects_label.setFont(QFont('Arial', 12, QFont.Bold))
        effects_label.setStyleSheet("color: #1976D2;")
        effects_layout.addWidget(effects_label)
        
        # Get currently selected effects
        selected_effects = self.settings.get('motion_effects', ['Static'])
        if isinstance(selected_effects, str):
            selected_effects = [selected_effects]
        
        # Create checkboxes for each effect
        self.effect_checkboxes = {}
        checkbox_layout = QVBoxLayout()
        
        effects = ["Static", "Pan Right", "Pan Left", "Noise", "Camera Shake", "Tilt"]
        
        for effect in effects:
            checkbox = QCheckBox(effect)
            checkbox.setFont(QFont('Arial', 10))
            checkbox.setChecked(effect in selected_effects)
            checkbox.stateChanged.connect(self.on_effect_changed)
            
            # Add description
            descriptions = {
                "Static": "No motion - image stays still",
                "Pan Right": "Slowly pan from left to right",
                "Pan Left": "Slowly pan from right to left",
                "Noise": "Add film grain/noise effect",
                "Camera Shake": "Add subtle camera shake",
                "Tilt": "Gentle left-right tilting/rotation"
            }
            
            effect_container = QHBoxLayout()
            effect_container.addWidget(checkbox)
            
            desc_label = QLabel(f"- {descriptions[effect]}")
            desc_label.setStyleSheet("color: #666; font-size: 9px; font-style: italic;")
            effect_container.addWidget(desc_label)
            effect_container.addStretch()
            
            checkbox_layout.addLayout(effect_container)
            self.effect_checkboxes[effect] = checkbox
        
        effects_layout.addLayout(checkbox_layout)
        
        # Warning label for conflicting effects
        self.effect_warning = QLabel("")
        self.effect_warning.setStyleSheet("color: #FF9800; font-size: 10px; font-weight: bold;")
        self.effect_warning.setWordWrap(True)
        effects_layout.addWidget(self.effect_warning)
        
        return effects_layout
    
    def _create_settings_panel(self):
        """Create right settings panel with scroll"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        settings_widget = QWidget()
        right_panel = QVBoxLayout()
        right_panel.setSpacing(15)
        
        settings_title = QLabel("⚙️ Caption Settings")
        settings_title.setFont(QFont('Arial', 14, QFont.Bold))
        settings_title.setStyleSheet("color: #1976D2; padding: 5px;")
        right_panel.addWidget(settings_title)
        
        # Settings grid
        grid = self._create_settings_grid()
        right_panel.addLayout(grid)
        
        # Preview text input
        sample_group = self._create_preview_text_input()
        right_panel.addWidget(sample_group)
        
        right_panel.addStretch()
        
        # Buttons
        button_layout = self._create_buttons()
        right_panel.addLayout(button_layout)
        
        settings_widget.setLayout(right_panel)
        scroll_area.setWidget(settings_widget)
        
        return scroll_area
    
    def _create_settings_grid(self):
        """Create settings grid"""
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
        self.text_color_btn.setStyleSheet(
            f"background-color: {self.settings['text_color']}; color: white; font-weight: bold;"
        )
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
        
        # Background enable/disable
        grid.addWidget(QLabel("Background:"), row, 0)
        self.has_bg_checkbox = QCheckBox("Enable Background")
        saved_has_bg = self.settings.get('has_background', True)
        self.has_bg_checkbox.setChecked(saved_has_bg)
        self.has_bg_checkbox.stateChanged.connect(self.on_bg_toggle)
        grid.addWidget(self.has_bg_checkbox, row, 1)
        row += 1
        
        # Background color
        grid.addWidget(QLabel("BG Color:"), row, 0)
        self.bg_color_btn = QPushButton(self.settings['bg_color'])
        self.bg_color_btn.setStyleSheet(
            f"background-color: {self.settings['bg_color']}; color: white; font-weight: bold;"
        )
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        self.bg_color_btn.setEnabled(saved_has_bg)
        grid.addWidget(self.bg_color_btn, row, 1)
        row += 1
        
        # Background opacity
        grid.addWidget(QLabel("BG Opacity:"), row, 0)
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(self.settings['bg_opacity'])
        self.opacity_spin.setSuffix(" %")
        self.opacity_spin.valueChanged.connect(self.update_preview)
        self.opacity_spin.setEnabled(saved_has_bg)
        grid.addWidget(self.opacity_spin, row, 1)
        row += 1
        
        # === Outline Controls ===
        grid.addWidget(QLabel("Outline:"), row, 0)
        self.has_outline_checkbox = QCheckBox("Enable Outline")
        saved_has_outline = self.settings.get('has_outline', not saved_has_bg)
        self.has_outline_checkbox.setChecked(saved_has_outline)
        self.has_outline_checkbox.stateChanged.connect(self.on_outline_toggle)
        grid.addWidget(self.has_outline_checkbox, row, 1)
        row += 1
        
        # Outline color
        grid.addWidget(QLabel("Outline Color:"), row, 0)
        outline_color = self.settings.get('outline_color', '#000000')
        self.outline_color_btn = QPushButton(outline_color)
        self.outline_color_btn.setStyleSheet(
            f"background-color: {outline_color}; color: white; font-weight: bold;"
        )
        self.outline_color_btn.clicked.connect(self.choose_outline_color)
        self.outline_color_btn.setEnabled(saved_has_outline)
        grid.addWidget(self.outline_color_btn, row, 1)
        row += 1
        
        # Outline width
        grid.addWidget(QLabel("Outline Width:"), row, 0)
        self.outline_width_spin = QSpinBox()
        self.outline_width_spin.setRange(1, 10)
        self.outline_width_spin.setValue(self.settings.get('outline_width', 3))
        self.outline_width_spin.setSuffix(" px")
        self.outline_width_spin.valueChanged.connect(self.update_preview)
        self.outline_width_spin.setEnabled(saved_has_outline)
        grid.addWidget(self.outline_width_spin, row, 1)
        row += 1
        
        return grid
    
    def _create_preview_text_input(self):
        """Create preview text input group"""
        sample_group = QGroupBox("📝 Preview Text")
        sample_layout = QVBoxLayout()
        preview_text = self.settings.get('preview_text', 'Sample Caption Text')
        self.sample_text_input = QLineEdit(preview_text)
        self.sample_text_input.textChanged.connect(self.update_preview)
        self.sample_text_input.setPlaceholderText("Type preview text here...")
        sample_layout.addWidget(self.sample_text_input)
        sample_group.setLayout(sample_layout)
        return sample_group
    
    def _create_buttons(self):
        """Create action buttons"""
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("✅ Save Settings")
        save_btn.clicked.connect(self.save_and_close)
        save_btn.setStyleSheet(Styles.BUTTON_SAVE)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(Styles.BUTTON_CANCEL)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        return button_layout
    
    def on_effect_changed(self):
        """Handle effect checkbox changes"""
        selected = self.get_selected_effects()
        
        # Check for conflicting effects
        conflicts = []
        if "Pan Right" in selected and "Pan Left" in selected:
            conflicts.append("⚠️ Pan Right and Pan Left cannot be used together")
        
        if conflicts:
            self.effect_warning.setText("\n".join(conflicts))
        else:
            self.effect_warning.setText("")
        
        # Log selected effects
        print(f"[DEBUG] Selected effects: {selected}")
    
    def get_selected_effects(self):
        """Get list of selected effects"""
        selected = []
        for effect, checkbox in self.effect_checkboxes.items():
            if checkbox.isChecked():
                selected.append(effect)
        
        # If nothing selected, default to Static
        if not selected:
            selected = ["Static"]
            self.effect_checkboxes["Static"].setChecked(True)
        
        return selected
    
    def load_preview(self):
        """Load preview image and setup view with saved settings"""
        if self.sample_image:
            # Load image into crop view
            self.crop_view.load_image(self.sample_image)
            
            # Apply saved crop settings if available
            crop_settings = self.settings.get('crop_settings', None)
            if crop_settings:
                self.apply_crop_settings_to_preview(crop_settings)
            
            # Update caption preview
            self.update_preview()
            
            # Apply saved caption position
            caption_pos = self.settings.get('caption_position', None)
            if caption_pos and self.crop_view.caption_item:
                crop_rect = self.crop_view.crop_frame.rect()
                x = crop_rect.x() + caption_pos['x'] * crop_rect.width()
                y = crop_rect.y() + caption_pos['y'] * crop_rect.height()
                
                caption_rect = self.crop_view.caption_item.boundingRect()
                x = x - caption_rect.width() / 2
                y = y - caption_rect.height() / 2
                
                self.crop_view.caption_item.setPos(x, y)
    
    def apply_crop_settings_to_preview(self, crop_settings: dict):
        """Apply saved crop settings to preview"""
        try:
            if not self.crop_view.image_item or not self.crop_view.original_pixmap:
                print("[DEBUG] Cannot apply crop: no image loaded")
                return
            
            orig_width = self.crop_view.original_pixmap.width()
            orig_height = self.crop_view.original_pixmap.height()
            
            print(f"[DEBUG] Original image: {orig_width}x{orig_height}")
            
            crop_x = crop_settings.get('x', 0)
            crop_y = crop_settings.get('y', 0)
            crop_w = crop_settings.get('width', orig_width)
            crop_h = crop_settings.get('height', orig_height)
            
            print(f"[DEBUG] Applying crop: {crop_w}x{crop_h} at ({crop_x},{crop_y})")
            
            if crop_w <= 0 or crop_h <= 0:
                print(f"[DEBUG] Invalid crop dimensions: {crop_w}x{crop_h}")
                return
            
            crop_frame_rect = self.crop_view.crop_frame.rect()
            frame_w = crop_frame_rect.width()
            frame_h = crop_frame_rect.height()
            
            zoom_x = frame_w / crop_w
            zoom_y = frame_h / crop_h
            zoom = max(zoom_x, zoom_y)
            
            print(f"[DEBUG] Calculated zoom: {zoom:.2f}x")
            
            zoom = max(self.crop_view.min_zoom, min(self.crop_view.max_zoom, zoom))
            
            self.crop_view.image_item.setScale(zoom)
            self.crop_view.zoom_level = zoom
            self.zoom_label.setText(f"{zoom:.1f}x")
            
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
    
    def on_auto_fit(self):
        """Handle auto-fit button"""
        zoom = self.crop_view.auto_fit_to_frame()
        self.zoom_label.setText(f"{zoom:.1f}x")
    
    def on_bg_toggle(self):
        """Handle background toggle"""
        has_bg = self.has_bg_checkbox.isChecked()
        self.bg_color_btn.setEnabled(has_bg)
        self.opacity_spin.setEnabled(has_bg)
        self.settings['has_background'] = has_bg
        
        # Auto-enable outline when background is disabled
        if not has_bg and not self.has_outline_checkbox.isChecked():
            self.has_outline_checkbox.setChecked(True)
        
        self.update_preview()
    
    def on_outline_toggle(self):
        """Handle outline toggle"""
        has_outline = self.has_outline_checkbox.isChecked()
        self.outline_color_btn.setEnabled(has_outline)
        self.outline_width_spin.setEnabled(has_outline)
        self.settings['has_outline'] = has_outline
        self.update_preview()
    
    def update_preview(self):
        """Update caption preview on image"""
        font = QFont(self.font_combo.currentText(), self.font_size_spin.value())
        text_color = QColor(self.settings['text_color'])
        bg_color = QColor(self.settings['bg_color'])
        bg_opacity = self.opacity_spin.value()
        has_bg = self.has_bg_checkbox.isChecked()
        has_outline = self.has_outline_checkbox.isChecked()
        outline_color = QColor(self.settings.get('outline_color', '#000000'))
        outline_width = self.outline_width_spin.value()
        
        sample_text = self.sample_text_input.text() or "Sample Caption Text"
        
        self.crop_view.add_caption(
            sample_text,
            font,
            text_color,
            bg_color,
            bg_opacity,
            has_bg,
            has_outline,
            outline_color,
            outline_width
        )
    
    def choose_text_color(self):
        """Choose text color"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.set_text_color(color.name())
    
    def set_text_color(self, color):
        """Set text color"""
        self.settings['text_color'] = color
        self.text_color_btn.setText(color)
        self.text_color_btn.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold;")
        self.update_preview()
    
    def choose_bg_color(self):
        """Choose background color"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings['bg_color'] = color.name()
            self.bg_color_btn.setText(color.name())
            self.bg_color_btn.setStyleSheet(f"background-color: {color.name()}; color: white; font-weight: bold;")
            self.update_preview()
    
    def choose_outline_color(self):
        """Choose outline color"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.settings['outline_color'] = color.name()
            self.outline_color_btn.setText(color.name())
            self.outline_color_btn.setStyleSheet(f"background-color: {color.name()}; color: white; font-weight: bold;")
            self.update_preview()
    
    def save_and_close(self):
        """Save all settings and close"""
        # Get selected effects
        selected_effects = self.get_selected_effects()
        
        # Check for conflicts
        if "Pan Right" in selected_effects and "Pan Left" in selected_effects:
            QMessageBox.warning(
                self,
                "⚠️ Conflicting Effects",
                "Pan Right and Pan Left cannot be used together.\n\n"
                "Please uncheck one of them before saving."
            )
            return
        
        crop_region = self.crop_view.get_crop_region()
        caption_pos = self.crop_view.get_caption_position()
        
        # Validate crop
        if crop_region:
            if crop_region['x'] < 0 or crop_region['y'] < 0:
                reply = QMessageBox.question(
                    self,
                    "⚠️ Invalid Crop Position",
                    "The image position resulted in an invalid crop.\n\n"
                    "The crop has been adjusted to valid boundaries.\n"
                    f"Adjusted crop: {crop_region['width']}x{crop_region['height']} "
                    f"at ({crop_region['x']},{crop_region['y']})\n\n"
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
            'has_outline': self.has_outline_checkbox.isChecked(),
            'outline_color': self.settings.get('outline_color', '#000000'),
            'outline_width': self.outline_width_spin.value(),
            'shadow_depth': self.settings.get('shadow_depth', 2),
            'crop_settings': crop_region,
            'caption_position': caption_pos,
            'preview_text': self.sample_text_input.text(),
            'motion_effects': selected_effects  # Save as list
        })
        
        # Show success message
        effects_str = ", ".join(selected_effects)
        QMessageBox.information(
            self,
            "✅ Settings Saved",
            f"Your settings have been saved successfully!\n\n"
            f"📝 Font: {self.settings['font']} ({self.settings['font_size']}px)\n"
            f"🎨 Caption Position: ({caption_pos['x']:.2f}, {caption_pos['y']:.2f})\n"
            f"🖼️ Crop: {crop_region['width']}x{crop_region['height']} "
            f"at ({crop_region['x']},{crop_region['y']})\n"
            f"🎬 Motion Effects: {effects_str}\n"
            f"✏️ Outline: {'Enabled' if self.settings['has_outline'] else 'Disabled'}\n\n"
            "These settings will be used for all videos."
        )
        
        self.accept()
    
    def get_settings(self):
        """Return all settings"""
        return self.settings