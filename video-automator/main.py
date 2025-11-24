#!/usr/bin/env python3
"""
Video Automator - Main Entry Point
Batch video editor with automated captions and motion effects
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from ui.main_window import MainWindow


def main():
    """Launch the Video Automator application"""
    app = QApplication(sys.argv)
    app.setFont(QFont('Arial', 10))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()