# TODO: Architectural Redesign for Modular Interactive Viewers

This document outlines the architectural changes required to transform LiteViz into a modular, "LEGO-block" framework for fast prototyping of interactive image viewers in Jupyter Notebooks. The core philosophy is **composition over inheritance**, decoupling the image source from the interaction UI.

## 1. Core Architecture Principles (LEGO Blocks)
- **Decouple Source from UI**: The source (e.g., a DICOM volume) and the logic to extract a slice from it must be completely independent of `ipywidgets` or `ipyevents`.
- **Composition over Inheritance**: Avoid deep class hierarchies. Apps should be built by snapping together a `Source/Slicer`, a `UI Controller`, and an `Image Viewer`.
- **RGB Hand-off**: The `Slicer` produces an RGB (or RGBA) image based on parameters. The `Image Viewer` only knows how to display RGB(A) images and handle user inputs (clicks, drags). Controls of how is slices are hadles by widget which has slicer. Composing app mean- i take slicer with its ui class and distplay widget and programm my custom calbacks which modify whatevern i need.
- **Callback-Driven**: Viewers communicate with Slicers via callbacks, passing UI events or updated parameters to get a new RGB frame.

## 2. Component Refactoring

### A. The "Slicers" (Pure Math & Data, No UI)
Slicers hold the N-dimensional data and the logic to extract a 2D RGB slice given specific parameters.
- [ ] **`DicomSlicer` Refactor**: 
    - Ensure it operates purely on data (preparing for 5D `(t, z, y, x, c)` arrays).
    - Expose a clean method (e.g., `get_rgb_slice(z, window, level, ...)`) that returns a PIL Image or RGB array.
    - Strictly separate math/data logic from any `ipywidget` state.
- [ ] **Extensibility**: Design the pattern so adding a `CPRSlicer` (Curved Planar Reformation with angle parameters) or a `MicroscopySlicer` (multi-channel) is as simple as writing a new math class that outputs RGB.

### B. The "Viewers" (Image Display & Interaction, No Data Logic)
Viewers are `ipywidgets` that display an RGB image and capture user interaction. They know nothing about DICOM or N-dimensional arrays.
- [ ] **`SimpleImageViewer`**: 
    - A basic `ipywidget.Image` wrapper.
    - **No `ipyevents` dependency** (safe fallback for environments where `ipyevents` is unavailable).
- [ ] **`InteractiveImageViewer`**:
    - Uses `ipyevents` to capture mouse/keyboard events (drag, click, scroll) over the RGB image.
    - Fires generic callbacks (e.g., `on_drag(dx, dy)`, `on_scroll(delta)`) without knowing what the events do to the underlying data.

### C. The "UI Controls" (Parameter Inputs)
- [ ] Extract standard widget control blocks (e.g., Z-index slider, Window/Level sliders, mask toggles) into reusable UI components that emit parameter changes.

### D. The "Apps" (Wiring it together)
Apps are the high-level classes that wire a Slicer, UI Controls, and a Viewer together.
- [ ] **`DicomWidget` (Fallback/Standard)**:
    - **MUST preserve existing API.**
    - Wires a `DicomSlicer` + standard sliders + `SimpleImageViewer`. 
    - Does NOT use `ipyevents`. Guaranteed to work in basic Jupyter environments.
- [ ] **`InteractiveDicomWidget` (Advanced)**:
    - Wires a `DicomSlicer` + standard sliders + `InteractiveImageViewer`.
    - Maps viewer events to slicer parameters (e.g., map right-click drag to Window/Level changes, scroll wheel to Z-index changes).

## 3. Specific Implementation Tasks

- [ ] **Remove `ipyevents` from base widgets**: Ensure `DicomWidget` imports and functions flawlessly without `ipyevents` installed.
- [ ] **Standardize Callback Signatures**: Define clear protocols for how Apps request new frames from Slicers when Viewers trigger events.
- [ ] **Flatten the Hierarchy**: Audit `InteractiveViewer` and `InteractiveSlicer` to remove deep inheritance. Move towards a model where an App *has a* Viewer and *has a* Slicer.
- [ ] **Generalize N-Dimensional Slicing**: Update `DicomSlicer` to handle arbitrary axes slicing gracefully.
