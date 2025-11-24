"""
Video List Item Widget
Custom widget for displaying videos in the render queue
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtGui import QFont
from ui.styles import Styles


class VideoListItem(QWidget):
    """Custom widget for video queue items"""
    
    def __init__(self, folder_name, num_images=2, parent=None):
        """
        Initialize video list item
        
        Args:
            folder_name: Name of the video project folder
            num_images: Number of images in the project
            parent: Parent widget
        """
        super().__init__(parent)
        self.folder_name = folder_name
        self.num_images = num_images
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Folder name with image count
        name_label = QLabel(
            f"📁 {self.folder_name} "
            f"({self.num_images} image{'s' if self.num_images != 1 else ''})"
        )
        name_label.setFont(QFont('Arial', 11, QFont.Bold))
        layout.addWidget(name_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(Styles.PROGRESS_BAR)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("⏳ Queued")
        self.status_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def update_progress(self, value, status="Processing..."):
        """Update progress bar and status"""
        self.progress_bar.setValue(value)
        self.status_label.setText(f"⚙️ {status}")
    
    def set_complete(self):
        """Mark item as complete"""
        self.progress_bar.setValue(100)
        self.progress_bar.setStyleSheet(Styles.PROGRESS_BAR_COMPLETE)
        self.status_label.setText("✅ Complete!")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
    
    def set_error(self, error_msg="Error"):
        """Mark item as error"""
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(Styles.PROGRESS_BAR_ERROR)
        self.status_label.setText(f"❌ {error_msg}")
        self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")