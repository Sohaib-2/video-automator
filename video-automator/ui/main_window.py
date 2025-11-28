"""
Main Window
Primary application window with video queue and batch rendering
"""

import sys
import json
import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QFrame, QMessageBox, QFileDialog, QListWidgetItem, QDialog,
    QInputDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from video_processing import VideoProcessor, check_ffmpeg_installed, check_gpu_available
from .settings_dialog import EnhancedSettingsDialog
from .widgets.video_list_item import VideoListItem
from .widgets.render_thread import RenderThread
from .styles import Styles


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
            folder = QFileDialog.getExistingDirectory(self, "Select Sample Video Project Folder")
            if folder:
                processor = VideoProcessor(self.settings)
                is_valid, error_msg = processor.validate_folder(folder)
                
                if is_valid:
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
                    if 'has_outline' not in settings:
                        settings['has_outline'] = False
                    if 'outline_color' not in settings:
                        settings['outline_color'] = '#000000'
                    if 'outline_width' not in settings:
                        settings['outline_width'] = 3
                    if 'shadow_depth' not in settings:
                        settings['shadow_depth'] = 2
                    if 'caption_position' not in settings:
                        settings['caption_position'] = {'x': 0.5, 'y': 0.95}
                    if 'caption_width_percent' not in settings:
                        settings['caption_width_percent'] = 0.80
                    if 'video_resolution' not in settings:
                        settings['video_resolution'] = '1080p'
                    
                    # UPDATED: Handle motion effects migration
                    if 'motion_effects' not in settings:
                        # Convert old single effect to list
                        old_effect = settings.get('motion_effect', 'Static')
                        settings['motion_effects'] = [old_effect]
                        # Remove old key
                        if 'motion_effect' in settings:
                            del settings['motion_effect']
                    
                    # Ensure motion_effects is always a list
                    if isinstance(settings.get('motion_effects'), str):
                        settings['motion_effects'] = [settings['motion_effects']]
                    
                    return settings
            except:
                pass
        
        # Default settings with motion_effects as list
        return {
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
            'caption_position': {'x': 0.5, 'y': 0.95},
            'caption_width_percent': 0.80,
            'video_resolution': '1080p'
        }

    def save_settings(self):
        """Save settings to config file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.settings, f, indent=2)
    
    def init_ui(self):
        """Initialize the UI"""
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
        settings_btn.setStyleSheet(Styles.BUTTON_SECONDARY)
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
        
        info_label = QLabel(
            "💡 Drag & drop folders here, or click button below • "
            "Each folder needs: voiceover audio + at least 1 image"
        )
        info_label.setStyleSheet("color: #666; font-style: italic; font-size: 12px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
        
        # Add folder button
        add_folder_btn = QPushButton("➕ Add Folders (or drag & drop)")
        add_folder_btn.setFixedHeight(70)
        add_folder_btn.setStyleSheet(Styles.BUTTON_ADD_FOLDER)
        add_folder_btn.clicked.connect(self.add_folders)
        main_layout.addWidget(add_folder_btn)
        
        # Queue section
        queue_label = QLabel("📋 Video Queue")
        queue_label.setFont(QFont('Arial', 16, QFont.Bold))
        queue_label.setStyleSheet("color: #1976D2;")
        main_layout.addWidget(queue_label)
        
        self.queue_list = QListWidget()
        self.queue_list.setStyleSheet(Styles.LIST_WIDGET)
        main_layout.addWidget(self.queue_list)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Start Batch Render")
        self.start_btn.setFixedHeight(55)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet(Styles.BUTTON_WARNING)
        self.start_btn.clicked.connect(self.start_rendering)
        
        clear_btn = QPushButton("🗑️ Clear Queue")
        clear_btn.setFixedHeight(55)
        clear_btn.setStyleSheet(Styles.BUTTON_DANGER)
        clear_btn.clicked.connect(self.clear_queue)
        
        button_layout.addWidget(self.start_btn, 3)
        button_layout.addWidget(clear_btn, 1)
        
        main_layout.addLayout(button_layout)
        
        # Status bar
        self.status_label = QLabel("✨ Ready to automate your videos!")
        self.status_label.setStyleSheet(
            "color: #666; padding: 10px; font-size: 12px; "
            "background-color: #f5f5f5; border-radius: 5px;"
        )
        main_layout.addWidget(self.status_label)
        
        central_widget.setLayout(main_layout)
        
        self.setStyleSheet(Styles.MAIN_WINDOW)
    
    def open_settings(self):
        """Open settings dialog"""
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
                QMessageBox.information(
                    self, "💡 Tip",
                    "Add a video folder first to access full preview settings!"
                )
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
        from PyQt5.QtWidgets import QApplication
        
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
        
        detected = processor.detect_files(folder_path)
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
            self.status_label.setText(
                f"✅ Added: {folder_name} ({num_images} image(s)) • "
                f"Total: {len(self.video_queue)} video(s)"
            )
    
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
        
        self.status_label.setText(
            f"🚀 Starting batch render: {len(self.video_queue)} videos "
            f"with {workers} parallel worker(s)..."
        )
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
        
        self.status_label.setText(
            f"🎉 All {len(self.video_queue)} video(s) complete! "
            "Check your project folders for MP4 files."
        )
    
    def dragEnterEvent(self, event):
        """Handle drag enter"""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if os.path.isdir(url.toLocalFile()):
                    event.acceptProposedAction()
                    self.setStyleSheet(Styles.MAIN_WINDOW_DRAG)
                    return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave"""
        self.setStyleSheet(Styles.MAIN_WINDOW)
    
    def dropEvent(self, event):
        """Handle drop"""
        self.setStyleSheet(Styles.MAIN_WINDOW)
        
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
                
                self.status_label.setText(
                    f"✅ Added {total_added} videos from {len(folders)} parent folder(s)"
                )
        
        event.acceptProposedAction()