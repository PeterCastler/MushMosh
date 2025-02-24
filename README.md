# MushMosh

MushMosh is a cross-platform desktop application for creative video manipulation that leverages the art of datamoshing. Built on top of FFMPEG, it empowers video artists to replace i-frames with p-frames using two distinct techniques, giving rise to unique visual effects.

---

## Overview

MushMosh focuses exclusively on two datamoshing techniques:

- **Wipe Mosh:** Replaces a single i-frame with a p-frame to gradually phase out the previous shot's textures and colors.
- **Persistent Mosh:** Replaces all i-frames within a selected time range, extending the previous shot's look (texture and color) across that period while retaining only motion data from the following shot(s).

The app features a GUI designed to simplify the process of importing files and applying datamosh effects without being overwhelmed by too many features and complexity.

---

## Features

- **Dual Datamosh Modes:**
  - **Wipe Mosh:** Single-frame replacement for transitions.
  - **Persistent Mosh:** Time-range replacement to sustain visual continuity.
  
- **User Interface Layout:**
  - **Session Pool (Left):** Central repository for all session files.
  - **Rendered Preview (Center):** Real-time visual output of timeline edits (final look of the video).
  - **Settings Panel (Right):** Dual-tabbed interface:
    - **Composition & Export Settings:** Configure resolution, FPS, bitrate, audio, codecs, containers, etc.
    - **Additional Settings:** Adjust timeline snapping, grid configuration, UI preferences, etc.
  - **Timeline (Bottom):** Multi-layer editing area with:
    - An numbered timeline with a playhead for navigation.
    - A larger clip view area where clips and their duration are visually represented.
  
- **Timeline Interaction:**
  - **Playback & Navigation:** Dedicated buttons for navigating between i-frames, playback (play/pause), and the "Datamosh" button.
  - **Dynamic Datamosh Button:** Context-sensitive activation that switches between "Datamosh", "Insert Wipe Mosh" and "Insert Persistent Mosh" based on the position of the playhead and the current mode of selection. When the playhead is not on an i-frame or not on a selected clip, the button will be disabled and say "Datamosh". When the playhead is over an i-frame of a selected clip, the button will say "Insert Wipe Mosh". When the user makes a temporal selection, the button will say "Insert Persistent Mosh". The playhead does not need to be on an i-frame nor in the selected range, and not even on any selected clip to use the "Insert Persistent Mosh" button. The only prerequisite for using the "Insert Persistent Mosh" button is that the user has made a temporal selection.

  - **Visual Feedback:**  
    - Single i-frame replacements (Wipe Mosh): Displayed as vertical red line (1px width) with:
      - Accompanying dot (5px diameter) centered on line
      - White "×" symbol (1px stroke) in dot's center
      - Clicking the dot removes both line and the i-frame replacement  
    - Range replacements (Persistent Mosh): Highlighted with animated overlay featuring:
      - Semi-transparent red diagonal lines (45°, 1px stroke, 2px spacing)
      - Continuous left-to-right translation animation (2s duration)
      - Persistent "x" dot indicator in the corner of the overlay, matches the single-replacement styling
      - Clicking the "x" dot removes overlay and reverts all frames in range
  - **Non-Destructive Editing:** All changes (i-frame replacements / p-frame insertions) can be undone, preserving original clip data.
  - **Selection Mode:**
    - Located in the top left corner of the timeline, two buttons allow for different selection modes:
      - Clip-based selection tool (pointing hand cursor): Allows selecting clips one by one (holding shift allows for multi-select). When the playhead is atop of an i-frame, the datamosh button will say "Insert Wipe Mosh".
      - Time-based selection tool (i-beam cursor): Allows selecting a range of time overlaying multiple clips. When the playhead is within a selected range, the datamosh button will say "Insert Persistent Mosh".

- **Workflow Integration:**
  - **Drag-and-Drop:** Import videos by dragging them into the Session Pool or Rendered Preview.
  - **Seamless Session Management:** Once imported, clips can be arranged on the timeline, zoomed for more granular editing, and modified with datamosh effects.

---

## How It Works

1. **Session Initialization:**
   - Drag and drop videos into the Session Pool or Rendered Preview to add files to the current session.

2. **Timeline Editing:**
   - Arrange clips on the timeline, which is divided into three horizontal bands (playhead, numbered time markers, and clip display).
   - Choose between clip-based or time-based selections. When selecting by time, configure the "grid" (time unit: frames or seconds/milliseconds) for precision.

3. **Datamosh Insertion:**
   - **Wipe Mosh:** Position the playhead over an i-frame on a selected clip. The "Datamosh" button becomes "Insert Wipe Mosh," which replaces the single i-frame with a p-frame and marks the change with a red line.
   - **Persistent Mosh:** Make a temporal selection (or select sequential clips) to cover a desired time period. The "Datamosh" button then switches to "Insert Persistent Mosh," replacing all i-frames in that segment. The resulting modifier spans across all layers and can be adjusted by dragging its handles.

4. **Preview & Export:**
   - Use the Rendered Preview to view the effect as it will appear in the final export.
   - Adjust export settings in the Composition & Export tab, then process the video using FFMPEG.

---

## Tech Stack
- **Language:** Python (3.8+)

### Frontend/GUI
- **CustomTkinter:** Modern and customizable UI framework for creating desktop applications
- **OpenCV (cv2):** For video processing, preview rendering, and thumbnails

### Backend/Video Processing
- **FFMPEG:** Core video processing engine via ffmpeg-python
- **ffmpeg-python:** Python bindings for FFMPEG
- **numpy:** Essential for efficient video frame manipulation

### Additional Libraries & Tools
- **pathlib:** Cross-platform path handling
- **typing:** Type hints for better code maintainability
- **logging:** Debug and error tracking

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
