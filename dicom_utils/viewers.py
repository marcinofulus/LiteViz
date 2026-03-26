import ipywidgets as widgets
from PIL import Image
import io

class SimpleImageViewer:
    """A simple viewer that displays an RGB(A) PIL image using ipywidgets, completely devoid of ipyevents."""
    def __init__(self, width=512, height=512, format='webp'):
        self.format = format
        self.width = width
        self.height = height
        
        self.image_widget = widgets.Image(
            format=self.format,
            width=self.width,
            height=self.height
        )
        self.widget = self.image_widget

    def set_image(self, pil_img):
        buf = io.BytesIO()
        pil_img.save(buf, format=self.format, quality=90)
        self.image_widget.value = buf.getvalue()


class InteractiveImageViewer:
    """An interactive viewer that displays an RGB(A) PIL image and emits generic events via callbacks."""
    def __init__(self, width=512, height=512, format='webp', fps=20, show_status=True):
        self.format = format
        self.width = width
        self.height = height
        self.show_status = show_status
        self.fps = fps
        
        # Generic Event Callbacks
        self.on_drag = None      # f(dx, dy, button)
        self.on_drag_start = None# f(x, y, button)
        self.on_drag_end = None  # f(button)
        self.on_click = None     # f(x, y, button)
        self.on_scroll = None    # f(delta)
        self.on_hover = None     # f(x, y)
        self.on_keydown = None   # f(key)
        
        self.image_widget = widgets.Image(
            format=self.format,
            width=self.width,
            height=self.height
        )
        self.status_label = widgets.Label(value="Viewer Ready")
        self.widget = widgets.VBox([self.image_widget, widgets.HBox([self.status_label])]) if show_status else self.image_widget
        
        self.mouse_x = 0
        self.mouse_y = 0
        self.is_dragging = False
        self.drag_start_pos = (0, 0)
        self.drag_button = None
        
        try:
            from ipyevents import Event
            self.d_event = Event(
                source=self.image_widget, 
                watched_events=[
                    'mousemove', 'wheel', 'mousedown', 'mouseup', 
                    'mouseleave', 'keydown', 'contextmenu', 'click'
                ],
                wait=int(1000/fps),
                prevent_default_action=True 
            )
            self.d_event.on_dom_event(self.handle_event)
        except ImportError:
            self.status_label.value = "ipyevents not installed. Interactivity disabled."
        
    def set_image(self, pil_img):
        buf = io.BytesIO()
        pil_img.save(buf, format=self.format, quality=90)
        self.image_widget.value = buf.getvalue()
        
    def update_status(self, text):
        if self.show_status:
            self.status_label.value = text

    def handle_event(self, event):
        if event['type'] == 'contextmenu': return

        # Robust Coordinate Scaling (Fixes resizing issues)
        if 'relativeX' in event:
            disp_w = event.get('boundingRectWidth', self.width)
            disp_h = event.get('boundingRectHeight', self.height)
            if disp_w > 0 and disp_h > 0:
                scale_x = self.width / disp_w
                scale_y = self.height / disp_h
                self.mouse_x = int(event['relativeX'] * scale_x)
                self.mouse_y = int(event['relativeY'] * scale_y)
                # Clamp
                self.mouse_x = max(0, min(self.width-1, self.mouse_x))
                self.mouse_y = max(0, min(self.height-1, self.mouse_y))

        etype = event['type']
        
        if etype == 'wheel' and self.on_scroll:
            self.on_scroll(event['deltaY'])
        elif etype == 'mousedown':
            self.is_dragging = True
            self.drag_start_pos = (self.mouse_x, self.mouse_y)
            self.drag_button = event['button']
            if self.on_drag_start:
                self.on_drag_start(self.mouse_x, self.mouse_y, self.drag_button)
        elif etype in ['mouseup', 'mouseleave']:
            was_dragging = self.is_dragging
            self.is_dragging = False
            if was_dragging and self.on_drag_end:
                self.on_drag_end(self.drag_button)
            self.drag_button = None
        elif etype == 'mousemove':
            if self.is_dragging and self.on_drag:
                dx = self.mouse_x - self.drag_start_pos[0]
                dy = self.mouse_y - self.drag_start_pos[1]
                self.on_drag(dx, dy, self.drag_button)
            elif not self.is_dragging and self.on_hover:
                self.on_hover(self.mouse_x, self.mouse_y)
        elif etype == 'click' and self.on_click:
             self.on_click(self.mouse_x, self.mouse_y, event.get('button', 0))
        elif etype == 'keydown' and self.on_keydown:
            self.on_keydown(event['key'])