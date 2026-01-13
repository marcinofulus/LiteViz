import ipywidgets as widgets
from ipyevents import Event
from PIL import Image, ImageDraw
import io
import threading
import time
output = widgets.Output()

class InteractiveImageSlicer:
    """
    An interactive viewer that drives a DicomSlicer backend directly.
    Decoupled from the DicomWidget UI controls.
    """
    version = 'dev4'
    def __init__(self, dicom_slicer, debug_overlay=False, fps=10, show_status=True):
        
        self.format = 'webp'
        self.slicer = dicom_slicer  # The logic engine
        self.debug_overlay = debug_overlay
        self.show_status = show_status
        
        # Internal state
        self.radius = 30
        self.wl_sens   = 1
        self.hu0 = self.slicer.state['hu']

        self.P1 = 'z_index'
        self.P1_min = 'z_index_min'
        self.P1_max = 'z_index_max'
        
        # Load Initial Image from Slicer
        self.base_image = self.slicer.get_image().convert("RGB")
        self.width, self.height = self.base_image.size

        # --- UI Components ---
        
        # 1. Image Widget
        initial_bytes = self._pil_to_bytes(self.base_image)
        self.image_widget = widgets.Image(
            value=initial_bytes,
            format=self.format,
            width=self.width,
            height=self.height
        )
        
        # 2. Status Label (for mouse coordinates/actions)
        self.status_label = widgets.Label(value="Ready")
        self.status_box = widgets.HBox([self.status_label])

        # 3. Container
        self.container = widgets.VBox([self.image_widget, self.status_box])

        # --- Event Listener ---
        # Note: 'keydown' requires the widget to be focused (clicked)
        self.d_event = Event(
            source=self.image_widget, 
            watched_events=['mousemove', 'wheel', 'mousedown', 'mouseup', 'mouseleave', 'contextmenu', 'keydown'],
            wait=int(1000/fps),
            prevent_default_action=True 
        )
        self.d_event.on_dom_event(self.handle_event)

        # Interaction State
        self.mouse_x = 0
        self.mouse_y = 0
        self._is_updating = False
        
        # Dragging State
        self.is_dragging = False
        self.drag_start_pos = (0, 0)
        self.drag_button = None # 0 for Left, 2 for Right

        # Cross State
        self.cross_pos = None 

    def display(self):
        """Returns the container widget."""
        return self.container

    def _pil_to_bytes(self, img):
        buf = io.BytesIO()
        img.save(buf, format=self.format, quality=75) 
        return buf.getvalue()

    def update_status(self, text):
        """Updates the status label if feature is enabled."""
        if self.show_status and self.status_label:
            self.status_label.value = text

    # --- Drawing / Display Logic ---

    def _clear_cross_after_delay(self):
        """Waits then clears the cross and refreshes the view."""
        time.sleep(1.4)
        self.cross_pos = None
        self.refresh_display()

    def refresh_display(self,get_base=False):
        """Main method to draw the current state and push to widget."""
        if self._is_updating:
            return
        
        self._is_updating = True
        try:
            if get_base:
                self.base_image = self.slicer.get_image().convert("RGB")            
            
            temp_img = self.base_image.copy()
            
            # 2. Debug Overlay Logic
            if self.debug_overlay:
                draw = ImageDraw.Draw(temp_img)

                # Draw Hover Circle 
                if not self.is_dragging:
                    p1 = (self.mouse_x - self.radius, self.mouse_y - self.radius)
                    p2 = (self.mouse_x + self.radius, self.mouse_y + self.radius)
                    draw.ellipse([p1, p2], outline='#00FF00', width=2)

                # Draw Drag Lines
                if self.is_dragging:
                    color = 'white' if self.drag_button == 0 else 'red'
                    draw.line([self.drag_start_pos, (self.mouse_x, self.mouse_y)], fill=color, width=3)

                # Draw Cross
                if self.cross_pos:
                    cx, cy = self.cross_pos
                    size = 15
                    draw.line([(cx - size, cy - size), (cx + size, cy + size)], fill='blue', width=4)
                    draw.line([(cx - size, cy + size), (cx + size, cy - size)], fill='blue', width=4)

            # 3. Push to Widget
            self.image_widget.value = self._pil_to_bytes(temp_img)

        finally:
            self._is_updating = False

    # --- Event Dispatcher ---

    def handle_event(self, event):
        etype = event['type']
        
        if etype == 'contextmenu':
            return
        
        # if 'relativeX' in event:
        #     self.mouse_x = event['relativeX']
        #     self.mouse_y = event['relativeY']

        if 'dataX' in event:
            self.mouse_x = event['dataX']
            self.mouse_y = event['dataY']
          

        # Dispatch
        if etype == 'wheel':
            self._on_wheel(event)
        elif etype == 'mousedown':
            self._on_drag_start(event)
        elif etype in ['mouseup', 'mouseleave']:
            self._on_drag_end(event)
        elif etype == 'mousemove':
            self._on_drag_move(event)
        elif etype == 'keydown':
            self._on_keydown(event)

    # --- Action Callbacks ---

    def _on_wheel(self, event):
        """Handle Slice Changing."""
        delta = event['deltaY']
        
        # 1. Get Limits
        min_z = self.slicer.state[self.P1_min]
        max_z = self.slicer.state[self.P1_max]
        current_z = self.slicer.state[self.P1]
        
        # 2. Calculate New Z
        step = 1 if delta > 0 else -1
        new_z = max(min_z, min(max_z, current_z + step))
        
        if new_z != current_z:
            # 3. Update Slicer
            self.slicer.update_state(**{self.P1: new_z})
            
            # 4. Update Status
            self.update_status(f"Slice: {new_z}/{max_z}")
            
            # 5. Fetch new image & Refresh
            self.base_image = self.slicer.get_image().convert("RGB")
            self.refresh_display(get_base=True)

    def _on_drag_start(self, event):
        self.is_dragging = True
        self.drag_start_pos = (self.mouse_x, self.mouse_y)
        self.drag_button = event['button']

        if  self.drag_button ==2:
            self.hu0 = self.slicer.state['hu']
        
        # Trigger temporary crosshair
        self.cross_pos = (self.mouse_x, self.mouse_y)
        threading.Thread(target=self._clear_cross_after_delay).start()
        
        self.update_status(f"Drag Start: {self.drag_start_pos} | Button: {self.drag_button}")
        self.refresh_display()
    output.capture()
    def _on_drag_move(self, event):

        if self.is_dragging:
            self.update_status(f"Dragging: {self.drag_start_pos} -> ({self.mouse_x}, {self.mouse_y})")

            if self.drag_button == 2:
    
                s = self.wl_sens    
                dx = (self.mouse_x-self.drag_start_pos[0])
                dy = (self.mouse_y-self.drag_start_pos[1])
                a,b = self.hu0
                a,b = int(a+s*dx -s*dy), int(b+s*dx + s*dy)
                
                self.slicer.state['hu'] = a, b
        
                self.refresh_display(get_base=True)

            else:
                self.refresh_display(get_base=False)

            
        else:
            try:
                HU = self.slicer.get_value_at_jk(self.mouse_y, self.mouse_x)
            except:
                HU='ops'
            self.update_status(f"Hover: ({self.mouse_x}, {self.mouse_y}) HU: {HU}")
            self.refresh_display(get_base=False)

       
        

    def _on_drag_end(self, event):
        if self.is_dragging:
            self.update_status(f"Drag End: ({self.mouse_x}, {self.mouse_y})")
            
        self.is_dragging = False
        self.refresh_display()

    def _on_keydown(self, event):
        print(event)
        key = event['key']
        
        current_z = self.slicer.state[self.P1]
        max_z = self.slicer.state[self.P1_max]
        new_z = current_z

        if key == 'ArrowUp':
            new_z = min(max_z, current_z + 1)
        elif key == 'ArrowDown':
            new_z = max(0, current_z - 1)
        elif key == 'm':
            self.slicer.state['mask_on'] = not self.slicer.state['mask_on']
            self.refresh_display(get_base=True)
        else:
            pass
            
        if new_z != current_z:
            self.slicer.update_state(**{self.P1: new_z})
            self.base_image = self.slicer.get_image().convert("RGB")
            self.update_status(f"Key: {key} | Slice: {new_z}")
            self.refresh_display(get_base=True)
        else:
            self.update_status(f"Key Pressed : {key}")

