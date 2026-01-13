import io
import numpy as np
from PIL import Image as PILImage
from contextlib import contextmanager

import ipywidgets as widgets
from ipywidgets import Image, Output, IntSlider, IntRangeSlider, ToggleButton, VBox, HBox


def wl2range(w, l):
    """Convert Window/Level to Min/Max."""
    return int(l - w / 2), int(l + w / 2)

def HU_to_gray(image, hu=(-140, 900)):
    """Convert image array to grayscale using HU windowing."""
    low, high = hu
    img_f = image.astype(np.float32)
    re_imgs = np.clip(255 * (img_f - low) / (high - low), 0, 255).astype(np.uint8)
    return re_imgs

def save_PILlst_webp(frames, fn='animation.webp', format='webp'):
    """Save a list of PIL images as a WebP animation."""
    if not frames:
        return
    frames[0].save(
        fn,
        save_all=True,
        append_images=frames[1:],
        duration=100,
        loop=0,
        format=format,
        quality=95
    )

# --- 1. DicomSlicer (The Logic / Model) ---
class DicomSlicer:
    """
    Handles DICOM data, state management, and image generation.
    Independent of ipywidgets.
    """
    def __init__(self, image_array, mask=None, origin=None, spacing=None, label_to_organ=None, organ_to_color=None):

        self.img = image_array
        self.mask = mask

        self.origin = origin if origin is not None else (0, 0, 0)
        self.spacing = spacing if spacing is not None else (1, 1, 1)
      
        # State Dictionary
        self.state = {
            'z_index': 0,
            'hu': (-130, 600),
            'mask_opacity': 50,  # 0-100
            'mask_on': False,
            'only_mask': False
        }

        self.label_to_organ = label_to_organ if label_to_organ else {1: 'mask'}
        self.organ_to_color = organ_to_color if organ_to_color else {'mask': (255, 0, 0, 128)}

    def update_state(self, **kwargs):
        """Update internal state dictionary."""
        self.state.update(kwargs)

    def set_data(self, image, mask=None):
        """Update the underlying data."""
        self.img = image
        self.mask = mask
        # Ensure z_index is within new bounds
        if self.state['z_index'] >= self.img.shape[0]:
            self.state['z_index'] = 0

    def set_mask_mappings(self, label_to_organ, organ_to_color):
        self.label_to_organ = label_to_organ
        self.organ_to_color = organ_to_color

    def get_image(self):
        """Generate and return the PIL Image based on current state."""
        # Unpack state
        z_index = self.state['z_index']
        hu = self.state['hu']
        mask_opacity = self.state['mask_opacity']
        mask_on = self.state['mask_on']
        only_mask = self.state['only_mask']

        opacity_factor = mask_opacity / 100.0

        # Case 1: Mask is OFF but Only Mask is ON -> Return Blank
        if mask_on is False and only_mask:
            return PILImage.new('RGBA', (self.img.shape[2], self.img.shape[1]), (0, 0, 0, 255))

        # Case 2: Base Image Generation
        if not only_mask:
            im_array = HU_to_gray(self.img[z_index], hu=hu)
            if self.mask is not None and mask_on:
                im_pil = PILImage.fromarray(im_array).convert('RGBA')
            else:
                im_pil = PILImage.fromarray(im_array)
        else:
            # Placeholder for 'only_mask' overlay base
            im_pil = PILImage.new('RGBA', (self.img.shape[2], self.img.shape[1]), (0, 0, 0, 0))

        # Case 3: Overlay Generation
        if self.mask is not None and mask_on:
            mask_slice = self.mask[z_index]
            overlay = np.zeros((mask_slice.shape[0], mask_slice.shape[1], 4), dtype=np.uint8)

            for label, organ in self.label_to_organ.items():
                if label != 0 and organ in self.organ_to_color:
                    rgba = self.organ_to_color[organ]
                    mask_region = (mask_slice == label)
                    overlay[mask_region] = rgba

            overlay_pil = PILImage.fromarray(overlay, 'RGBA')

            if only_mask:
                im_pil = overlay_pil
            else:
                if opacity_factor < 1.0:
                    overlay_array = np.array(overlay_pil, dtype=np.float32)
                    overlay_array[..., 3] *= opacity_factor
                    overlay_pil = PILImage.fromarray(overlay_array.astype(np.uint8), 'RGBA')

                im_pil = PILImage.alpha_composite(im_pil, overlay_pil)
        
        return im_pil

    def save_animation(self, fn='animation.webp', z_lst=None):
        """
        Generates and saves an animation.
        Restores internal state (z_index) when finished.
        """
        if z_lst is None:
            z_lst = range(self.img.shape[0])
        
        frames = []
        original_z = self.state['z_index']  # Save State
        
        # Iterate and Generate
        for z in z_lst:
            self.update_state(z_index=z)
            frames.append(self.get_image())
            
        save_PILlst_webp(frames, fn=fn, format='webp')
        
        # Restore State
        self.update_state(z_index=original_z)

class DicomWidget:
    """A widget for interactively displaying DICOM slices with HU windowing."""

    def __init__(self, image_array, mask=None, origin=None, spacing=None, label_to_organ=None, organ_to_color=None):
        
        # Initialize the Logic Engine
        self.slicer = DicomSlicer(image_array, mask=mask, origin=origin, spacing=spacing, \
                                  label_to_organ=label_to_organ, organ_to_color=organ_to_color)
        
        # Meta properties
        self.format = 'webp'
        self.output = Output()

        # Flags
        self._programmatic_update = False
        self.update_image_widget = True 
        
        # Visual Component
        self.im_w = Image()
        # Keep a reference to current PIL for saving frames
        self.im_pil = None

        # --- Define Widgets (All Int based) ---
        self.z_index = IntSlider(
            min=0, max=image_array.shape[0] - 1, value=0, description='Slice'
        )
        
        self.hu = IntRangeSlider(
            min=-1000, max=3000, step=1, value=(-130, 600), description='HU Range'
        )
        
        self.mask_opacity = IntSlider(
            min=0, max=100, step=1, value=50, description='Opacity %'
        )
        
        self.mask_on = ToggleButton(value=False, description='Mask On/Off')
        self.only_mask = ToggleButton(value=False, description='Img On/Off')

        # --- Bind Observers ---
        for w in [self.z_index, self.hu, self.mask_opacity, self.mask_on, self.only_mask]:
            w.observe(self._on_change, names='value')

        self.controls = VBox([
            self.z_index, self.hu, self.mask_opacity, self.mask_on, self.only_mask
        ])
        self.widget = HBox([self.im_w, self.controls])

        # Preset Windows
        self.LungWindow = wl2range(1500, -600)
        self.MediastinumWindow = wl2range(400, 40)
        self.BoneWindow = wl2range(1800, 400)
        
        # Initial Render
        self._on_change(None)

    @contextmanager
    def ignore_updates(self):
        """Context manager to silence observers during programmatic updates."""
        self._programmatic_update = True
        try:
            yield
        finally:
            self._programmatic_update = False

    def set_widget_value(self, widget, new_val):
        """
        Generic backend function to safely update any widget programmatically.
        """
        if not hasattr(widget, 'value'):
            return

        w_min = getattr(widget, 'min', None)
        w_max = getattr(widget, 'max', None)
        step = getattr(widget, 'step', 1)

        def fit(val):
            if w_min is not None: val = max(w_min, val)
            if w_max is not None: val = min(w_max, val)
            if step > 1 and w_min is not None:
                val = round((val - w_min) / step) * step + w_min
            return int(val)

        if isinstance(widget, IntRangeSlider):
            try:
                v1, v2 = new_val
                final_val = (min(fit(v1), fit(v2)), max(fit(v1), fit(v2)))
            except (ValueError, TypeError):
                return
        elif isinstance(widget, IntSlider):
            try:
                final_val = fit(new_val)
            except (ValueError, TypeError):
                return
        elif isinstance(widget, ToggleButton):
            final_val = bool(new_val)
        else:
            final_val = new_val

        if widget.value != final_val:
            with self.ignore_updates():
                widget.value = final_val

    def _on_change(self, change):
        """Central event handler."""
        if self._programmatic_update:
            return

        # 1. Update Slicer State
        self.slicer.update_state(
            z_index=self.z_index.value,
            hu=self.hu.value,
            mask_opacity=self.mask_opacity.value,
            mask_on=self.mask_on.value,
            only_mask=self.only_mask.value
        )
        
        # 2. Get Image from Slicer
        self.im_pil = self.slicer.get_image()
        
        # 3. Update Widget View
        if self.update_image_widget:
            buf = io.BytesIO()
            self.im_pil.save(buf, format=self.format, quality=90)
            self.im_w.value = buf.getvalue()

    # --- Wrapper methods for external control ---

    def _update_image(self, z_index, hu, mask_opacity, mask_on, only_mask):
        """
        Compatibility method for external interaction classes (like InteractiveImageEditor).
        Instead of duplicating logic, this just pushes values to slicer and updates view.
        """
        self.slicer.update_state(
            z_index=z_index, hu=hu, mask_opacity=mask_opacity,
            mask_on=mask_on, only_mask=only_mask
        )
        self.im_pil = self.slicer.get_image()
        
        if self.update_image_widget:
            buf = io.BytesIO()
            self.im_pil.save(buf, format=self.format, quality=90)
            self.im_w.value = buf.getvalue()

    def set_slice(self, z):
        self.set_widget_value(self.z_index, z)
        # Assuming UI sync only; explicit update might be needed if not coupled with mouse

    def set_hu(self, min_val, max_val):
        self.set_widget_value(self.hu, (min_val, max_val))

    def display(self):
        from IPython.display import display
        display(self.widget)

    def add_mask(self, mask_array, label_to_organ, organ_to_color):
        if mask_array.shape != self.slicer.img.shape:
            raise ValueError("Mask array shape must match image array shape.")
        
        self.slicer.set_data(self.slicer.img, mask_array)
        self.slicer.set_mask_mappings(label_to_organ, organ_to_color)
        self._on_change(None)

    def update_case(self, image, mask=None):
        # Update Slicer Data
        self.slicer.set_data(image, mask)
        
        # Update Widget Bounds
        if self.z_index.value > image.shape[0]-1:
             self.set_widget_value(self.z_index, 0)
        self.z_index.max = image.shape[0] - 1
        
        # Refresh
        self._on_change(None)

    def save_frame(self, output_fn=None):
        format = self.format
        current_z = self.z_index.value
        if output_fn:
            if not output_fn.endswith('.' + format):
                output_fn = f'{output_fn}_{current_z:04}.{format}'
        else:
            output_fn = f'img_{current_z:04}.{format}'
        
        # Use current PIL
        if self.im_pil:
            with open(output_fn, 'wb') as f:
                self.im_pil.save(f, format=format)


      