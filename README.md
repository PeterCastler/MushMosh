# MushMosh

MushMosh is a cross-platform desktop application for creative video manipulation that leverages the art of datamoshing. Built on top of FFMPEG, it empowers video artists to replace i-frames with p-frames using two distinct techniques, giving rise to unique visual effects.

---

## Overview

MushMosh focuses exclusively on two datamoshing techniques:

- **Wipe Mosh:** Replaces a single i-frame with a p-frame to gradually phase out the previous shot’s textures and colors.
- **Persistent Mosh:** Replaces all i-frames within a selected time range, extending the previous shot’s look (texture and color) across that period while retaining only motion data from the following shot(s).

The app features a GUI designed to simplify the process of importing files and applying datamosh effects without being overwhelmed by too many features and complexity.

---

## Features

- **Dual Datamosh Modes:**
  - **Wipe Mosh:** Single-frame replacement for smooth transitions.
  - **Persistent Mosh:** Time-range replacement to sustain visual continuity.
  
- **Intuitive GUI Layout:**
  - **Media Pool (Left):** Central repository for all session files.
  - **Rendered Preview (Center):** Real-time visual output of timeline edits.
  - **Settings Panel (Right):** Dual-tabbed interface:
    - **Composition & Export Settings:** Configure resolution, FPS, bitrate, audio, codecs, containers, color grading, and more.
    - **Additional Settings:** Adjust timeline snapping, grid configuration, UI preferences, and performance options.
  - **Timeline (Bottom):** Multi-layer editing area with:
    - A slim playhead band for navigation.
    - A numbered band for temporal selections.
    - A larger clip view area where clip duration is visually represented.
  
- **Timeline Interaction:**
  - **Playhead Navigation:** Dedicated buttons for jumping to the previous or next i-frame.
  - **Dynamic Datamosh Button:** Context-sensitive activation that switches between “Insert Wipe Mosh” and “Insert Persistent Mosh” based on selection mode.
  - **Visual Feedback:** Insertion of red vertical lines (with removable red dots) on clips to indicate where i-frame replacements have been applied.
  - **Non-Destructive Editing:** All changes (p-frame insertions) can be undone, preserving original clip data.

- **Workflow Integration:**
  - **Drag-and-Drop:** Import videos by dragging them into the Media Pool or Rendered Preview.
  - **Seamless Session Management:** Once imported, clips can be arranged on the timeline, zoomed for precise editing, and modified with datamosh effects.

---

## How It Works

1. **Session Initialization:**
   - Drag and drop videos into the Media Pool or Rendered Preview to add files to the current session.

2. **Timeline Editing:**
   - Arrange clips on the timeline, which is divided into three horizontal bands (playhead, numbered time markers, and clip display).
   - Choose between clip-based or time-based selections. When selecting by time, configure the “grid” (time unit: frames or seconds/milliseconds) for precision.

3. **Datamosh Insertion:**
   - **Wipe Mosh:** Position the playhead over an i-frame on a selected clip. The “Datamosh” button becomes “Insert Wipe Mosh,” which replaces the single i-frame with a p-frame and marks the change with a red line.
   - **Persistent Mosh:** Make a temporal selection (or select sequential clips) to cover a desired time period. The “Datamosh” button then switches to “Insert Persistent Mosh,” replacing all i-frames in that segment. The resulting modifier spans across all layers and can be adjusted by dragging its handles.

4. **Preview & Export:**
   - Use the Rendered Preview to view the effect as it will appear in the final export.
   - Adjust export settings in the Composition & Export tab, then process the video using FFMPEG.

---

## Proposed Tech Stack

### Frontend/GUI
- **Electron:** Ideal for building cross-platform desktop applications with web technologies.
- **React.js or Vue.js:** For developing a responsive and dynamic user interface.
- **HTML5, CSS3, and JavaScript:** Core technologies for UI development.

### Backend/Video Processing
- **FFMPEG:** The powerful open-source multimedia framework that handles all video processing tasks.
- **Node.js:** Manages backend operations and interfaces directly with FFMPEG.

### Additional Libraries & Tools
- **Timeline Library:** Consider integrating a specialized timeline library or developing a custom solution for precise clip and time management.
- **State Management:** Redux (if using React) or Vuex (if using Vue) to handle complex application state.
- **Cross-Platform Build Tools:** Tools like Electron Forge or Electron Builder for packaging and deployment.

---

## Composition & Export Settings (Tab 1)

- **Resolution:** Width x Height settings.
- **Frame Rate (FPS):** Adjust frames per second.
- **Bitrate:** Set video and audio bitrate.
- **Audio:** Enable/disable, choose channels, sampling rate.
- **Codecs & Containers:** Options like H264/MP4, Uncompressed, AVI, etc.
- **Color Grading & Filters:** Apply visual effects and corrections.
- **Aspect Ratio & Compression:** Manage quality and file size.

---

## Additional Settings (Tab 2) – Suggested Enhancements

- **Timeline & Playback Options:**
  - Grid configuration: Define grid units (frames vs. seconds/milliseconds).
  - Playhead snapping: Toggle and customize snapping behavior to i-frames.
  - Layer management: Adjust visibility and stacking order.
  
- **User Interface Preferences:**
  - Customizable workspace layout.
  - Theme options (light/dark mode).

- **Editing Controls:**
  - Undo/Redo functionality for non-destructive editing.
  - Version control for tracking changes.

- **Performance & Resource Management:**
  - Cache settings for smoother preview rendering.
  - Options to balance render quality and processing speed.

---

## Final Notes

This document serves as the handover guide for the MushMosh project. While the primary focus is on two datamosh techniques, the design allows for potential future enhancements. The recommended tech stack leverages familiar web technologies while introducing robust tools like Electron, Node.js, and FFMPEG for optimal performance across platforms.

Team members are encouraged to discuss and iterate on this design, ensuring that all components are modular, maintainable, and scalable. Your expertise in HTML/CSS/JS provides a strong foundation to quickly adapt to new frameworks that enhance the overall success of this project.

Happy coding!
