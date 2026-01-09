from ipycanvas import MultiCanvas, hold_canvas
from ipywidgets import Output, VBox
import ipywidgets as widgets
import time 
from ipywidgets import HBox,VBox,Box, Textarea,Layout
import numpy as np 

def get_bounded_slice(point, delta, shape):
    """
    Returns a tuple of slice objects for i, j, k coordinates 
    clamped to the volume shape.
    """
    i, j, k = point
    
    i_min, i_max = max(0, i - delta), min(shape[0], i + delta + 1)
    j_min, j_max = max(0, j - delta), min(shape[1], j + delta + 1)
    k_min, k_max = max(0, k - delta), min(shape[2], k + delta + 1)
    
    # Return a numpy slice object
    return np.s_[i_min:i_max, j_min:j_max, k_min:k_max]
log_out = Output()
class AnnotationCanvas:
    def __init__(self, dicom_w, width=512, height=512):
        self.w = dicom_w
        self.msg = Textarea()
        self.width=width
        self.height = height
        # 1. Initialize Canvas
        self.canvas = MultiCanvas(2, width=width, height=height)
        self.canvas.layout = Layout(
            width=f"{self.width}px",
            height=f"{self.height}px",
            display='block' # Prevents inline-block spacing issues
        )
        self.bg_layer = self.canvas[0]
        self.fg_layer = self.canvas[1]
        
        # State Tracking
        self.is_drawing = False
        self.start_drawing_on_click = False
        self.run_ijk = False
        self.zoom = 1.0
        self.zoom_factor = 1.1
        self.is_zooming  = False
        self.last_pos = (0, 0)
        
        self.mask_label = 1         
        self.fg_layer.stroke_style = 'red'
        
        self.fg_layer.line_width = 2
        self.canvas[1].sync_image_data = True


        # 2. Bind Observers and Native Callbacks
        self.w.im_w.observe(self._update_background, names='value')
        
        self.canvas.on_mouse_down(self._on_mouse_down)
        self.canvas.on_mouse_move(self._on_mouse_move)
        self.canvas.on_mouse_up(self._on_mouse_up)
        self.canvas.on_touch_start(self._on_touch_start)
        self.canvas.on_touch_move(self._on_touch_move)
        
      

        self.canvas.on_key_down(self._on_keyboard_event)
        # Initial draw if image exists
        self._update_background()

    def _update_background(self, *args):
        with hold_canvas(self.bg_layer):
            self.bg_layer.clear()
            self.bg_layer.draw_image(self.w.im_w, 0, 0)

    def _on_keyboard_event(self, key, shift_key, ctrl_key, meta_key):
        
        self.msg.value = f"KEY PRESSED : {key=} {shift_key=}, {ctrl_key=}, {meta_key=}"
        
        x, y = self.last_pos 
       
        match key:
            case '.':
                self.zoom_by(zoom_factor=1.1)
            case ',':
                self.zoom_by(zoom_factor=0.9)
            case 'd': 
                self.start_drawing_on_click = not self.start_drawing_on_click
            
        
            case 's':
                self.is_drawing = False
                self.save_mask(label=self.mask_label)
                self.w.controls.update()
            case 'l':
                self.load_mask(label=self.mask_label)
            case 'c':
                self.canvas[1].clear()

            case 'p':
                self.run_ijk = not  self.run_ijk 
               
    @log_out.capture()            
    def save_mask(self, label=1):
        if self.w.mask is not None:
            time.sleep(.5)
            mask_at_current =  self.canvas[1].get_image_data()[...,0] # red channel!
            time.sleep(.5)
            self.w.mask[self.w.z_index.value,mask_at_current>0] =  label
    @log_out.capture()
    def load_mask(self, label=1):

        if self.w.mask is not None:
            mask_rgb = np.zeros( self.w.mask.shape[1:] + (4,), dtype=np.uint8)
            mask_rgb[...,0] = 255*(self.w.mask[self.w.z_index.value,...]  == label)
            mask_rgb[...,3] = 255*(self.w.mask[self.w.z_index.value,...]  == label)
            self.canvas[1].clear()
            self.canvas[1].put_image_data(mask_rgb,0,0)
        else:
            pass
    @log_out.capture()
    def draw_rect(self, i,j,k, label=1):
        d = 2
        if self.w.mask is not None:
            s = get_bounded_slice((i,j,k), d, self.w.mask.shape)
            self.w.mask[*s] = label
      
        
    def zoom_by(self, zoom_factor=1.1):
        # IMG_W/H are the 'buffer' dimensions (e.g. 512, 512)
        IMG_W, IMG_H = self.width, self.height
        
        # Update zoom state
        self.zoom *= zoom_factor
        self.zoom = min(max(self.zoom, 0.5), 4.0)
        z = self.zoom
        
        
    
        self.canvas.layout = Layout(
            width=f"{int(IMG_W * z)}px",
            height=f"{int(IMG_H * z)}px",
         
            display='block',
            object_fit='contain' 
        )
        
        self.msg.value = f"Zoom: {int(IMG_W * z)} x {int(IMG_H * z)}"

    def _on_mouse_down(self, x, y):
      
        self.last_pos = (x, y)
        

        self.is_zooming = True
        if self.start_drawing_on_click:
         
            self.is_drawing = True
        elif self.run_ijk:
            
            i,j,k = self.w.z_index.value,round(y), round(x)
            self.draw_rect(i,j,k, label=self.mask_label)
            self.w.controls.update()



            
        elif self.is_zooming:
            pass
        else:
            self.msg.value = f"Click at: {int(x)}, {int(y)} on {self.w.z_index.value}"

    def _on_mouse_move(self, x, y, **kwargs):
        dx = x - self.last_pos[0]
        dy = y - self.last_pos[1]

        if self.is_drawing:
            # Drawing on foreground
            with hold_canvas(self.fg_layer):
                self.fg_layer.stroke_line(self.last_pos[0], self.last_pos[1], x, y)
            self.last_pos = (x, y)
       
        else:
            # Just moving (hovering)
            self.msg.value = f"Hover on : {int(x)}, {int(y)} on {self.w.z_index.value}"

                

    def _on_mouse_up(self, x, y, **kwargs):
        self.is_drawing = False
        self.last_pos = (x, y)
        self.is_zooming = False
        
    def _on_mouse_out(self, x, y, **kwargs):
        self.is_drawing = False
        
    def _on_touch_start(self, touches):
       
        self.msg = (f"Touch Start: {len(touches)} fingers")

    def _on_touch_move(self, touches):
        self.msg.value = "Touch"

        if len(touches) == 2:
           t1, t2 = touches[0], touches[1]
           self.msg.value = "Two-finger move: T1({int(t1[0])},{int(t1[1])}) T2({int(t2[0])},{int(t2[1])})"

    # --- UI Accessor ---
    def show(self):
        return VBox([self.canvas, self.out])
