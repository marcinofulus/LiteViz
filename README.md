# LiteViz

LiteViz is a lightweight Python toolkit designed for interactive visualization and annotation of DICOM images and segmentation masks within Jupyter Notebook environments. It leverages `ipywidgets`, `ipyevents`, and `PIL` to provide a responsive, browser-based UI for medical image viewing.

## Architecture Overview

```text
 ┌─────────────────────┐
 │    DicomSlicer      │ <────────────────────┐
 │ (Core Logic Engine) │                      │
 └─────────▲───────────┘                      │ (wraps)
           │                                  │
   (uses)  │                       ┌──────────┴─────────┐
           │                       │    DicomWidget     │ <────┐
 ┌─────────┴───────────┐           │ (Slider-based UI)  │      │ (wraps)
 │  InteractiveSlicer  │           └────────────────────┘      │
 │ (Advanced Mouse UI) │                                ┌──────┴───────────┐
 └─────────▲───────────┘                                │ AnnotationCanvas │
           │                                            │   (Drawing UI)   │
           │ (inherits)                                 └──────────────────┘
 ┌─────────┴───────────┐
 │  InteractiveViewer  │
 │  (Base UI Events)   │
 └─────────────────────┘
```

## Class Summaries

Below is a summary of the core classes and their functionalities in the project.

### 1. `DicomSlicer` (`dicom_utils/dicom_utils.py`)
The core logic engine for handling DICOM data, independent of any UI components. 
- **Functionality:** Manages the underlying 3D image arrays (HU values) and optional segmentation masks.
- **State Management:** Tracks visualization state such as current slice (`z_index`), Window/Level range (`hu`), mask opacity, and display toggles.
- **Image Generation:** Converts HU values to grayscale arrays, maps mask labels to RGBA colors, and composites them into `PIL.Image` objects.
- **Export:** Includes utilities for generating and saving WebP animations of the slices.

### 2. `DicomWidget` (`dicom_utils/dicom_utils.py`)
A UI wrapper around `DicomSlicer` using `ipywidgets`.
- **Functionality:** Provides a ready-to-use interactive widget with sliders for navigating slices, adjusting HU windowing, setting mask opacity, and toggling mask overlays.
- **Integration:** Binds UI controls directly to the state of the underlying `DicomSlicer` instance, updating the displayed image automatically when parameters change.
- **Presets:** Includes predefined Window/Level settings for common medical views (e.g., Lung Window, Mediastinum Window, Bone Window).

### 3. `InteractiveViewer` (`dicom_utils/interactive_slicer.py`)
A base class for generic, event-driven image interaction.
- **Functionality:** Handles low-level UI interactions such as mouse movement, dragging, clicking, keyboard inputs, and scroll wheel events using `ipyevents`.
- **Coordinate Handling:** Performs robust coordinate scaling to map browser DOM events to accurate pixel coordinates on the image.
- **Overlays:** Supports drawing temporary debug overlays like crosshairs, hover circles, and drag lines directly onto the view.

### 4. `InteractiveSlicer` (`dicom_utils/interactive_slicer.py`)
An advanced viewer that connects `InteractiveViewer` (UI events) to `DicomSlicer` (DICOM data).
- **Functionality:** Implements intuitive, mouse-driven controls typical in radiology software:
  - **Scroll Wheel / Up & Down Arrows:** Navigate through slices (`z_index`).
  - **Right-Click Drag:** Dynamically adjust Window (width) and Level (center) on the fly.
  - **Hover:** Displays the real-time Hounsfield Unit (HU) value of the pixel under the cursor.
  - **'m' Key:** Quickly toggle the mask overlay on and off.

### 5. `AnnotationCanvas` (`dicom_utils/canvas_utils.py`)
An interactive canvas designed to extend a basic `DicomWidget` with custom event handling and annotation capabilities.
- **Functionality:** Uses `ipyevents` to monitor mouse actions over the displayed image.
- **Drawing/Annotation:** Allows modifying the underlying mask array (e.g., drawing label `4`) by left-clicking and dragging.
- **Interactive Controls:** Supports adjusting HU by right-clicking and dragging, and navigating slices with the mouse wheel, while providing real-time feedback via a text area.

### 6. `BodyRegions` & `BodyParts` (`dicom_utils/label_schemes/saros.py`)
Enumeration classes used for standardizing segmentation labels.
- **Functionality:** Maps integer label values to specific anatomical structures (e.g., `SUBCUTANEOUS_TISSUE`, `MUSCLE`, `BONE`, `TORSO`, `HEAD`).
- **Styling:** The module also defines associated color dictionaries (`body_regions_colors`, `body_parts_colors`) to ensure consistent visual representation of these structures when rendered as mask overlays.

## Usage Examples

You can copy and paste these examples directly into your Jupyter Notebook cells.

### 1. Advanced Interactive Viewer (Mouse-Driven)
The `InteractiveSlicer` provides a professional radiology-style experience with mouse wheel scrolling and right-click windowing.

```python
import numpy as np
from dicom_utils import DicomSlicer, InteractiveSlicer
from IPython.display import display

# Load your 3D image and mask arrays (numpy)
# image.shape -> (depth, height, width)
image = np.load('image.npy') 
mask = np.load('mask.npy')

# 1. Initialize the logic engine
slicer = DicomSlicer(image_array=image, mask=mask)

# 2. Initialize the interactive viewer
app = InteractiveSlicer(
    dicom_slicer=slicer, 
    fps=20,             # Target frames per second for interaction
    show_status=True    # Show the status bar with HU and slice info
)

# 3. Render in notebook
display(app.display())
```

### 2. Simple Widget (Slider-Driven)
The `DicomWidget` is perfect for a quick, control-based inspection without complex mouse interactions.

```python
import numpy as np
from dicom_utils import DicomWidget

# Load your 3D image and mask arrays (numpy)
image = np.load('image.npy')
mask = np.load('mask.npy')

# Initialize and display the widget
w = DicomWidget(image_array=image, mask=mask)
w.display()
```

### 3. Using Annotation Canvas
To enable simple mask editing (painting) within the notebook:

```python
from dicom_utils import DicomWidget, AnnotationCanvas

# Initialize standard widget
w = DicomWidget(image_array=image, mask=mask)

# Wrap it in an AnnotationCanvas to enable drawing
canvas = AnnotationCanvas(w, edit_flag=True)
canvas.display()
```