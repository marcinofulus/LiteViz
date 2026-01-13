import ipywidgets as widgets
from ipyevents import Event
from PIL import Image, ImageDraw
import io
import threading
import time

# --- BASE CLASS: Pure UI & Interaction Logic ---
class InteractiveViewer:
    """
    A generic interactive image viewer. 
    Handles: Widget creation, Event listening, Coordinate scaling, Debug overlays.
    Does NOT know about DICOM or Slicers.
    """
    def __init__(self, width=512, height=512, debug_overlay=False, fps=10, show_status=True):
        self.format = 'webp'
        self.debug_overlay = debug_overlay
        self.show_status = show_status
        self.fps = fps
        
        # Internal Interaction State
        self.width = width
        self.height = height
        self.mouse_x = 0
        self.mouse_y = 0
        self.is_dragging = False
        self.drag_start_pos = (0, 0)
        self.drag_button = None
        self.cross_pos = None 
        self.radius = 30 # For hover circle
        self._is_updating = False

        # 1. Base Image (Default: Gray Placeholder)
        self.base_image = self._create_dummy_image(width, height)

        # 2. UI Components
        self.image_widget = widgets.Image(
            value=self._pil_to_bytes(self.base_image),
            format=self.format,
            width=self.width,
            height=self.height
        )
        self.status_label = widgets.Label(value="Viewer Ready")
        self.container = widgets.VBox([self.image_widget, widgets.HBox([self.status_label])])

        # 3. Event Listener (Robust Setup)
        self.d_event = Event(
            source=self.image_widget, 
            watched_events=[
                'mousemove', 'wheel', 'mousedown', 'mouseup', 
                'mouseleave', 'keydown', 'contextmenu'
            ],
            wait=int(1000/fps),
            prevent_default_action=True 
        )
        self.d_event.on_dom_event(self.handle_event)

    def display(self):
        return self.container

    def _create_dummy_image(self, w, h):
        """Creates a gray testbench image."""
        return Image.new("RGB", (w, h), color=(100, 100, 100))

    def _pil_to_bytes(self, img):
        buf = io.BytesIO()
        img.save(buf, format=self.format, quality=75) 
        return buf.getvalue()

    def update_status(self, text):
        if self.show_status:
            self.status_label.value = text

    # --- View Logic (Overlays) ---

    def refresh_display(self, fetch_new_base=False):
        """
        Refreshes the view.
        Args:
            fetch_new_base: If True, calls self._get_updated_base_image() 
                            to get new content from the backend.
        """
        if self._is_updating: return
        self._is_updating = True
        
        try:
            # 1. Optional: Fetch new content from child class
            if fetch_new_base:
                self.base_image = self._get_updated_base_image()

            # 2. Prepare Overlay
            # We copy so we don't draw permanently on the base image
            temp_img = self.base_image.copy()
            
            if self.debug_overlay:
                self._draw_overlays(temp_img)

            # 3. Push to Widget
            self.image_widget.value = self._pil_to_bytes(temp_img)
        finally:
            self._is_updating = False

    def _draw_overlays(self, image):
        """Draws the standard debug shapes."""
        draw = ImageDraw.Draw(image)
        
        # Hover Circle
        if not self.is_dragging:
            p1 = (self.mouse_x - self.radius, self.mouse_y - self.radius)
            p2 = (self.mouse_x + self.radius, self.mouse_y + self.radius)
            draw.ellipse([p1, p2], outline='#00FF00', width=2)

        # Drag Line
        if self.is_dragging:
            color = 'white' if self.drag_button == 0 else 'red'
            draw.line([self.drag_start_pos, (self.mouse_x, self.mouse_y)], fill=color, width=3)

        # Crosshair
        if self.cross_pos:
            cx, cy = self.cross_pos
            size = 15
            draw.line([(cx - size, cy - size), (cx + size, cy + size)], fill='blue', width=4)
            draw.line([(cx - size, cy + size), (cx + size, cy - size)], fill='blue', width=4)

    def _clear_cross_after_delay(self):
        time.sleep(0.5) # Shorter delay usually feels snappier
        self.cross_pos = None
        self.refresh_display(fetch_new_base=False)

    # --- Virtual Methods (To be overridden by Child) ---
    
    def _get_updated_base_image(self):
        """Child should return the current PIL image from logic backend."""
        return self.base_image # Default: return what we have

    def _on_wheel(self, event): pass
    def _on_keydown(self, event): pass

    # --- Event Handling ---

    def handle_event(self, event):
        if event['type'] == 'contextmenu': return # Block menu

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

        # Dispatch
        etype = event['type']
        if etype == 'wheel': self._on_wheel(event)
        elif etype == 'mousedown': self._on_drag_start(event)
        elif etype in ['mouseup', 'mouseleave']: self._on_drag_end(event)
        elif etype == 'mousemove': self._on_drag_move(event)
        elif etype == 'keydown': self._on_keydown(event)

    # --- Default Drag Logic ---
    
    def _on_drag_start(self, event):
        self.is_dragging = True
        self.drag_start_pos = (self.mouse_x, self.mouse_y)
        self.drag_button = event['button']
        
        self.cross_pos = (self.mouse_x, self.mouse_y)
        threading.Thread(target=self._clear_cross_after_delay).start()
        
        self.update_status(f"Drag Start: {self.drag_start_pos}")
        self.refresh_display()

    def _on_drag_move(self, event):
        # Base implementation just updates status
        if self.is_dragging:
            self.update_status(f"Dragging: {self.drag_start_pos} -> ({self.mouse_x}, {self.mouse_y})")
        else:
            self.update_status(f"Hover: ({self.mouse_x}, {self.mouse_y})")
        self.refresh_display()

    def _on_drag_end(self, event):
        self.is_dragging = False
        self.refresh_display()


# --- DERIVATIVE CLASS: The Slicer Implementation ---

class InteractiveSlicer(InteractiveViewer):
    """
    Connects the generic InteractiveViewer to a DicomSlicer backend.
    """
    def __init__(self, dicom_slicer, **kwargs):
        # 1. Initialize Slicer Logic
        self.slicer = dicom_slicer
        
        # Get dimensions from the slicer image
        initial_img = self.slicer.get_image()
        w, h = initial_img.size
        
        # 2. Initialize Base Class
        super().__init__(width=w, height=h, **kwargs)
        
        # 3. Setup Slicer Specific State
        self.base_image = initial_img.convert("RGB")
        self.wl_sens = 1
        self.hu0 = self.slicer.state.get('hu', (0,0)) # Safety get
        
        self.P1 = 'z_index'
        self.P1_min = 'z_index_min'
        self.P1_max = 'z_index_max'

    # --- Overrides ---

    def _get_updated_base_image(self):
        """Fetch fresh image from Slicer."""
        return self.slicer.get_image().convert("RGB")

    def _on_wheel(self, event):
        delta = event['deltaY']
        min_z = self.slicer.state[self.P1_min]
        max_z = self.slicer.state[self.P1_max]
        current_z = self.slicer.state[self.P1]
        
        step = 1 if delta > 0 else -1
        new_z = max(min_z, min(max_z, current_z + step))
        
        if new_z != current_z:
            self.slicer.update_state(**{self.P1: new_z})
            self.update_status(f"Slice: {new_z}/{max_z}")
            self.refresh_display(fetch_new_base=True)

    def _on_drag_start(self, event):
        # Call base to set flags/draw cross
        super()._on_drag_start(event)
        
        # Capture current HU if Right Click
        if self.drag_button == 2:
            self.hu0 = self.slicer.state['hu']

    def _on_drag_move(self, event):
        if self.is_dragging:
            if self.drag_button == 2:
                # --- Right Click: Window/Level Logic ---
                s = self.wl_sens    
                dx = (self.mouse_x - self.drag_start_pos[0])
                dy = (self.mouse_y - self.drag_start_pos[1])
                
                a, b = self.hu0
                # Logic: dx widens window, dy shifts level
                new_a = int(a + s*dx - s*dy)
                new_b = int(b + s*dx + s*dy)
                
                self.slicer.state['hu'] = (new_a, new_b)
                self.update_status(f"W/L: {new_a}, {new_b}")
                self.refresh_display(fetch_new_base=True) # Must fetch new pixels!
            else:
                # --- Left Click: Just draw line (Base logic) ---
                super()._on_drag_move(event)
        else:
            # --- Hover Logic: Show HU Value ---
            try:
                # Note: Slicer expects (y, x) usually
                val = self.slicer.get_value_at_jk(self.mouse_y, self.mouse_x)
            except Exception:
                val = 'N/A'
                
            self.update_status(f"Hover: ({self.mouse_x}, {self.mouse_y}) | Val: {val}")
            # Do NOT fetch base here, just redraw overlay
            self.refresh_display(fetch_new_base=False)

    def _on_keydown(self, event):
        key = event['key']
        current_z = self.slicer.state[self.P1]
        max_z = self.slicer.state[self.P1_max]
        new_z = current_z

        if key == 'ArrowUp':
            new_z = min(max_z, current_z + 1)
        elif key == 'ArrowDown':
            new_z = max(0, current_z - 1)
        elif key == 'm':
            # Toggle Mask
            self.slicer.state['mask_on'] = not self.slicer.state['mask_on']
            self.update_status(f"Mask: {self.slicer.state['mask_on']}")
            self.refresh_display(fetch_new_base=True)
            return

        if new_z != current_z:
            self.slicer.update_state(**{self.P1: new_z})
            self.update_status(f"Slice: {new_z}")
            self.refresh_display(fetch_new_base=True)