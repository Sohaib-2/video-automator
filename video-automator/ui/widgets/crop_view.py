"""
Image Crop View Widget
Interactive 16:9 crop/zoom view with draggable image and caption positioning
"""

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont
from .caption_item import DraggableCaptionItem


class ImageCropView(QGraphicsView):
    """Interactive image crop/zoom view for 16:9 ratio with draggable image"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Setup view
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
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

        # Safe zone boundaries (10% margins on each side)
        # For 1920px width: 192px left + 192px right = 1536px safe area
        self.SAFE_MARGIN_PERCENT = 0.10
        self.safe_zone_left = None
        self.safe_zone_right = None
        self._add_safe_zone_guides()
        
        # Zoom level
        self.zoom_level = 1.0
        self.min_zoom = 0.3
        self.max_zoom = 5.0
        
        # Caption overlay
        self.caption_item = None

    def _add_safe_zone_guides(self):
        """Add visual guides showing the safe zone boundaries (10% margins)"""
        crop_rect = self.crop_frame.rect()
        margin_px = crop_rect.width() * self.SAFE_MARGIN_PERCENT  # 192px for 1920px width

        # Left boundary line
        self.safe_zone_left = QGraphicsRectItem(
            crop_rect.x() + margin_px,
            crop_rect.y(),
            0,  # No width - just a line
            crop_rect.height()
        )
        self.safe_zone_left.setPen(QPen(QColor(0, 255, 0, 150), 2, Qt.DashLine))
        self.safe_zone_left.setZValue(101)  # Above crop frame
        self.scene.addItem(self.safe_zone_left)

        # Right boundary line
        self.safe_zone_right = QGraphicsRectItem(
            crop_rect.x() + crop_rect.width() - margin_px,
            crop_rect.y(),
            0,  # No width - just a line
            crop_rect.height()
        )
        self.safe_zone_right.setPen(QPen(QColor(0, 255, 0, 150), 2, Qt.DashLine))
        self.safe_zone_right.setZValue(101)  # Above crop frame
        self.scene.addItem(self.safe_zone_right)

    def resizeEvent(self, event):
        """Maintain 16:9 aspect ratio on resize"""
        super().resizeEvent(event)
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
        
        # Make image draggable
        self.image_item.setFlag(QGraphicsPixmapItem.ItemIsMovable, True)
        self.image_item.setFlag(QGraphicsPixmapItem.ItemIsSelectable, True)
        self.image_item.setCursor(Qt.OpenHandCursor)
        
        # Auto-fit to fill 16:9 frame perfectly
        self.auto_fit_to_frame()
        
        # Fit view to show crop frame properly
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
        
        # Clamp values to valid ranges
        x = max(0, min(x, orig_width - 1))
        y = max(0, min(y, orig_height - 1))
        
        # Ensure crop doesn't exceed image boundaries
        if x + w > orig_width:
            w = orig_width - x
        if y + h > orig_height:
            h = orig_height - y
        
        # Ensure minimum size
        w = max(100, w)
        h = max(100, h)
        
        return {
            'x': int(x),
            'y': int(y),
            'width': int(w),
            'height': int(h)
        }
    
    def add_caption(
        self,
        text: str,
        font: QFont,
        color: QColor,
        bg_color: QColor,
        bg_opacity: int,
        has_background: bool,
        has_outline: bool = None,
        outline_color: QColor = None,
        outline_width: int = 3
    ):
        """Add draggable caption to preview with outline support and safe zone constraints"""
        if self.caption_item:
            self.scene.removeItem(self.caption_item)

        self.caption_item = DraggableCaptionItem(text)

        # Parse font correctly (handle "Arial Bold" format like the video renderer does)
        font_name = font.family()
        font_size = font.pointSize()
        is_bold = False

        # Check if font name contains "Bold" and extract base font name
        if ' Bold' in font_name:
            font_name = font_name.replace(' Bold', '')
            is_bold = True

        # Create properly parsed font
        parsed_font = QFont(font_name, font_size)
        if is_bold:
            parsed_font.setBold(True)

        self.caption_item.setFont(parsed_font)
        self.caption_item.setDefaultTextColor(color)

        # Handle outline - default to opposite of background if not specified
        if has_outline is None:
            has_outline = not has_background

        # Calculate max width based on safe zones (80% of screen width = 1536px for 1920px)
        # This matches the video rendering which uses max 30 chars and 10% margins
        crop_rect = self.crop_frame.rect()
        margin_px = crop_rect.width() * self.SAFE_MARGIN_PERCENT
        max_caption_width = crop_rect.width() - (2 * margin_px)  # 1536px

        # Also enforce word wrapping in HTML to match video behavior
        # Max ~30 characters per line to match video caption splitting

        # Use parsed font properties for HTML rendering
        font_weight = 'bold' if is_bold else 'normal'

        if has_background:
            # Create HTML with background and max-width constraint
            html = f"""
            <div style='background-color: rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, {bg_opacity/100.0});
                        padding: 10px; border-radius: 5px; max-width: {int(max_caption_width)}px;
                        word-wrap: break-word; overflow-wrap: break-word;'>
                <span style='color: {color.name()}; font-family: {font_name}; font-size: {font_size}pt; font-weight: {font_weight};'>
                    {text}
                </span>
            </div>
            """
        elif has_outline and outline_color:
            # No background but with outline and max-width
            html = f"""
            <div style='max-width: {int(max_caption_width)}px; word-wrap: break-word; overflow-wrap: break-word;'>
                <span style='color: {color.name()}; font-family: {font_name}; font-size: {font_size}pt; font-weight: {font_weight};
                             text-shadow:
                                 -{outline_width}px -{outline_width}px 0 {outline_color.name()},
                                 {outline_width}px -{outline_width}px 0 {outline_color.name()},
                                 -{outline_width}px {outline_width}px 0 {outline_color.name()},
                                 {outline_width}px {outline_width}px 0 {outline_color.name()},
                                 2px 2px 4px rgba(0,0,0,0.5);'>
                    {text}
                </span>
            </div>
            """
        else:
            # No background, no outline - just text with basic shadow and max-width
            html = f"""
            <div style='max-width: {int(max_caption_width)}px; word-wrap: break-word; overflow-wrap: break-word;'>
                <span style='color: {color.name()}; font-family: {font_name}; font-size: {font_size}pt; font-weight: {font_weight};
                             text-shadow: 2px 2px 4px rgba(0,0,0,0.8);'>
                    {text}
                </span>
            </div>
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
        
        # Use LARGER zoom to ensure frame is completely filled
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