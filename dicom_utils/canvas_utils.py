from ipyevents import Event
from ipywidgets import Textarea, VBox, Output
import time 
import logging
import numpy as np
import threading
from typing import List, Optional, Tuple, Callable
from dataclasses import dataclass

from contextlib import contextmanager

@dataclass
class WindowMeta:
    width: int
    height: int
    offset_x: int
    offset_y: int
    name: Optional[str] = None
    subwindows: Optional[List['WindowMeta']] = None

    def find_subwindow(self, x: int, y: int) -> Tuple[Optional['WindowMeta'], int, int]:
        """
        Recursively find the subwindow containing (x, y).
        Returns: (window, local_x, local_y)
        """
        if not (self.offset_x <= x < self.offset_x + self.width and 
                self.offset_y <= y < self.offset_y + self.height):
            return None, 0, 0
        
        local_x = x - self.offset_x
        local_y = y - self.offset_y
        
        if self.subwindows:
            for sub in self.subwindows:
                res_sub, res_lx, res_ly = sub.find_subwindow(x, y)
                if res_sub:
                    return res_sub, res_lx, res_ly
                    
        return self, local_x, local_y

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
            watched_events=['mousemove','mouseup','click', 'contextmenu','dragstart'],
            wait=int(1000/fps),
            prevent_default_action=True
        )
        self.z = self.w.slicer.state['z_index']

        self.events_fast = Event(
            source=self.w.im_w, 
            watched_events=['wheel'],
            prevent_default_action=True
        )

        # 2. Bind the event handler
        self.events_slow.on_dom_event(self._handle_slow)
        self.events_fast.on_dom_event(self._handle_fast)

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
            
          
            if event.get('buttons') == 1 and self.edit_flag and (event.get('ctrlKey') or event.get('metaKey')):
               self.w.slicer.mask[z,y,x]= 4
               
               hu_val = getattr(self.w, 'hu', None)
               hu_range = hu_val.value if hu_val else None
               
               self.w._update_image(self.w.slicer.state['z_index'], hu_range, \
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
 
        elif etype == 'click':
            self.msg.value = f"Clicked Data: x={x}, y={y}, slice={z}"
            if self.edit_flag and self.on_click_callback and (event.get('ctrlKey') or event.get('metaKey')):
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
        if etype == 'wheel':
            step = int(event.get('deltaY', 0) )
            step= max(min(step,1),-1)
            self.z = min(max(0,self.z + step), self.w.slicer.img.shape[0]-1)
            
            self.msg.value = f"Wheel  {step=} {self.z=}"
           
          
            with self.w.ignore_updates():
                self.w.set_widget_value(self.w.z_index, self.z )
            
            hu_val = getattr(self.w, 'hu', None)
            hu_range = hu_val.value if hu_val else None
                
            self.w._update_image( self.z, hu_range , mask_opacity=self.w.slicer.state['mask_opacity'], mask_on=self.w.slicer.state['mask_on'], only_mask=self.w.slicer.state['only_mask'])

        elif etype == 'mousemove':
            if event.get('buttons') == 2:
                return
            if 0 <= y < self.w.slicer.img.shape[1] and 0 <= x < self.w.slicer.img.shape[2]:
                hu_val = self.w.slicer.img[z, y, x]
                self.msg.value = f"Pixel: [{x}, {y}] | Slice: {z} | HU: {hu_val}"
            else:
                pass
        elif etype == 'click':
                self.msg.value = f"Clicked Data: x={x}, y={y}, slice={z}"
                if self.edit_flag and self.on_click_callback and (event.get('ctrlKey') or event.get('metaKey')):
                    self.on_click_callback(x, y, z)


        

        
        else:
            pass


    
    def display(self):
        from IPython.display import display
        display(self.container)

class UICanvas:
    def __init__(self, base_widget, window_meta: WindowMeta, event_callback: Callable, throttle_rate=20):
        self.w = base_widget
        self.meta = window_meta
        self.send = event_callback
        
        # Timing and Thresholds (matching JS)
        self.CLICK_MAX_DURATION = 0.3  # seconds
        self.DBL_CLICK_SPEED = 0.25   # seconds
        self.DRAG_THRESHOLD = 5
        
        self.throttle_interval = 1.0 / throttle_rate if throttle_rate > 0 else 0
        self.last_sent_timestamp = 0
        self.throttled_actions = {'drag_move', 'mouse_move'}
        
        # Trailing event logic
        self.trailing_timer = None
        self.last_event_data = None
        
        # State
        self.is_mouse_down = False
        self.is_dragging = False
        self.start_x = 0
        self.start_y = 0
        self.last_x = 0
        self.last_y = 0
        self.last_x_global = 0
        self.last_y_global = 0
        self.down_timestamp = 0
        self.last_mouse_up_timestamp = 0
        self.drag_button = None
        self.current_subwindow_name = None
        self.key_state = set()
        
        # Tracked Keys
        self.tracked_keys = ['KeyM', 'KeyC', 'KeyW', 'KeyA', 'KeyS', 'KeyD', 'KeyV', 'KeyR', 'ShiftLeft',
                             'ControlLeft', 'AltLeft','ArrowUp','ArrowLeft','ArrowRight','ArrowDown', 
                             'KeyU','KeyI','KeyO','KeyJ','KeyK','KeyL', 'KeyH', 'KeyG', 'KeyP', 'KeyB']
        
        # ipyevents
        self.events = Event(
            source=self.w.im_w, 
            watched_events=['mousedown', 'mouseup', 'mousemove', 'mouseleave', 'wheel', 'contextmenu', 'keydown', 'keyup'],
            prevent_default_action=True
        )
        self.events.on_dom_event(self._handle_event)
        
        # UI Container
        self.msg = Textarea(value='Ready', layout={'width': '100%', 'height': '100px'})
        self.container = VBox([self.w.widget, self.msg])

    def _handle_event(self, event):
        etype = event['type']
        now = time.time()
        
        # Coordinate Mapping
        x_global = int(event.get('dataX', 0))
        y_global = int(event.get('dataY', 0))
        
        # If event doesn't have coordinates (some key events), use last known
        if 'dataX' not in event and 'dataY' not in event:
            sub_win, x, y = self.meta.find_subwindow(self.last_x_global, self.last_y_global)
        else:
            sub_win, x, y = self.meta.find_subwindow(x_global, y_global)
            self.last_x_global = x_global
            self.last_y_global = y_global
            self.last_x = x
            self.last_y = y

        new_subwindow_name = sub_win.name if sub_win else None
        
        # Subwindow Enter/Leave
        if new_subwindow_name != self.current_subwindow_name:
            if self.current_subwindow_name:
                self.send_event('subwindow_leave', {}, self.current_subwindow_name, event)
            if new_subwindow_name:
                self.send_event('subwindow_enter', {'x': x, 'y': y}, new_subwindow_name, event)
            self.current_subwindow_name = new_subwindow_name

        if etype == 'mousedown':
            self.is_mouse_down = True
            self.is_dragging = False
            self.start_x = x
            self.start_y = y
            self.down_timestamp = now
            self.drag_button = event.get('button')
            self.send_event('mouse_down', {'x': x, 'y': y}, self.current_subwindow_name, event)

        elif etype == 'mousemove':
            if self.is_mouse_down and not self.is_dragging:
                dx = x - self.start_x
                dy = y - self.start_y
                distance = np.sqrt(dx*dx + dy*dy)
                if distance > self.DRAG_THRESHOLD:
                    self.is_dragging = True
                    self.send_event('drag_start', {'x': self.start_x, 'y': self.start_y, 'mouseButton': self.drag_button}, self.current_subwindow_name, event)
            
            if self.is_dragging:
                dx = x - self.start_x
                dy = y - self.start_y
                self.send_event('drag_move', {'x': x, 'y': y, 'dx': dx, 'dy': dy, 'mouseButton': self.drag_button}, self.current_subwindow_name, event)
                self.start_x = x
                self.start_y = y
            else:
                self.send_event('mouse_move', {'x': x, 'y': y}, self.current_subwindow_name, event)

        elif etype == 'mouseup':
            if self.is_dragging:
                self.send_event('drag_end', {'x': x, 'y': y, 'mouseButton': self.drag_button}, self.current_subwindow_name, event)
            elif self.is_mouse_down:
                duration = now - self.down_timestamp
                time_since_last_up = now - self.last_mouse_up_timestamp
                
                if duration < self.CLICK_MAX_DURATION:
                    if time_since_last_up < self.DBL_CLICK_SPEED:
                        self.send_event('double_click', {'x': x, 'y': y, 'mouseButton': event.get('button')}, self.current_subwindow_name, event)
                    else:
                        self.send_event('click', {'x': x, 'y': y, 'mouseButton': event.get('button')}, self.current_subwindow_name, event)
                self.last_mouse_up_timestamp = now
            
            self.is_mouse_down = False
            self.is_dragging = False
            self.drag_button = None

        elif etype == 'mouseleave':
            if self.current_subwindow_name:
                self.send_event('subwindow_leave', {}, self.current_subwindow_name, event)
                if self.is_dragging:
                    self.send_event('drag_end', {'x': self.start_x, 'y': self.start_y, 'mouseButton': self.drag_button}, self.current_subwindow_name, event)
                self.current_subwindow_name = None
                self.is_mouse_down = False
                self.is_dragging = False

        elif etype == 'wheel':
            scroll_delta = np.sign(event.get('deltaY', 0))
            self.send_event('mouse_wheel', {'deltaY': scroll_delta, 'x': x, 'y': y}, self.current_subwindow_name, event)

        elif etype == 'keydown':
            code = event.get('code')
            if code in self.tracked_keys and code not in self.key_state:
                self.key_state.add(code)
                self.send_event('key_down', {'pressedKeys': list(self.key_state)}, 'document', event)

        elif etype == 'keyup':
            code = event.get('code')
            if code in self.tracked_keys and code in self.key_state:
                self.key_state.remove(code)
                self.send_event('key_up', {'pressedKeys': list(self.key_state)}, 'document', event)

    def send_event(self, action, payload, plane_id, raw_event):
        now = time.time()
        
        # Cancel any pending trailing timer
        if self.trailing_timer:
            self.trailing_timer.cancel()
            self.trailing_timer = None

        modifier_mask = 0
        if raw_event.get('shiftKey'): modifier_mask |= 1
        if raw_event.get('ctrlKey'): modifier_mask |= 2
        if raw_event.get('altKey'): modifier_mask |= 4
        if raw_event.get('metaKey'): modifier_mask |= 8
        
        message = {
            'action': 'UIevents',
            'eventType': action,
            'planeId': plane_id or 'none',
            'modifierMask': modifier_mask,
            'timestamp': int(now * 1000),
            'x': payload.get('x', self.last_x),
            'y': payload.get('y', self.last_y),
            'dx': payload.get('dx'),
            'dy': payload.get('dy'),
            'mouseButton': payload.get('mouseButton'),
            'deltaY': payload.get('deltaY'),
            'pressedKeys': payload.get('pressedKeys')
        }

        if self.throttle_interval > 0 and action in self.throttled_actions:
            self.last_event_data = message
            if now - self.last_sent_timestamp >= self.throttle_interval:
                self._send_message(message)
                self.last_sent_timestamp = now
            
            # Always schedule a trailing event for throttled actions
            self.trailing_timer = threading.Timer(0.1, self._send_trailing_event)
            self.trailing_timer.start()
        else:
            self._send_message(message)

    def _send_trailing_event(self):
        if self.last_event_data:
            self._send_message(self.last_event_data)
            self.last_event_data = None

    def _send_message(self, message):
        # Log for debugging in UI
        log_line = f"[{message['eventType']}] @ {message['planeId']} | x: {message['x']}, y: {message['y']} | mod: {message['modifierMask']}"
        self.msg.value = log_line + "\n" + self.msg.value[:1000]
        self.send(message)

    def display(self):
        from IPython.display import display
        display(self.container)