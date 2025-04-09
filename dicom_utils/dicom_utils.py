import ipywidgets as widgets
from ipywidgets import Image, Output,interactive, IntSlider,FloatSlider, FloatRangeSlider, ToggleButton,VBox,HBox,FloatSlider
from PIL import Image as PILImage
import io
import numpy as np

def save_PILlst_webp(frames, fn='animation.webp',format='webp'):
    """Save a list of PIL images as a WebP animation."""
    frames[0].save(
        fn,
        save_all=True,
        append_images=frames[1:],
        duration=100,  # Duration in milliseconds per frame
        loop=0,
        format=format,
        quality=95
    )

colors1 = {
    'RA': (255, 0, 0, 255),           # Red for Right Atrium (RA)
    'RV': (0, 255, 0, 255),           # Green for Right Ventricle (RV)
    'LVmyo': (0, 0, 255, 255),        # Blue for Left Ventricle Myocardium (LVmyo)
    'LA': (255, 255, 0, 255),         # Yellow for Left Atrium (LA)
    'LV': (255, 165, 0, 255),         # Orange for Left Ventricle (LV)
    'Ao': (128, 0, 128, 255),         # Purple for Aorta (Ao)
    'pericardium': (255, 192, 203, 255), # Pink for Pericardium
    'CORONARIES': (0, 255, 255, 255), # Cyan for Coronary Arteries (CORONARIES)
    'LCA': (0, 128, 128, 255),        # Teal for Left Coronary Artery (LCA)
    'RCA': (128, 0, 0, 255),          # Maroon for Right Coronary Artery (RCA)
    'plaque_calcified': (192, 192, 192, 255), # Silver for Calcified Plaque
    'plaque_non_calcified': (128, 128, 128, 255) # Gray for Non-Calcified Plaquq
}

wl2range = lambda w,l: (l-w/2,l+w/2)

def HU_to_gray(image, hu=(-140, 900)):
    """Convert image array to grayscale using HU windowing."""
    re_imgs = np.clip(255 * (image - hu[0]) / (hu[1] - hu[0]), 0, 255).astype(np.uint8)
    return re_imgs

class DicomWidget:
    """A widget for interactively displaying DICOM slices with HU windowing."""
    
    def __init__(self, image_array, origin=None, spacing=None,mask=None,label_to_organ=None,organ_to_color=None):
        """
        Initialize the DicomWidget with a 3D image array and optional metadata.
        
        Parameters:
        - image_array: 3D NumPy array (z, y, x) of DICOM image data.
        - origin: Tuple or array of image origin coordinates (optional).
        - spacing: Tuple or array of voxel spacing (optional).
        """
        self.img = image_array
        self.origin = origin if origin is not None else (0, 0, 0)
        self.spacing = spacing if spacing is not None else (1, 1, 1)
        self.mask = None
        self.format = 'webp'
        self.output = Output()

        if mask is not None:
            self.mask = mask
            
        if label_to_organ:
            self.label_to_organ = label_to_organ 

        else:
            self.label_to_organ = {1: 'mask'}

            
        if organ_to_color:
            self.organ_to_color = organ_to_color
        else:
            self.organ_to_color = {'mask': (255, 0, 0, 128)}
      
        
        # Create the Image widget
        self.im_w = Image()
        
        # Set up the initial display
        self._update_image(0, (-140, 900))
        
        self.z_index=IntSlider(min=0, max=self.img.shape[0] - 1, value=0, description='Slice')
        self.hu=FloatRangeSlider(min=-1000, max=2000, step=1, value=(-130, 600), description='HU Range')
        self.mask_opacity=FloatSlider(min=0.0, max=1.0, step=0.01, value=0.5, description='Mask Opacity')
        self.mask_on=ToggleButton(value=False, description='Mask On/Off')
        self.only_mask=ToggleButton(value=False, description='Imag On/Off')

        
        self.controls = interactive(
            self._update,
            z_index=self.z_index,
            hu=self.hu,
            mask_opacity=self.mask_opacity,
            mask_on=self.mask_on,
            only_mask=self.only_mask
        )
        
        # Layout the widget and controls horizontally
        self.widget = HBox([self.im_w, self.controls])


        self.LungWindow = wl2range(1500,-600) # Lung Window
        self.MediastinumWindow = wl2range(400,40) # mediastinum Window
        self.BoneWindow = wl2range(1800,400) # Bone Window
    
    def _update_image(self, z_index, hu, mask_opacity=0.5, mask_on=False, only_mask=False):
        """Update the displayed image based on z-index and HU range."""
        # Convert the selected slice to grayscale

        if  mask_on is False  and  only_mask:
            im_pil =  PILImage.new('RGBA', (self.img.shape[2], self.img.shape[1]), (0, 0, 0, 255))
            self.im_pil = im_pil
            buf = io.BytesIO()
            im_pil.save(buf, format=self.format, quality=90)
            self.im_w.value = buf.getvalue()
            return None 

       
        if not only_mask:
            im_array = HU_to_gray(self.img[z_index], hu=hu)
            
            if self.mask is not None and mask_on:
                im_pil = PILImage.fromarray(im_array).convert('RGBA')
            else:
                im_pil = PILImage.fromarray(im_array)

    
        # Apply mask overlay if mask exists and is enabled
        if self.mask is not None and mask_on:
            mask_slice = self.mask[z_index]
            overlay = np.zeros((mask_slice.shape[0], mask_slice.shape[1], 4), dtype=np.uint8)
            
            # Iterate through labels in the mask
            for label, organ in self.label_to_organ.items():
                if label != 0 and organ in self.organ_to_color:
                    rgba = self.organ_to_color[organ]  # Expected format: (R, G, B, A)
                    mask_region = (mask_slice == label)
                    overlay[mask_region] = rgba
            
            # Convert overlay to PIL image
            overlay_pil = PILImage.fromarray(overlay, 'RGBA')

            if only_mask:
                im_pil = overlay_pil
            else:
                # Scale overlay alpha by mask_opacity
                overlay_array = np.array(overlay_pil, dtype=np.float32)
                overlay_array[..., 3] *= mask_opacity  # Adjust alpha channel (0-255)
                overlay_pil = PILImage.fromarray(overlay_array.astype(np.uint8), 'RGBA')
                
                        
                with self.output:
                    print(f'in mask {overlay.sum()}')
                # im_pil = PILImage.blend(im_pil, overlay_pil, alpha=mask_opacity)
                
                im_pil = PILImage.alpha_composite(im_pil, overlay_pil)


        else:
            with self.output:
                print(f'NO in mask')

        self.im_pil = im_pil

        # Save to WebP bytes
        buf = io.BytesIO()
        im_pil.save(buf, format=self.format, quality=90)
        self.im_w.value = buf.getvalue()
    
    def _update(self, z_index, hu, mask_opacity, mask_on, only_mask):
        """Callback function for interactive updates."""
        self._update_image(z_index, hu, mask_opacity, mask_on, only_mask)
    
    def display(self):
        """Display the widget in a Jupyter notebook."""
        from IPython.display import display
        display(self.widget)


    def add_mask(self, mask_array, label_to_organ, organ_to_color):
        """
        Add a mask to the widget with label-to-organ and organ-to-color mappings.
        
        Parameters:
        - mask_array: 3D NumPy array (z, y, x) of the same shape as image_array, with integer labels.
        - label_to_organ: Dict mapping integer labels to organ names (e.g., {1: 'liver', 2: 'kidney'}).
        - organ_to_color: Dict mapping organ names to RGBA colors (e.g., {'liver': (255, 0, 0, 128)}).
        """
        if mask_array.shape != self.img.shape:
            raise ValueError("Mask array shape must match image array shape.")
        
        self.mask = mask_array
        self.label_to_organ = label_to_organ
        self.organ_to_color = organ_to_color
        
        # Update the display with the mask controls enabled
        self._update_image(
            self.controls.kwargs['z_index'],
            self.controls.kwargs['hu'],
            self.controls.kwargs['mask_opacity'],
            self.controls.kwargs['mask_on']
        )
    def update_case(self,image,mask=None):
        """
            changes the whole case.
        """

        self.img = image
        self.mask = mask
        slider = [c  for c in self.controls.children if hasattr(c,'description') and c.description == 'Slice'][0]
        slider.max = self.img.shape[0]-1
        self.controls.update()

    def save_frame(self,output_fn=None):
        format = self.format
        if  output_fn:
            if not output_fn.endswith('.'+format):
                output_fn = f'{output_fn}_{self.controls.kwargs["z_index"]:04}.{format}'
        else:
            output_fn = f'img_{self.controls.kwargs["z_index"]:04}.{format}'
        
        with open(output_fn, 'wb') as f:
            f.write(self.im_w.value)

    
    def save_animation(self, fn='animation.webp', z_lst=None):
        """Save an animation of slices as a WebP file."""
        
        #    fn = '.'.join(fn.split('.')[:-1])  
        #    fn = f'{fn}_{self.controls.kwargs["z_index"]:04}.webp'

        if z_lst is None:
            z_lst = range(self.img.shape[0])

        frames = []
        for z in z_lst:
            self.z_index.value = z
            frames.append(self.im_pil)
        
       
        save_PILlst_webp(frames, fn=fn,format='webp')
