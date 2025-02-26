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
    - **Flattened Preview:** Displays a combined view of all timeline layers and applied effects.
    - **Quality Selection:** Choose from preview quality options (25%, 50%, 75%, 100%) to balance visual fidelity and playback performance.
    - **Outdated Preview Indicator:** A "⚠️ Preview Outdated" message appears when changes are made that are not reflected in the current preview.
  - **Settings Panel (Right):** Dual-tabbed interface:
    - **Composition & Export Settings:** Configure resolution, FPS, bitrate, audio, codecs, containers, etc.
    - **Additional Settings:** Adjust timeline snapping, grid configuration, UI preferences, etc.
  - **Timeline (Bottom):** Multi-layer editing area with:
    - A numbered timeline with a playhead for navigation.
    - A larger clip view area where clips and their duration are visually represented.
  
- **Timeline Interaction:**
  - **Selection Modes:** Toggle between two modes via switch in timeline's top-left corner:
    - **Clip Selection** (pointing hand cursor):
      - Single/Multi-select: Click clips to select/deselect, click empty space to clear selection
      - Wipe Mosh Context: Activates "Insert Wipe Mosh" button when:
        - Playhead is positioned on an i-frame
        - At least one clip is selected
      - Auto-align: Playhead snaps to nearest i-frame when applying effect
    
    - **Time Selection** (i-beam cursor):
      - Range Selection:
        - Click-drag from sideways to create a time selection
      - Persistent Mosh Context: Activates "Insert Persistent Mosh" button when:
        - Any time range is selected
        - Selection contains at least one i-frame

  - **Selection conversion:**
    - When a selection has been made, switching between modes (clip/time) converts the selection.
        - Clip selection to time selection spans the duration of selected clips, including gaps.
        - Time selection to clip selection selects clips within the temporal range.

  - **Persistent Mosh Handling:**
    - Time selection snaps to i-frames with user options:
      - Snap to include/exclude i-frame at selection start.
      - Snap to clip edges (start/end).
    - Minimum selection size spans at least two i-frames.
    - Persistent Mosh updates preview for all i-frames within selection.

  - **Playback Controls** (ordered left-to-right):
    - [Stop] Resets playhead to start
    - [Play/Pause] Toggles playback state
    - [Previous i-frame] Jumps to prior i-frame
    - [Insert Wipe/Persistent Mosh] Context-sensitive action button
    - [Next i-frame] Jumps to subsequent i-frame
    
  - **State Management:**
    - Button labels dynamically reflect active selection mode
    - Action button disabled when preconditions unmet:
      - Wipe Mosh: No selected clip or invalid playhead position
      - Persistent Mosh: No time selection

  - **Visual Feedback:**
    - Single i-frame replacements (Wipe Mosh): Displayed as vertical red line (1px width) with:
        - Accompanying "delete" button is a dot (5px diameter) centered on the line with a white "×" symbol (1px stroke) in the dot's center.
        - Clicking the dot with the "x" removes both the i-frame replacement and the red line, returning the original i-frame that was replaced.
    - Making a Time Selection creates a 50% transparent blue overlay that spans the entire height of the timeline and with two non-transparent blue lines (3px width) at both ends of the selection that allows the user to click and drag to resize the selected range of time.
        Hover effects in Time Selection mode:
            - If the cursor moves outside of the selected time range, the blue lines shrink to 1px width.
            - If the cursor moves back inside the selected time range, the blue lines grow back to 3px width.
            - If the cursor hovers over the blue lines, the lines grow to 5px width and the cursor changes to a double-sided horizontal arrow that communicates to the user that they can click and drag to resize the selected time range.
        - When a time selection is made and the user clicks on the "Insert Persistent Mosh" button, the selected range of i-frames is replaced with p-frames and the blue selection is replaced with an animated overlay featuring:
        - Semi-transparent red diagonal lines (45°, 1px stroke, 2px spacing)
      - Continuous left-to-right translation animation (2s duration)
      - Persistent "x" dot indicator in the corner of the overlay, matches the single-replacement styling
      - Clicking the "x" dot removes overlay and reverts all frames in range to the original i-frames
  
  - **Non-Destructive Editing:** All changes (i-frame replacements / p-frame insertions) can be undone, preserving original clip data.

- **Undo/Redo System:**
  - Every action is undoable, including selections and settings changes.
  - Undo history is capped at 100 actions.

- **Variable Framerate (VFR) Handling:**
  - VFR is not allowed. The app prevents imports and displays a warning.

- **Clip Boundaries & Transitions:**
  - Spillover is intentional; datamosh effects persist across clips unless a new i-frame is introduced.
  - Blank timeline between spaced clips retains the last visible i-frame of the previous clip.
  - Snapping option allows clips to align when dragged.

- **Snapping Behavior:**
  - Snapping occurs only when dragging, not during playback.
  - Global toggle for snapping on/off, plus granular snapping settings.
  - When global snapping is off, the user can temporarily enable snapping during an action by holding down the Ctrl/Cmd key.

- **FFMPEG Performance & Caching:**
  - Preview limitations exist because clips are separate until rendered/exported.
  - Background rendering is ideal but may be complex.
  - Cache size must be managed to avoid excessive memory usage.
  - A loading indicator is required for long operations.

- **File Handling & Session Saving:**
  - Save sessions using JSON metadata (timeline, selections, modifications).
  - Support temporary video cache files for faster previews.
  - Implement a missing file recovery prompt when reopening sessions.

- **Terminal Output:**
  - Option to toggle terminal visibility for advanced users.

- **Default Export Settings:**
  - User chooses which clip's settings to inherit or sets custom settings.
  - The app exports one file at a time—no batch processing.

- **Feature Scope Management:**
  - Additional features will belong to a separate project; MushMosh remains focused on datamoshing only.

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
   - **Generate a flattened preview** by clicking the "Preview" button. This renders a combined view of your timeline, with all datamosh effects applied.
   - **Select preview quality** (25%, 50%, 75%, 100%) to optimize preview render time.
   - **Further changes made to the project will invalidate the preview** and a "⚠️ Preview Outdated" message will be displayed.
   - Adjust export settings in the Composition & Export tab, then process and export the video using FFMPEG.

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
- **Export Duration:** By default, the export range starts from frame/second "0" of the timeline and extends to the last frame of the final clip on the timeline. The user can set a custom start and end time for the export manually: "Start Time: [00:00:00]" and "End Time: [00:00:00]" with the brackets representing input fields where the user can type in the desired start and end times.

---

## Additional Settings (Tab 2) – Suggested Enhancements

- **Timeline & Playback Options:**
  - Grid configuration: Define grid units (frames vs. seconds/milliseconds).
  - Snapping:
    - Playhead: Toggle snapping to i-frames.
    - Selection modes:
        - Time selection:
            - Toggle snapping to Grid
            - Toggle snapping to Clips' two edges (start/end)
            - Toggle snapping to i-frames
        - Clip Selection:
            - Toggle auto-multi-select
            - Toggle auto-align
  
- **User Interface Preferences:**
    - Theme options (light/dark mode).

- **Editing Controls:**
  - Undo/Redo functionality for non-destructive editing (invisible, but available via keyboard shortcuts: Ctrl/Cmd+Z and Shift+Ctrl/Cmd+Z)

- **Performance & Resource Management:**
  - Cache settings for smoother preview rendering.
  - Options to balance render quality and processing speed.

---

## Final Notes

This document serves as the development guide for the MushMosh project. While the primary focus is on two datamosh techniques, the design allows for potential future enhancements. The recommended tech stack leverages Python's robust ecosystem while utilizing FFMPEG for optimal video processing across platforms.

Contributors are encouraged to discuss and iterate on this design, ensuring that all components are modular, maintainable, and scalable. The combination of CustomTkinter for the GUI and FFMPEG for video processing provides a strong foundation to build upon and extend with additional features in the future.

This project has a lot of potential for video manipulation with obscure effects, and I'm excited to see what will come of it.

Happy coding!
