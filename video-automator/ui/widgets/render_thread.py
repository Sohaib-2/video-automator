"""
Render Thread
Background thread for video rendering without blocking UI
"""

from PyQt5.QtCore import QThread, pyqtSignal
from video_processing import BatchRenderer


class RenderThread(QThread):
    """Thread for rendering videos without blocking UI"""
    
    # Signals
    progress_update = pyqtSignal(str, int, str)  # folder_path, progress, status
    render_complete = pyqtSignal(str, bool, str)  # folder_path, success, output_path
    all_complete = pyqtSignal()
    
    def __init__(self, video_folders, settings, max_workers=2):
        """
        Initialize render thread
        
        Args:
            video_folders: List of video project folder paths
            settings: Video style settings
            max_workers: Number of parallel renders
        """
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