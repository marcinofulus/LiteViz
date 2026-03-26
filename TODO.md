# LiteViz Development Roadmap

## DONE
- **AnnotationCanvas Performance**: 
    - Moved `wheel` events to a non-throttled `events_fast` handler.
    - Optimized slice scrolling to be fluid and un-capped by FPS.
- **Improved Interaction Safety**:
    - Added requirement for **Cmd/Ctrl** modifier key for mask drawing and click callbacks.
    - Prevented accidental edits during navigation or Window/Level (right-click drag) adjustments.
- **Modular Event System (`UICanvas`)**:
    - Implemented `UICanvas` class that replicates `input_manager.js` logic in Python.
    - Supports advanced event detection: Drag vs. Click (5px threshold), Single vs. Double click (250ms).
    - Standardized event schema with `modifierMask` (Shift: 1, Ctrl: 2, Alt: 4).
    - Integrated throttling (50 msg/sec) for high-frequency events.
- **Layout Metadata (`WindowMeta`)**:
    - Added hierarchical window mapping to support multi-view layouts (Axial, Coronal, Sagittal, VRT).
    - Implemented recursive `find_subwindow` for mapping global coordinates to local view coordinates.
- **Generic Prototyping Lab**:
    - Created `SimpleRGBWidget` in `dicom_utils/base_widgets.py` as a lightweight bridge for non-DICOM image data.
    - Refactored `AnnotationCanvas` to be decoupled from DICOM-specific parameters (`hu`).
- **Documentation & Tutorials**:
    - Created `notebooks/UI_canvas.ipynb` demonstrating `UICanvas` integration.
    - Added "Lab" and "Controller" pattern examples to `notebooks/liteviz_tutorial.ipynb`.

## Planned (Architectural Redesign)

The goal is to transform LiteViz into a modular, "LEGO-block" framework for fast prototyping.

### 1. Core Architecture Principles
- **Decouple Source from UI**: The source (e.g., a DICOM volume) and the logic to extract a slice must be independent of `ipywidgets`.
- **Composition over Inheritance**: Apps should be built by snapping together a `Source/Slicer`, a `UI Controller`, and an `Image Viewer`.
- **RGB Hand-off**: Slicers produce RGB(A) arrays; Viewers only know how to display them and capture input.

### 2. Component Refactoring

#### A. The "Slicers" (Pure Math & Data)
- [ ] **`DicomSlicer` Refactor**: Ensure it operates purely on data (preparing for 5D arrays).
- [ ] **Extensibility**: Design pattern for easy addition of `CPRSlicer` or `MicroscopySlicer`.

#### B. The "Viewers" (Display & Interaction)
- [ ] **`SimpleImageViewer`**: A basic `ipywidget.Image` wrapper without `ipyevents` dependency.
- [ ] **`InteractiveImageViewer`**: Uses `ipyevents` to capture mouse/keyboard events and fire generic callbacks.

#### C. The "Apps" (Wiring)
- [ ] **`DicomWidget` (Standard)**: Preserve existing API; wire `DicomSlicer` + sliders + `SimpleImageViewer`.
- [ ] **`InteractiveDicomWidget` (Advanced)**: Wire `DicomSlicer` + sliders + `InteractiveImageViewer`.

### 3. Implementation Tasks
- [ ] **Remove `ipyevents` from base widgets**: Ensure `DicomWidget` functions without it.
- [ ] **Standardize Callback Signatures**: Define protocols for Apps to request new frames from Slicers.
- [x] **Flatten the Hierarchy**: Audit classes to remove deep inheritance. (Verified: Core components like InteractiveDicomWidget and UICanvas already use composition).
