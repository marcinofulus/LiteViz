import ipywidgets as widgets
from .viewers import InteractiveImageViewer, SimpleImageViewer
from .controls import DicomControls
from .dicom_utils import DicomSlicer

class InteractiveDicomWidget:
    """An advanced widget for interactively displaying DICOM slices,
    combining a DicomSlicer, UI controls, and an InteractiveImageViewer."""

    def __init__(self, dicom_slicer=None, image_array=None, mask=None, fps=20, show_status=True, **kwargs):
        
        # 1. Init Slicer (Math/Data Block)
        if dicom_slicer:
            self.slicer = dicom_slicer
        elif image_array is not None:
            self.slicer = DicomSlicer(image_array, mask=mask, **kwargs)
        else:
            raise ValueError("Must provide either a dicom_slicer or an image_array.")
            
        # 2. Init UI Controls
        self.controls = DicomControls(max_z=self.slicer.state['z_index_max'], on_change=self._on_controls_change)
        
        # 3. Init Viewer
        init_img = self.slicer.get_image()
        self.viewer = InteractiveImageViewer(
            width=init_img.width, 
            height=init_img.height,
            fps=fps,
            show_status=show_status
        )
        
        # 4. Wire Viewer Events to Logic
        self.viewer.on_scroll = self._handle_scroll
        self.viewer.on_drag_start = self._handle_drag_start
        self.viewer.on_drag = self._handle_drag
        self.viewer.on_hover = self._handle_hover
        self.viewer.on_keydown = self._handle_keydown
        
        # State
        self.wl_sens = 1
        self.hu0 = self.slicer.state['hu']
        
        # Layout
        self.widget = widgets.HBox([self.viewer.widget, self.controls.widget])
        
        # Sync initial state
        self._sync_state()

    def display(self):
        from IPython.display import display
        display(self.widget)
        
    def _sync_state(self):
        state_dict = {
            'z_index': self.controls.z_index.value,
            'hu': self.controls.hu.value,
            'mask_opacity': self.controls.mask_opacity.value,
            'mask_on': self.controls.mask_on.value,
            'only_mask': self.controls.only_mask.value
        }
        self.slicer.update_state(**state_dict)
        self.viewer.set_image(self.slicer.get_image())

    def _on_controls_change(self, state_dict):
        self.slicer.update_state(**state_dict)
        self.viewer.set_image(self.slicer.get_image())
        self.viewer.update_status(f"Slice: {state_dict['z_index']} | W/L: {state_dict['hu']}")

    # --- Event Handlers (Mapping UI actions to Slicer Math) ---
    
    def _handle_scroll(self, delta):
        step = 1 if delta > 0 else -1
        current_z = self.slicer.state['z_index']
        new_z = max(0, min(self.slicer.state['z_index_max'], current_z + step))
        if new_z != current_z:
            self.controls.update_silently(z_index=new_z)
            self._sync_state()
            self.viewer.update_status(f"Slice: {new_z}/{self.slicer.state['z_index_max']}")

    def _handle_drag_start(self, x, y, button):
        if button == 2:  # Right click
            self.hu0 = self.slicer.state['hu']

    def _handle_drag(self, dx, dy, button):
        if button == 2:  # Right click -> Window/Level
            s = self.wl_sens    
            a, b = self.hu0
            # dx widens window, dy shifts level
            new_a = int(a + s*dx - s*dy)
            new_b = int(b + s*dx + s*dy)
            
            # Update controls silently, then sync
            self.controls.update_silently(hu=(new_a, new_b))
            self._sync_state()
            self.viewer.update_status(f"W/L: {new_a}, {new_b}")

    def _handle_hover(self, x, y):
        try:
            val = self.slicer.get_value_at_jk(y, x)
        except Exception:
            val = 'N/A'
        self.viewer.update_status(f"Hover: ({x}, {y}) | Val: {val}")

    def _handle_keydown(self, key):
        current_z = self.slicer.state['z_index']
        max_z = self.slicer.state['z_index_max']
        new_z = current_z

        if key == 'ArrowUp':
            new_z = min(max_z, current_z + 1)
        elif key == 'ArrowDown':
            new_z = max(0, current_z - 1)
        elif key == 'm':
            new_mask = not self.slicer.state['mask_on']
            self.controls.update_silently(mask_on=new_mask)
            self._sync_state()
            self.viewer.update_status(f"Mask: {new_mask}")
            return

        if new_z != current_z:
            self.controls.update_silently(z_index=new_z)
            self._sync_state()
            self.viewer.update_status(f"Slice: {new_z}")

# Aliases for backwards compatibility
InteractiveSlicer = InteractiveDicomWidget
InteractiveViewer = InteractiveImageViewer
