import ipywidgets as widgets
import numpy as np
from PIL import Image
import io

class SimpleRGBWidget:
    """
    A minimal widget satisfying the AnnotationCanvas interface for single RGB images.
    Serves as a proxy/lab for larger data objects.
    """
    def __init__(self, rgb_array, mask=None, format='webp', quality=90, save_params=None):
        self.img_data = rgb_array
        self.mask = mask if mask is not None else np.zeros(rgb_array.shape[:2], dtype=np.uint8)
        self.format = format
        self.quality = quality
        self.save_params = save_params or {'method': 1}
        
        # 1. Image Widget (The DOM Event Source)
        self.im_w = widgets.Image(format=self.format, width=rgb_array.shape[1], height=rgb_array.shape[0])
        
        # 2. Slicer Proxy (Required by AnnotationCanvas)
        # We wrap our state to match the expected .slicer.state and .slicer.mask structure
        class SlicerProxy:
            def __init__(self, mask):
                self.mask = mask
                self.state = {
                    'z_index': 0,
                    'mask_opacity': 0.5,
                    'mask_on': True,
                    'only_mask': False,
                    'hu': (0, 255) # Dummy for RGB
                }
        self.slicer = SlicerProxy(self.mask)
        
        # 3. Dummy HU widget (Required by AnnotationCanvas._update_image call signature)
        self.hu = widgets.FloatRangeSlider(value=[0, 255])
        
        # 4. Top-level Widget
        self.widget = widgets.Box([self.im_w])
        
        # Initial render
        self._update_image(0, (0, 255))

    def _update_image(self, z, hu_range, **kwargs):
        """
        Refresh the UI. In a 'large object' scenario, this is where you'd 
        trigger the object's internal update logic.
        """
        # Convert NumPy to PIL Image
        pil_img = Image.fromarray(self.img_data.astype('uint8'))
        
        # Overlay mask if requested
        if kwargs.get('mask_on', True) and self.mask is not None:
            # Basic visualization logic for the lab
            pass
            
        byte_io = io.BytesIO()
        pil_img.save(byte_io, format=self.format.upper(), quality=self.quality, **self.save_params)
        self.im_w.value = byte_io.getvalue()

    def display(self):
        from IPython.display import display
        display(self.widget)
