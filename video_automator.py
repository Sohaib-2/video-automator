import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QListWidget, 
                             QProgressBar, QComboBox, QColorDialog, QDialog,
                             QGridLayout, QSpinBox, QFileDialog, QListWidgetItem,
                             QFrame, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

# Import video processor
from video_processor import VideoProcessor, BatchRenderer, check_ffmpeg_installed, check_gpu_available

class SettingsDialog(QDialog):
    """Dialog for configuring caption settings"""
    
    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Caption Settings")
        self.setModal(True)
        self.resize(500, 400)
        
        # Default settings
        self.settings = current_settings or {
            'font': 'Arial',
            'font_size': 48,
            'text_color': '#FFFFFF',
            'bg_color': '#000000',
            'bg_opacity': 80,
            'position': 'Bottom Center'
        }
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Caption Settings")
        title.setFont(QFont('Arial', 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Settings grid
        grid = QGridLayout()
        grid.setSpacing(15)
        
        # Font selection
        grid.addWidget(QLabel("Font:"), 0, 0)
        self.font_combo = QComboBox()
        fonts = ['Arial', 'Arial Bold', 'Helvetica', 'Roboto', 'Montserrat', 
                 'Open Sans', 'Lato', 'Poppins', 'Oswald', 'Raleway']
        self.font_combo.addItems(fonts)
        self.font_combo.setCurrentText(self.settings['font'])
        grid.addWidget(self.font_combo, 0, 1)
        
        # Font size
        grid.addWidget(QLabel("Font Size:"), 1, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(20, 100)
        self.font_size_spin.setValue(self.settings['font_size'])
        self.font_size_spin.setSuffix(" px")
        grid.addWidget(self.font_size_spin, 1, 1)
        
        # Position
        grid.addWidget(QLabel("Position:"), 2, 0)
        self.position_combo = QComboBox()
        positions = ['Top Center', 'Middle Center', 'Bottom Center']
        self.position_combo.addItems(positions)
        self.position_combo.setCurrentText(self.settings['position'])
        grid.addWidget(self.position_combo, 2, 1)
        
        # Text color
        grid.addWidget(QLabel("Text Color:"), 3, 0)
        self.text_color_btn = QPushButton(self.settings['text_color'])
        self.text_color_btn.setStyleSheet(f"background-color: {self.settings['text_color']}; color: white;")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        grid.addWidget(self.text_color_btn, 3, 1)
        
        # Preset colors for text
        text_preset_layout = QHBoxLayout()
        text_colors = [('#FFFFFF', 'White'), ('#000000', 'Black'), ('#FF0000', 'Red'), 
                      ('#0000FF', 'Blue'), ('#FFFF00', 'Yellow'), ('#00FF00', 'Green')]
        for color, name in text_colors:
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(f"background-color: {color}; border: 1px solid #ccc;")
            btn.clicked.connect(lambda checked, c=color: self.set_text_color(c))
            text_preset_layout.addWidget(btn)
        grid.addLayout(text_preset_layout, 4, 1)
        
        # Background color
        grid.addWidget(QLabel("Background Color:"), 5, 0)
        self.bg_color_btn = QPushButton(self.settings['bg_color'])
        self.bg_color_btn.setStyleSheet(f"background-color: {self.settings['bg_color']}; color: white;")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        grid.addWidget(self.bg_color_btn, 5, 1)
        
        # Background opacity
        grid.addWidget(QLabel("Background Opacity:"), 6, 0)
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(self.settings['bg_opacity'])
        self.opacity_spin.setSuffix(" %")
        grid.addWidget(self.opacity_spin, 6, 1)
        
        layout.addLayout(grid)
        
        # Preview section
        preview_label = QLabel("Preview")
        preview_label.setFont(QFont('Arial', 12, QFont.Bold))
        layout.addWidget(preview_label)
        
        self.preview = QLabel("Sample Caption Text")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(80)
        self.preview.setStyleSheet("border: 1px solid #ccc; padding: 10px;")
        self.update_preview()
        layout.addWidget(self.preview)
        
        # Connect signals for live preview
        self.font_combo.currentTextChanged.connect(self.update_preview)
        self.font_size_spin.valueChanged.connect(self.update_preview)
        self.opacity_spin.valueChanged.connect(self.update_preview)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        cancel_btn.setStyleSheet("background-color: #f44336; color: white; padding: 10px;")
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def update_preview(self):
        """Update the preview with current settings"""
        font_name = self.font_combo.currentText()
        font_size = self.font_size_spin.value()
        
        # Calculate opacity in hex
        opacity_hex = format(int(self.opacity_spin.value() * 2.55), '02x')
        bg_with_opacity = self.settings['bg_color'] + opacity_hex
        
        style = f"""
            background-color: {bg_with_opacity};
            color: {self.settings['text_color']};
            font-family: {font_name};
            font-size: {font_size}px;
            padding: 15px;
            border-radius: 5px;
        """
        self.preview.setStyleSheet(style)
    
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
    
    def get_settings(self):
        """Return the current settings"""
        return {
            'font': self.font_combo.currentText(),
            'font_size': self.font_size_spin.value(),
            'text_color': self.settings['text_color'],
            'bg_color': self.settings['bg_color'],
            'bg_opacity': self.opacity_spin.value(),
            'position': self.position_combo.currentText()
        }


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
        name_label = QLabel(f"📁 {self.folder_name} ({self.num_images} image{'s' if self.num_images != 1 else ''})")
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
        self.status_label.setText("✓ Complete")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
    
    def set_error(self, error_msg="Error"):
        self.progress_bar.setValue(0)
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
        
        # Process videos (output in same folder as input)
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
        
        # Output directory
        self.output_dir = os.path.join(os.path.expanduser('~'), 'VideoAutomator_Output')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Rendering thread
        self.render_thread = None
        
        # Check system requirements
        self.check_system_requirements()
        
        self.init_ui()
    
    def check_system_requirements(self):
        """Check if FFmpeg and GPU are available"""
        # Check FFmpeg
        if not check_ffmpeg_installed():
            QMessageBox.warning(
                self,
                "FFmpeg Not Found",
                "FFmpeg is not installed or not in PATH.\n\n"
                "Please install FFmpeg to use this application.\n"
                "Visit: https://ffmpeg.org/download.html"
            )
        
        # Check GPU (optional, just for info)
        gpu_available = check_gpu_available()
        if gpu_available:
            print("✓ NVIDIA GPU detected - will use hardware acceleration")
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
            'position': 'Bottom Center'
        }
    
    def save_settings(self):
        """Save settings to config file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f, indent=2)
    
    def init_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("🎬 Video Automator")
        title.setFont(QFont('Arial', 24, QFont.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Settings button
        settings_btn = QPushButton("⚙️ Settings")
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
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #ccc;")
        main_layout.addWidget(line)
        
        # Add folders section
        add_section = QLabel("Add Video Folders")
        add_section.setFont(QFont('Arial', 14, QFont.Bold))
        main_layout.addWidget(add_section)
        
        info_label = QLabel("Drag & drop folders here, or click button below • Each folder: voiceover audio + at least 1 image")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        main_layout.addWidget(info_label)
        
        # Add folder button
        add_folder_btn = QPushButton("📂 Add Folders (or drag & drop)")
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
        
        # Video queue section
        queue_label = QLabel("Video Queue")
        queue_label.setFont(QFont('Arial', 14, QFont.Bold))
        main_layout.addWidget(queue_label)
        
        # Queue list
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
        
        self.start_btn = QPushButton("▶️ Start Batch Render")
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
        
        clear_btn = QPushButton("🗑️ Clear Queue")
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
        
        # Apply overall stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
        """)
    
    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self, self.settings)
        if dialog.exec_() == QDialog.Accepted:
            self.settings = dialog.get_settings()
            self.save_settings()
            self.status_label.setText("Settings saved successfully!")
    
    def add_folders(self):
        """Add video folders to queue - can add individual folder or scan parent folder"""
        # Show dialog with options
        reply = QMessageBox.question(
            self,
            "Add Folders",
            "How would you like to add folders?\n\n"
            "• Individual: Select one video project folder\n"
            "• Batch Scan: Select a parent folder, app will scan for all valid video projects inside\n\n"
            "Choose method:",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Cancel:
            return
        
        if reply == QMessageBox.Yes:
            # Individual folder selection
            folder = QFileDialog.getExistingDirectory(self, "Select Video Project Folder")
            if folder:
                self.add_folder_to_queue(folder)
        else:
            # Batch scan - select parent folder
            parent_folder = QFileDialog.getExistingDirectory(self, "Select Parent Folder to Scan")
            if parent_folder:
                self.scan_and_add_folders(parent_folder)
    
    def scan_and_add_folders(self, parent_folder: str):
        """Scan parent folder for valid video projects and add them to queue"""
        from pathlib import Path
        
        self.status_label.setText(f"Scanning {parent_folder}...")
        QApplication.processEvents()  # Update UI
        
        found_folders = []
        skipped_folders = []
        
        # Scan all immediate subdirectories
        parent_path = Path(parent_folder)
        for subfolder in parent_path.iterdir():
            if subfolder.is_dir():
                # Check if this folder is a valid video project
                processor = VideoProcessor(self.settings)
                is_valid, msg = processor.validate_folder(str(subfolder))
                
                if is_valid:
                    found_folders.append(str(subfolder))
                else:
                    skipped_folders.append((subfolder.name, msg))
        
        # Add all found folders
        if found_folders:
            for folder in found_folders:
                self.add_folder_to_queue(folder, silent=True)
            
            # Show summary
            summary = f"✓ Added {len(found_folders)} video project(s)\n\n"
            
            if skipped_folders:
                summary += f"⚠ Skipped {len(skipped_folders)} folder(s):\n"
                for name, reason in skipped_folders[:5]:  # Show first 5
                    summary += f"  • {name}: {reason}\n"
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
                "• Audio file (voiceover)\n"
                "• At least 1 image file"
            )
            self.status_label.setText("No valid projects found")
    
    def add_folder_to_queue(self, folder_path, silent=False):
        """Add a folder to the video queue"""
        folder_name = os.path.basename(folder_path)
        
        # Validate folder before adding
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
                    "- At least 1 image (.png, .jpg, etc.)\n"
                    "- script.txt (optional, will use Whisper if missing)"
                )
            return
        
        # Get detected files info
        detected = processor.detect_files_in_folder(folder_path)
        num_images = len(detected['images'])
        
        # Create custom list item with image count
        item_widget = VideoListItem(folder_name, num_images)
        item = QListWidgetItem(self.queue_list)
        item.setSizeHint(item_widget.sizeHint())
        
        self.queue_list.addItem(item)
        self.queue_list.setItemWidget(item, item_widget)
        
        # Store folder path
        self.video_queue.append({
            'path': folder_path,
            'name': folder_name,
            'item': item,
            'widget': item_widget
        })
        
        # Enable start button
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
        
        # Ask user about parallel rendering
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
        
        # Get folder paths
        folder_paths = [video['path'] for video in self.video_queue]
        
        # Create and start render thread (no output_dir needed - saves in same folder)
        self.render_thread = RenderThread(
            folder_paths,
            self.settings,
            max_workers=workers
        )
        
        # Connect signals
        self.render_thread.progress_update.connect(self.on_progress_update)
        self.render_thread.render_complete.connect(self.on_render_complete)
        self.render_thread.all_complete.connect(self.on_all_complete)
        
        # Start rendering
        self.render_thread.start()
    
    def on_progress_update(self, folder_path, progress, status):
        """Handle progress updates from render thread"""
        # Find the video item and update it
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
                    self.status_label.setText(f"✓ Completed: {video['name']} → {output_path}")
                else:
                    video['widget'].set_error("Rendering failed")
                    self.status_label.setText(f"❌ Failed: {video['name']}")
                break
    
    def on_all_complete(self):
        """Handle completion of all videos"""
        self.start_btn.setEnabled(True)
        
        # Show completion dialog with list of output locations
        output_list = "\n".join([f"• {video['name']}: {video['path']}/{video['name']}.mp4" 
                                 for video in self.video_queue])
        
        QMessageBox.information(
            self,
            "Rendering Complete",
            f"All videos have been rendered!\n\n"
            f"Videos saved in their project folders:\n{output_list}\n\n"
            "You can now upload your videos to YouTube!"
        )
        
        self.status_label.setText(f"All videos complete! Check your project folders for the MP4 files.")
    
    # Drag and Drop Implementation
    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            # Check if any of the URLs are directories
            for url in event.mimeData().urls():
                if os.path.isdir(url.toLocalFile()):
                    event.acceptProposedAction()
                    # Visual feedback - change appearance when dragging over
                    self.setStyleSheet("QMainWindow { background-color: #E3F2FD; }")
                    return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event"""
        # Reset appearance when drag leaves
        self.setStyleSheet("QMainWindow { background-color: white; }")
    
    def dropEvent(self, event):
        """Handle drop event"""
        # Reset appearance
        self.setStyleSheet("QMainWindow { background-color: white; }")
        
        # Get all dropped folders
        folders = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                folders.append(path)
        
        if not folders:
            return
        
        # If single folder dropped
        if len(folders) == 1:
            folder = folders[0]
            
            # Check if it's a valid video project folder
            processor = VideoProcessor(self.settings)
            is_valid, msg = processor.validate_folder(folder)
            
            if is_valid:
                # It's a valid video project - add it directly
                self.add_folder_to_queue(folder)
            else:
                # Not valid - might be a parent folder, ask user
                reply = QMessageBox.question(
                    self,
                    "Folder Type",
                    f"The folder you dropped is not a valid video project.\n\n"
                    f"Reason: {msg}\n\n"
                    "Would you like to scan it for video projects inside?\n\n"
                    "• Yes: Scan for subfolders with video projects\n"
                    "• No: Cancel",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.scan_and_add_folders(folder)
        
        # If multiple folders dropped
        else:
            # Ask how to handle
            reply = QMessageBox.question(
                self,
                "Multiple Folders Dropped",
                f"You dropped {len(folders)} folders.\n\n"
                "How would you like to add them?\n\n"
                "• Add All: Add each folder as a video project\n"
                "• Scan Each: Scan each folder for video projects inside\n"
                "• Cancel: Don't add anything",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                # Add all folders directly (validate each)
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
                
                # Show summary
                summary = f"✓ Added {added} folder(s)\n\n"
                if skipped:
                    summary += f"⚠ Skipped {len(skipped)} folder(s):\n"
                    for name, reason in skipped[:5]:
                        summary += f"  • {name}: {reason}\n"
                    if len(skipped) > 5:
                        summary += f"  ... and {len(skipped) - 5} more"
                
                QMessageBox.information(self, "Drop Complete", summary)
                self.status_label.setText(f"Added {added} videos via drag & drop")
                
            elif reply == QMessageBox.No:
                # Scan each folder for projects
                total_added = 0
                
                for folder in folders:
                    # Count before
                    before = len(self.video_queue)
                    self.scan_and_add_folders(folder)
                    # Count after
                    after = len(self.video_queue)
                    total_added += (after - before)
                
                self.status_label.setText(f"Added {total_added} videos from {len(folders)} parent folder(s)")
        
        event.acceptProposedAction()


def main():
    app = QApplication(sys.argv)
    
    # Set application-wide font
    app.setFont(QFont('Arial', 10))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()