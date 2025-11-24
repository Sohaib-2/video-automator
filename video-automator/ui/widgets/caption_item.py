"""
Draggable Caption Item
Text item that can be dragged around the preview
"""

from PyQt5.QtWidgets import QGraphicsTextItem
from PyQt5.QtCore import Qt


class DraggableCaptionItem(QGraphicsTextItem):
    """Draggable caption text item for preview"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFlag(QGraphicsTextItem.ItemIsMovable)
        self.setFlag(QGraphicsTextItem.ItemIsSelectable)
        self.setFlag(QGraphicsTextItem.ItemSendsGeometryChanges)
        self.setCursor(Qt.OpenHandCursor)
        
    def mousePressEvent(self, event):
        """Handle mouse press - change cursor to closed hand"""
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release - change cursor back to open hand"""
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)