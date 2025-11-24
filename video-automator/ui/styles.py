"""
UI Stylesheets
Centralized style definitions for the application
"""


class Styles:
    """Application stylesheet definitions"""
    
    BUTTON_PRIMARY = """
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:disabled {
            background-color: #ccc;
            color: #999;
        }
    """
    
    BUTTON_SECONDARY = """
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
    """
    
    BUTTON_DANGER = """
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
    """
    
    BUTTON_WARNING = """
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
    """
    
    BUTTON_ADD_FOLDER = """
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
    """
    
    BUTTON_ZOOM_IN = """
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
    """
    
    BUTTON_ZOOM_OUT = """
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
    """
    
    BUTTON_RESET = """
        QPushButton {
            background-color: #FF9800;
            color: white;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #F57C00;
        }
    """
    
    BUTTON_AUTO_FIT = """
        QPushButton {
            background-color: #2196F3;
            color: white;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
    """
    
    BUTTON_SAVE = """
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
    """
    
    BUTTON_CANCEL = """
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
    """
    
    PROGRESS_BAR = """
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
    """
    
    PROGRESS_BAR_COMPLETE = """
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
    """
    
    PROGRESS_BAR_ERROR = """
        QProgressBar {
            border: 2px solid #f44336;
            border-radius: 5px;
            text-align: center;
            background-color: #ffebee;
        }
    """
    
    LIST_WIDGET = """
        QListWidget {
            border: 2px solid #ddd;
            border-radius: 8px;
            background-color: #fafafa;
        }
        QListWidget::item {
            border-bottom: 1px solid #eee;
            padding: 5px;
        }
    """
    
    MAIN_WINDOW = "QMainWindow { background-color: white; }"
    
    MAIN_WINDOW_DRAG = "QMainWindow { background-color: #E3F2FD; }"