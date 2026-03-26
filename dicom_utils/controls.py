import ipywidgets as widgets

class DicomControls:
    """Reusable UI sliders and toggles for DicomSlicer parameters."""
    def __init__(self, max_z, on_change=None):
        self.on_change = on_change
        self._programmatic_update = False
        
        # --- Define Widgets (All Int based) ---
        self.z_index = widgets.IntSlider(min=0, max=max_z, value=0, description='Slice')
        self.hu = widgets.IntRangeSlider(min=-1000, max=3000, step=1, value=(-130, 600), description='HU Range')
        self.mask_opacity = widgets.IntSlider(min=0, max=100, step=1, value=50, description='Opacity %')
        self.mask_on = widgets.ToggleButton(value=False, description='Mask On/Off')
        self.only_mask = widgets.ToggleButton(value=False, description='Img On/Off')
        
        self.widget = widgets.VBox([
            self.z_index, self.hu, self.mask_opacity, self.mask_on, self.only_mask
        ])
        
        for w in [self.z_index, self.hu, self.mask_opacity, self.mask_on, self.only_mask]:
            w.observe(self._on_change, names='value')

    def _on_change(self, change):
        if self._programmatic_update or not self.on_change:
            return
        self.on_change({
            'z_index': self.z_index.value,
            'hu': self.hu.value,
            'mask_opacity': self.mask_opacity.value,
            'mask_on': self.mask_on.value,
            'only_mask': self.only_mask.value
        })

    def update_silently(self, **kwargs):
        self._programmatic_update = True
        try:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    w = getattr(self, k)
                    # For IntRangeSlider we expect a tuple
                    if isinstance(w, widgets.IntRangeSlider) and isinstance(v, tuple):
                        w.value = v
                    elif hasattr(w, 'value'):
                        w.value = v
        finally:
            self._programmatic_update = False