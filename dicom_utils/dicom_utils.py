import io
import numpy as np
from PIL import Image as PILImage
from contextlib import contextmanager

import ipywidgets as widgets
from ipywidgets import Image, Output, IntSlider, IntRangeSlider, ToggleButton, VBox, HBox

default_label_to_organ = {i: f'mask{i}' for i in range(1, 17)}

# 2. Define a discrete 16-color palette (RGBA)
# 1:Red, then high-contrast standard colors
palette_16 = [
    (255, 0, 0, 255),       # 1. Red
    (0, 255, 0, 255),       # 2. Green
    (0, 0, 255, 255),       # 3. Blue
    (255, 255, 0, 255),     # 4. Yellow
    (0, 255, 255, 255),     # 5. Cyan
    (255, 0, 255, 255),     # 6. Magenta
    (255, 165, 0, 255),     # 7. Orange
    (128, 0, 128, 255),     # 8. Purple
    (255, 192, 203, 255),   # 9. Pink
    (128, 128, 0, 255),     # 10. Olive
    (0, 128, 128, 255),     # 11. Teal
    (0, 0, 128, 255),       # 12. Navy
    (128, 0, 0, 255),       # 13. Maroon
    (0, 255, 127, 255),     # 14. Spring Green
    (128, 128, 128, 255),   # 15. Gray
    (210, 105, 30, 255)     # 16. Chocolate
]

# 3. Map Organ Names to Colors
default_organ_to_color = {
    f'mask{i}': palette_16[i-1] for i in range(1, 17)
}

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
            'z_index_min':0,
            'z_index_max':self.img.shape[0]-1,
            'hu': (-130, 600),
            'mask_opacity': 50,  # 0-100
            'mask_on': False,
            'only_mask': False
        }

        self.label_to_organ = label_to_organ if label_to_organ else default_label_to_organ
        self.organ_to_color = organ_to_color if organ_to_color else default_organ_to_color 

    def update_state(self, **kwargs):
        """Update internal state dictionary."""
        self.state.update(kwargs)

    def set_data(self, image, mask=None):
        """Update the underlying data."""
        self.img = image
        self.mask = mask
        self.state['z_index_max'] = self.img.shape[0]-1
        # Ensure z_index is within new bounds
        if self.state['z_index'] >= self.state['z_index_max']:
            self.state['z_index'] = 0

    def set_mask_mappings(self, label_to_organ, organ_to_color):
        self.label_to_organ = label_to_organ
        self.organ_to_color = organ_to_color
    
    def get_value_at_jk(self, j,k):
        i = self.state['z_index']
        HU = self.img[i,j,k]
        return HU

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
    """A widget for interactively displaying DICOM slices with HU windowing.
    This base widget relies on simple ipywidgets and has NO dependencies on ipyevents."""

    def __init__(self, image_array, mask=None, origin=None, spacing=None, label_to_organ=None, organ_to_color=None):
        
        # Initialize the Logic Engine
        self.slicer = DicomSlicer(image_array, mask=mask, origin=origin, spacing=spacing,
                                  label_to_organ=label_to_organ, organ_to_color=organ_to_color)
        
        # UI Components
        from .viewers import SimpleImageViewer
        from .controls import DicomControls
        
        initial_img = self.slicer.get_image()
        self.viewer = SimpleImageViewer(width=initial_img.width, height=initial_img.height)
        self.controls = DicomControls(max_z=image_array.shape[0]-1, on_change=self._on_controls_change)
        
        self.widget = widgets.HBox([self.viewer.widget, self.controls.widget])
        
        # Preset Windows
        self.LungWindow = wl2range(1500, -600)
        self.MediastinumWindow = wl2range(400, 40)
        self.BoneWindow = wl2range(1800, 400)
        
        # Sync Initial State
        self._on_controls_change({
            'z_index': self.controls.z_index.value,
            'hu': self.controls.hu.value,
            'mask_opacity': self.controls.mask_opacity.value,
            'mask_on': self.controls.mask_on.value,
            'only_mask': self.controls.only_mask.value
        })

    # --- Backwards Compatibility Properties ---
    @property
    def z_index(self): return self.controls.z_index
    @property
    def hu(self): return self.controls.hu
    @property
    def mask_opacity(self): return self.controls.mask_opacity
    @property
    def mask_on(self): return self.controls.mask_on
    @property
    def only_mask(self): return self.controls.only_mask
    @property
    def im_w(self): return self.viewer.image_widget

    # --- State Handling ---
    def _on_controls_change(self, state_dict):
        """Called when UI controls are changed."""
        self.slicer.update_state(**state_dict)
        self.viewer.set_image(self.slicer.get_image())

    @contextmanager
    def ignore_updates(self):
        """Context manager to silence observers during programmatic updates."""
        self.controls._programmatic_update = True
        try:
            yield
        finally:
            self.controls._programmatic_update = False

    def set_widget_value(self, widget_obj, new_val):
        """Generic backend function to safely update any widget programmatically."""
        # Find which key this widget represents and update it via update_silently
        for k in ['z_index', 'hu', 'mask_opacity', 'mask_on', 'only_mask']:
            if getattr(self.controls, k) is widget_obj:
                self.controls.update_silently(**{k: new_val})
                return

    def _update_image(self, z_index, hu, mask_opacity, mask_on, only_mask):
        """Compatibility method for external interaction classes."""
        self.slicer.update_state(
            z_index=z_index, hu=hu, mask_opacity=mask_opacity,
            mask_on=mask_on, only_mask=only_mask
        )
        self.viewer.set_image(self.slicer.get_image())

    def set_slice(self, z):
        self.controls.update_silently(z_index=z)

    def set_hu(self, min_val, max_val):
        self.controls.update_silently(hu=(min_val, max_val))

    def display(self):
        from IPython.display import display
        display(self.widget)

    def add_mask(self, mask_array, label_to_organ, organ_to_color):
        if mask_array.shape != self.slicer.img.shape:
            raise ValueError("Mask array shape must match image array shape.")
        self.slicer.set_data(self.slicer.img, mask_array)
        self.slicer.set_mask_mappings(label_to_organ, organ_to_color)
        self.viewer.set_image(self.slicer.get_image())

    def update_case(self, image, mask=None):
        self.slicer.set_data(image, mask)
        max_z = image.shape[0] - 1
        self.controls.z_index.max = max_z
        if self.controls.z_index.value > max_z:
             self.controls.update_silently(z_index=0)
             self.slicer.update_state(z_index=0)
        self.viewer.set_image(self.slicer.get_image())

    def save_frame(self, output_fn=None):
        format = self.viewer.format
        current_z = self.controls.z_index.value
        if output_fn:
            if not output_fn.endswith('.' + format):
                output_fn = f'{output_fn}_{current_z:04}.{format}'
        else:
            output_fn = f'img_{current_z:04}.{format}'
        
        im_pil = self.slicer.get_image()
        if im_pil:
            with open(output_fn, 'wb') as f:
                im_pil.save(f, format=format)


      