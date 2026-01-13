from ipyevents import Event
from ipywidgets import Textarea, VBox, Output
import time 

from contextlib import contextmanager
@contextmanager
def silence_widget(widget):
    """Temporarily removes all observers from a widget and restores them after."""
    # Save current observers
    saved_observers = widget._trait_notifiers.copy()
    try:
        # Clear observers
        widget._trait_notifiers = {}
        yield
    finally:
        # Restore observers
        widget._trait_notifiers = saved_observers   
        
        
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
output = Output()
DATA_LIMITS = (-2000,3000)

class AnnotationCanvas:
    def __init__(self, dicom_widget, edit_flag=False, on_click_callback=None, fps=5, logger=None):

        self.logger = logger or logging.getLogger(__name__)
        
        self.w = dicom_widget  
        self.edit_flag = edit_flag
        self.on_click_callback = on_click_callback
        
        self._last_data_pos = None
        self._last_data_pos_btn2 = None
        
        # UI for feedback
        self.msg = Textarea(
            value='System Ready', 
            layout={'width': '100%', 'height': '60px'}
        )
        
        # 1. Create the Event watcher
        # 'wait' in ms. 200ms = 5fps. 
        # throttle_or_debounce='throttle' ensures events are dropped, not queued.
        self.events_slow = Event(
            source=self.w.im_w, 
            watched_events=['wheel', 'mousemove','mouseup','click', 'contextmenu','dragstart'],
            wait=int(1000/fps),
            prevent_default_action=True
        )
        self.z = self.w.slicer.state['z_index']

        #self.events_fast = Event(
        #source=self.w.im_w, 
        #    watched_events=['click', 'contextmenu'],
        #    prevent_default_action=True
        #)

        # 2. Bind the event handler
        self.events_slow.on_dom_event(self._handle_slow)
        #self.events_fast.on_dom_event(self._handle_fast)

        # 3. Layout - ensuring the image fills its container properly
        self.w.im_w.layout.max_width = '100%'
        self.w.im_w.layout.height = 'auto'
        
        self.container = VBox([self.w.widget, self.msg])
        self.counter = 0
        self.last_msg = time.time()



        
    
    @output.capture()
    def _handle_slow(self, event):
      
        etype = event['type']
       
        x = int(event.get('dataX', 0))
        y = int(event.get('dataY', 0))
        z = self.w.slicer.state['z_index']

        if etype == 'mousemove':
            
          
            if event.get('buttons') == 1:
               self.w.slicer.mask[z,y,x]= 4
               self.w._update_image(self.w.slicer.state['z_index'],  self.w.hu.value, \
                                mask_opacity=self.w.slicer.state['mask_opacity'], mask_on=self.w.slicer.state['mask_on'], only_mask=self.w.slicer.state['only_mask'])
        
                  
                
            if event.get('buttons') == 2:
                
                if self._last_data_pos_btn2 is not None:
                    dx = x - self._last_data_pos_btn2[0]
                    dy = y - self._last_data_pos_btn2[1]
                    
                    low, high = self.w.slicer.state['hu']
                   
                    sensitivity = 1
                    if abs(dx) > abs(dy):
                        dy = 0
                    else:
                        dx=0
                    offset = dy * sensitivity
                    spread = dx * sensitivity
            
                        
                    new_min = low + offset - (spread / 2)
                    new_max = high + offset + (spread / 2)
            
                    if new_max - new_min < 1: 
                        new_max = new_min + 1
            
                
                    new_min = max(DATA_LIMITS[0], new_min)
                    new_max = min(DATA_LIMITS[1], new_max)

                    self.msg.value = f"HU changer {dx=}, {dy=} {event.get('buttons')=} {self.w.slicer.state['hu']} {(round(new_min),round(new_max))=}"
                    
                  
                    with self.w.ignore_updates():
                        self.w.set_widget_value(self.w.hu,(new_min,new_max) )

                    self.w._update_image( self.w.slicer.state['z_index'], (new_min,new_max) , mask_opacity=self.w.slicer.state['mask_opacity'], mask_on=self.w.slicer.state['mask_on'], only_mask=self.w.slicer.state['only_mask'])

                
                else:
                    self._last_data_pos_btn2 = (x, y)
           
            else:
                self._last_data_pos_btn2 = None
   
                if 0 <= y < self.w.slicer.img.shape[1] and 0 <= x < self.w.slicer.img.shape[2]:
                    hu_val = self.w.slicer.img[z, y, x]
                    self.msg.value = f"Pixel: [{x}, {y}] | Slice: {z} | HU: {hu_val}"

        elif etype == 'mouseup':
            self._last_data_pos_btn2 = None

    
        elif etype == 'contextmenu':
            pass
               
        elif etype == 'wheel':
            step = int(event.get('deltaY', 0) )
            step= max(min(step,1),-1)
            self.z = min(max(0,self.z + step), self.w.slicer.img.shape[0]-1)
            
            self.msg.value = f"Wheel  {step=} {self.z=}"
           
          
            with self.w.ignore_updates():
                self.w.set_widget_value(self.w.z_index, self.z )
                
            self.w._update_image( self.z, self.w.slicer.state['hu'] , mask_opacity=self.w.slicer.state['mask_opacity'], mask_on=self.w.slicer.state['mask_on'], only_mask=self.w.slicer.state['only_mask'])
 
        elif etype == 'click':
            self.msg.value = f"Clicked Data: x={x}, y={y}, slice={z}"
            if self.edit_flag and self.on_click_callback:
                self.on_click_callback(x, y, z)

        else:
            pass

        self.logger.debug(f'handle_slow {self.z=} {etype=}')
      
    @output.capture()
    def _handle_fast(self, event):

        etype = event['type']
            
          
        x = int(event.get('dataX', 0))
        y = int(event.get('dataY', 0))
        
      

        z = self.w.slicer.state['z_index']

        self.logger.debug(f'handle fast: {etype=} {x} {y} {z}')
        if etype == 'mousemove':
            if event.get('buttons') == 2:
                return
            if 0 <= y < self.w.slicer.img.shape[1] and 0 <= x < self.w.slicer.img.shape[2]:
                hu_val = self.w.slicer.img[z, y, x]
                self.msg.value = f"Pixel: [{x}, {y}] | Slice: {z} | HU: {hu_val}"
            else:
                pass
        elif etype == 'click':
                self.msg.value = f"Clicked Data: x={x}, y={y}, slice={z}"
                if self.edit_flag and self.on_click_callback:
                    self.on_click_callback(x, y, z)


        

        
        else:
            pass


    
    def display(self):
        from IPython.display import display
        display(self.container)