#!/usr/bin/env python3
import sys
import os
import subprocess
import time
import re
import threading
import numpy as np
import json
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QLabel, QCheckBox, QSlider
from PyQt5.QtGui import QImage, QPixmap, QPainter
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QMutex, QRect

class FrameBuffer:
    def __init__(self, max_size=10):
        self.buffer = []
        self.max_size = max_size
        self.mutex = QMutex()
        
    def push(self, frame):
        self.mutex.lock()
        if len(self.buffer) >= self.max_size:
            self.buffer.pop(0)  # Remove oldest frame
        self.buffer.append(frame)
        self.mutex.unlock()
        
    def get_latest(self):
        self.mutex.lock()
        if not self.buffer:
            self.mutex.unlock()
            return None
        frame = self.buffer[-1]
        self.mutex.unlock()
        return frame
        
    def clear(self):
        self.mutex.lock()
        self.buffer.clear()
        self.mutex.unlock()


class VideoProcessor(QThread):
    frame_ready = pyqtSignal()
    position_changed = pyqtSignal(int)  # Signal to update timeline position (in milliseconds)
    duration_changed = pyqtSignal(int)  # Signal to update total duration (in milliseconds)
    
    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
        self.running = False
        self.paused = False
        self.current_position = 0  # Current position in milliseconds
        self.duration = 0  # Duration in milliseconds
        self.seek_position = -1  # Position to seek to (-1 means no seeking)
        self.seek_mutex = QMutex()  # Mutex to protect seek operations
        self.position_mutex = QMutex()  # Mutex to protect position updates
        
        # Get video information using ffprobe
        try:
            # Get duration directly from container
            duration_cmd = ['ffprobe', '-v', 'error', '-show_entries', 
                           'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', 
                           video_path]
            duration_output = subprocess.check_output(duration_cmd).decode('utf-8').strip()
            if duration_output and duration_output != 'N/A':
                try:
                    self.duration = int(float(duration_output) * 1000)  # Convert to milliseconds
                    print(f"Video duration from container: {self.duration/1000:.2f} seconds")
                except ValueError:
                    self.duration = 0
            
            # Get video dimensions and frame rate
            info_cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
                       '-show_entries', 'stream=width,height,r_frame_rate', 
                       '-of', 'default=noprint_wrappers=1:nokey=1', 
                       video_path]
            info_output = subprocess.check_output(info_cmd).decode('utf-8').strip().split('\n')
            
            if len(info_output) >= 3:
                self.width = int(info_output[0])
                self.height = int(info_output[1])
                
                # Parse frame rate
                fps_parts = info_output[2].split('/')
                if len(fps_parts) == 2:
                    self.frame_rate = float(fps_parts[0]) / float(fps_parts[1])
                else:
                    self.frame_rate = float(info_output[2])
            else:
                raise ValueError("Couldn't get video dimensions and frame rate")
                
            # If duration is still not available, estimate it
            if self.duration <= 0:
                # Count frames to get duration
                frame_count_cmd = ['ffprobe', '-v', 'error', '-count_frames', 
                                  '-select_streams', 'v:0', '-show_entries', 
                                  'stream=nb_read_frames', '-of', 
                                  'default=noprint_wrappers=1:nokey=1', 
                                  video_path]
                try:
                    frame_count_output = subprocess.check_output(frame_count_cmd, timeout=10).decode('utf-8').strip()
                    if frame_count_output and frame_count_output.isdigit():
                        frame_count = int(frame_count_output)
                        self.duration = int((frame_count / self.frame_rate) * 1000)
                        print(f"Video duration from frame count: {self.duration/1000:.2f} seconds")
                except (subprocess.SubprocessError, ValueError, subprocess.TimeoutExpired):
                    # If frame counting times out or fails, use a default duration
                    self.duration = 60000  # Default to 1 minute
                    
        except (subprocess.CalledProcessError, ValueError, IndexError) as e:
            print(f"Error getting video information: {e}")
            self.width = 640
            self.height = 480
            self.frame_rate = 30.0
            self.duration = 60000  # Default to 1 minute
        
        # Create frame buffer
        buffer_size = max(30, int(self.frame_rate / 4))  # Buffer 1/4 second of video
        self.frame_buffer = FrameBuffer(max_size=buffer_size)
        
        # Detect hardware acceleration after initializing other variables
        self.hw_accel_method = None
        self.hw_acceleration_enabled = True  # Flag to control hardware acceleration
    
    def detect_hw_acceleration(self):
        """Detect available hardware acceleration methods"""
        if not self.hw_acceleration_enabled:
            print("Hardware acceleration disabled by user")
            return None
            
        try:
            # Get list of available hardware accelerators
            result = subprocess.run(
                ['ffmpeg', '-hide_banner', '-hwaccels'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            
            # Parse the output to find available methods
            hw_accels = result.stdout.strip().split('\n')
            if len(hw_accels) > 1:  # First line is usually "Hardware acceleration methods:"
                hw_accels = hw_accels[1:]
                
            available_methods = [method.strip() for method in hw_accels if method.strip()]
            
            if available_methods:
                print(f"Available hardware acceleration methods: {', '.join(available_methods)}")
                
                # Prioritize methods based on common performance
                for method in ['cuda', 'amf', 'qsv', 'd3d11va', 'dxva2']:
                    if method in available_methods:
                        print(f"Selected hardware acceleration method: {method}")
                        return method
                
                # If none of the preferred methods are available, use the first one
                print(f"Selected hardware acceleration method: {available_methods[0]}")
                return available_methods[0]
                
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            print(f"Error detecting hardware acceleration: {e}")
        
        print("No hardware acceleration available, using software decoding")
        return None
        
    def seek(self, position_ms):
        """Set the position to seek to in milliseconds"""
        self.seek_mutex.lock()
        self.seek_position = position_ms
        self.seek_mutex.unlock()
    
    def run(self):
        self.running = True
        
        # Emit the duration when starting playback
        if self.duration > 0:
            self.duration_changed.emit(self.duration)
        
        # Detect hardware acceleration at runtime
        self.hw_accel_method = self.detect_hw_acceleration()
        
        # Try hardware acceleration first if available
        if self.hw_accel_method:
            success = self.run_with_hw_accel()
            if not success and self.running:
                print("Hardware acceleration failed, falling back to software decoding")
                self.hw_accel_method = None
                self.run_with_sw_decoding()
        else:
            # Use software decoding
            self.run_with_sw_decoding()
    
    def run_with_hw_accel(self):
        """Run video processing with hardware acceleration"""
        try:
            # Base FFmpeg command
            cmd = ['ffmpeg', '-y']
            
            # Add hardware acceleration
            if self.hw_accel_method == 'cuda':
                cmd.extend(['-hwaccel', 'cuda'])
            elif self.hw_accel_method == 'amf':
                cmd.extend(['-hwaccel', 'amf'])
            elif self.hw_accel_method == 'qsv':
                cmd.extend(['-hwaccel', 'qsv'])
            elif self.hw_accel_method == 'd3d11va':
                cmd.extend(['-hwaccel', 'd3d11va'])
            elif self.hw_accel_method == 'dxva2':
                cmd.extend(['-hwaccel', 'dxva2'])
            else:
                cmd.extend(['-hwaccel', self.hw_accel_method])
            
            # Input file
            cmd.extend(['-i', self.video_path])
            
            # Output settings - ensure we convert back to a format we can process
            cmd.extend([
                '-f', 'image2pipe',
                '-pix_fmt', 'rgb24',  # Force RGB24 pixel format for our processing
                '-vcodec', 'rawvideo',
                '-vsync', 'cfr',  # Constant frame rate
                '-'
            ])
            
            print(f"Running FFmpeg with hardware acceleration ({self.hw_accel_method})")
            print(f"Command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                bufsize=10**8
            )
            
            # Start a separate thread to monitor progress
            self.start_progress_monitor()
            
            return self.process_frames(process)
            
        except Exception as e:
            print(f"Error with hardware acceleration: {e}")
            return False
    
    def run_with_sw_decoding(self):
        """Run video processing with software decoding"""
        try:
            cmd = [
                'ffmpeg',
                '-i', self.video_path,
                '-f', 'image2pipe',
                '-pix_fmt', 'rgb24',
                '-vcodec', 'rawvideo',
                '-vsync', 'cfr',
                '-'
            ]
            
            print("Running FFmpeg with software decoding")
            print(f"Command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                bufsize=10**8
            )
            
            # Start a separate thread to monitor progress
            self.start_progress_monitor()
            
            return self.process_frames(process)
            
        except Exception as e:
            print(f"Error with software decoding: {e}")
            return False
    
    def start_progress_monitor(self):
        """Start a separate thread to monitor playback progress"""
        self.progress_thread = threading.Thread(target=self.monitor_progress)
        self.progress_thread.daemon = True
        self.progress_thread.start()
    
    def monitor_progress(self):
        """Monitor playback progress by analyzing the video file"""
        start_time = time.time()
        
        while self.running:
            # Calculate current position based on elapsed time
            elapsed_time = time.time() - start_time
            position_ms = int(elapsed_time * 1000)
            
            # Update position
            self.position_mutex.lock()
            self.current_position = position_ms
            self.position_mutex.unlock()
            
            # Emit position update
            self.position_changed.emit(position_ms)
            
            # Check for seek requests
            self.seek_mutex.lock()
            seek_requested = self.seek_position >= 0
            if seek_requested:
                # Update start time to account for seek
                start_time = time.time() - (self.seek_position / 1000.0)
                self.seek_position = -1  # Reset seek position
            self.seek_mutex.unlock()
            
            # Sleep to avoid consuming too much CPU
            time.sleep(0.1)  # Update position 10 times per second
    
    def process_frames(self, process):
        """Process frames from the FFmpeg output"""
        frame_size = self.width * self.height * 3  # 3 bytes per pixel (RGB)
        
        try:
            while self.running:
                # Check if we need to seek
                self.seek_mutex.lock()
                seek_requested = self.seek_position >= 0
                seek_pos = self.seek_position
                self.seek_mutex.unlock()
                
                if seek_requested:
                    # Stop current process
                    process.terminate()
                    
                    # Start a new process with seek
                    seek_sec = seek_pos / 1000.0  # Convert to seconds
                    cmd = [
                        'ffmpeg',
                        '-ss', f"{seek_sec:.3f}",  # Seek position
                        '-i', self.video_path,
                        '-f', 'image2pipe',
                        '-pix_fmt', 'rgb24',
                        '-vcodec', 'rawvideo',
                        '-vsync', 'cfr',
                        '-'
                    ]
                    
                    print(f"Seeking to {seek_sec:.3f} seconds")
                    process = subprocess.Popen(
                        cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, 
                        bufsize=10**8
                    )
                
                # Read a frame
                raw_frame = process.stdout.read(frame_size)
                if not raw_frame or len(raw_frame) < frame_size:
                    # Check if there was an error
                    error_output = process.stderr.read()
                    if error_output:
                        print(f"FFmpeg error: {error_output.decode('utf-8', errors='ignore')}")
                    # End of video or error
                    break
                    
                # Convert to numpy array
                frame = np.frombuffer(raw_frame, np.uint8).reshape((self.height, self.width, 3))
                
                # Add to buffer
                self.frame_buffer.push(frame.copy())  # Make a copy to ensure data ownership
                
                # Emit signal that a new frame is available
                self.frame_ready.emit()
                
            return True
            
        except Exception as e:
            print(f"Error processing frames: {e}")
            return False
        finally:
            if process:
                process.terminate()
    
    def stop(self):
        self.running = False
        self.wait()
        self.frame_buffer.clear()
    
    def toggle_hw_acceleration(self, enabled):
        """Enable or disable hardware acceleration"""
        self.hw_acceleration_enabled = enabled


class VideoPlayerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.setMinimumSize(320, 180)
        self.aspect_ratio = 2.39  # Standard anamorphic aspect ratio
        self.pixel_aspect_ratio = 2.0  # Default PAR for anamorphic content
        
        # Add border styling
        self.setStyleSheet("border: none;")  # Default state
        
    def set_frame(self, frame):
        height, width = frame.shape[:2]
        # Apply PAR correction for anamorphic content
        self.aspect_ratio = (width * self.pixel_aspect_ratio) / height
        bytes_per_line = 3 * width
        self.image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        self.update()
        
    def paintEvent(self, event):
        if self.image:
            painter = QPainter(self)
            
            # Calculate the size maintaining aspect ratio
            widget_width = self.width()
            widget_height = self.height()
            
            # Calculate target size preserving aspect ratio
            if widget_width / widget_height > self.aspect_ratio:
                # Width is too wide, constrain by height
                target_height = widget_height
                target_width = int(target_height * self.aspect_ratio)
            else:
                # Height is too tall, constrain by width
                target_width = widget_width
                target_height = int(target_width / self.aspect_ratio)
            
            # Calculate position to center the image
            x = (widget_width - target_width) // 2
            y = (widget_height - target_height) // 2
            
            # Draw the image with proper aspect ratio
            target_rect = QRect(x, y, target_width, target_height)
            painter.drawImage(target_rect, self.image)
            
    def set_approval_status(self, status):
        if status == "approved":
            self.setStyleSheet("border: 1px solid #4CAF50;")  # Green border
        elif status == "rejected":
            self.setStyleSheet("border: 1px solid #f44336;")  # Red border
        else:
            self.setStyleSheet("border: none;")  # No border


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AnaPrev - Anamorphic Video Player (GPU Accelerated)")
        self.resize(1024, 768)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Create the main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create approval buttons layout
        self.approval_layout = QHBoxLayout()
        self.approve_button = QPushButton("Approve")
        self.reject_button = QPushButton("Reject")
        self.approve_button.setEnabled(False)
        self.reject_button.setEnabled(False)
        self.approve_button.clicked.connect(self.approve_video)
        self.reject_button.clicked.connect(self.reject_video)
        
        # Set default colorless style for buttons
        self.approve_button.setStyleSheet("padding: 5px 15px;")
        self.reject_button.setStyleSheet("padding: 5px 15px;")

        self.approval_layout.addStretch(1)
        self.approval_layout.addWidget(self.approve_button)
        self.approval_layout.addWidget(self.reject_button)
        self.approval_layout.addStretch(1)
        
        # Add approval buttons layout before the video player
        self.layout.addLayout(self.approval_layout)
        
        # Create the video player widget
        self.player = VideoPlayerWidget()
        self.layout.addWidget(self.player, 1)  # Give the player a stretch factor of 1
        
        # Create timeline slider
        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setMinimum(0)
        self.timeline.setMaximum(1000)  # Will be updated when video is loaded
        self.timeline.setValue(0)
        self.timeline.setEnabled(False)
        self.timeline.sliderPressed.connect(self.timeline_pressed)
        self.timeline.sliderReleased.connect(self.timeline_released)
        self.timeline.valueChanged.connect(self.timeline_value_changed)
        self.timeline_dragging = False
        
        # Add time labels
        self.time_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00:00")
        self.duration_label = QLabel("00:00:00")
        self.time_layout.addWidget(self.current_time_label)
        self.time_layout.addStretch(1)
        self.time_layout.addWidget(self.duration_label)
        
        # Create a container for timeline and time labels with reduced spacing
        self.timeline_container = QVBoxLayout()
        self.timeline_container.setSpacing(2)  # Reduce spacing between elements
        self.timeline_container.addWidget(self.timeline)
        self.timeline_container.addLayout(self.time_layout)
        
        # Add timeline container to main layout with minimal margins
        timeline_widget = QWidget()
        timeline_widget.setLayout(self.timeline_container)
        self.layout.addWidget(timeline_widget)
        self.layout.setSpacing(5)  # Reduce spacing between main layout elements
        
        # Create the controls layout
        self.controls_layout = QHBoxLayout()
        
        # Create control buttons
        self.open_button = QPushButton("Open Video")
        self.play_button = QPushButton("Play")
        self.stop_button = QPushButton("Stop")
        
        # Add hardware acceleration toggle
        self.hw_accel_checkbox = QCheckBox("Hardware Acceleration")
        self.hw_accel_checkbox.setChecked(True)
        
        # Add info label
        self.info_label = QLabel("No video loaded")
        
        # Connect button signals
        self.open_button.clicked.connect(self.open_video)
        self.play_button.clicked.connect(self.play_video)
        self.stop_button.clicked.connect(self.stop_video)
        
        # Add buttons to the controls layout
        self.controls_layout.addWidget(self.open_button)
        self.controls_layout.addWidget(self.play_button)
        self.controls_layout.addWidget(self.stop_button)
        self.controls_layout.addWidget(self.hw_accel_checkbox)
        self.controls_layout.addWidget(self.info_label)
        self.controls_layout.addStretch(1)  # Add stretch to push buttons to the left
        
        # Add the controls layout to the main layout
        self.layout.addLayout(self.controls_layout)
        
        # Initialize variables
        self.video_processor = None
        self.video_path = None
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_display)
        
        # Disable play and stop buttons initially
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        # Initialize approval system
        self.initialize_approval_system()
    
    def format_time(self, ms):
        """Format milliseconds as HH:MM:SS"""
        # Ensure ms is a valid number
        if not isinstance(ms, (int, float)) or ms < 0:
            ms = 0
            
        s = int(ms // 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        
        # Cap hours to prevent unreasonable values
        if h > 99:
            h = 99
            
        return f"{h:02d}:{m:02d}:{s:02d}"
    
    def timeline_pressed(self):
        """Called when the timeline slider is pressed"""
        self.timeline_dragging = True
    
    def timeline_released(self):
        """Called when the timeline slider is released"""
        if self.video_processor and self.video_processor.running:
            # Calculate position in milliseconds
            position = int(self.timeline.value() * self.video_processor.duration / 1000)
            # Seek to the position
            self.video_processor.seek(position)
        self.timeline_dragging = False
    
    def timeline_value_changed(self, value):
        """Called when the timeline slider value changes"""
        if self.timeline_dragging and self.video_processor:
            # Update current time label
            position = int(value * self.video_processor.duration / 1000)
            self.current_time_label.setText(self.format_time(position))
    
    def update_timeline(self, position):
        """Update the timeline position"""
        if not self.timeline_dragging and self.video_processor:
            # Ensure position is within valid range
            if position < 0:
                position = 0
            if self.video_processor.duration > 0 and position > self.video_processor.duration:
                position = self.video_processor.duration
                
            # Update slider position
            if self.video_processor.duration > 0:
                slider_pos = int((position * 1000) / self.video_processor.duration)
                # Ensure slider_pos is within valid range (0-1000)
                slider_pos = max(0, min(1000, slider_pos))
                self.timeline.setValue(slider_pos)
            
            # Update current time label
            self.current_time_label.setText(self.format_time(position))
    
    def update_duration(self, duration):
        """Update the video duration"""
        # Ensure duration is reasonable (cap at 24 hours)
        if duration > 24 * 60 * 60 * 1000:
            print(f"Warning: Unreasonable duration detected ({duration/1000/60/60:.2f} hours), capping at 24 hours")
            duration = 24 * 60 * 60 * 1000
            
        self.duration_label.setText(self.format_time(duration))
        self.timeline.setEnabled(True)
    
    def dragEnterEvent(self, event):
        # Accept the drag event if it contains files
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        # Process the dropped files
        if event.mimeData().hasUrls():
            # Get the first URL (we'll only handle one file at a time)
            url = event.mimeData().urls()[0]
            # Convert QUrl to local file path
            file_path = url.toLocalFile()
            
            # Check if it's a video file (simple extension check)
            video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']
            if any(file_path.lower().endswith(ext) for ext in video_extensions):
                self.load_video(file_path)
                
                # Create a temporary processor to load the first frame
                temp_processor = VideoProcessor(file_path)
                temp_processor.hw_acceleration_enabled = self.hw_accel_checkbox.isChecked()
                
                # Start the processor briefly to get the first frame
                temp_processor.start()
                time.sleep(0.1)  # Give it a moment to process
                
                # Get the first frame from the buffer if available
                first_frame = temp_processor.frame_buffer.get_latest()
                if first_frame is not None:
                    self.player.set_frame(first_frame)
                
                # Stop the temporary processor
                temp_processor.stop()
    
    def load_video(self, file_path):
        # Stop any current playback
        if self.video_processor and self.video_processor.running:
            self.stop_video()
            
        # Load the video
        self.video_path = file_path
        
        # Create a new video processor
        self.video_processor = VideoProcessor(file_path)
        self.video_processor.hw_acceleration_enabled = self.hw_accel_checkbox.isChecked()
        
        # Update info label
        self.info_label.setText(f"{os.path.basename(file_path)} - {self.video_processor.width}x{self.video_processor.height} @ {self.video_processor.frame_rate:.1f}fps")
        
        # Update timeline duration
        if self.video_processor.duration > 0:
            self.timeline.setMaximum(self.video_processor.duration)
            self.duration_label.setText(self.format_time(self.video_processor.duration))
        
        # Load first frame
        self.video_processor.start()
        
        # Wait briefly for the first frame
        start_time = time.time()
        while time.time() - start_time < 1.0:  # Wait up to 1 second
            frame = self.video_processor.frame_buffer.get_latest()
            if frame is not None:
                self.player.set_frame(frame)
                break
            time.sleep(0.1)
        
        # Stop the processor after getting the first frame
        self.video_processor.stop()
        
        # Enable all relevant controls
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.timeline.setEnabled(True)
        self.approve_button.setEnabled(True)
        self.reject_button.setEnabled(True)
        
        # Update approval states
        self.update_approval_states()
    
    def open_video(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Open Video File", "", "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)"
        )
        
        if file_path:
            self.load_video(file_path)
            
    def play_video(self):
        if not self.video_path:
            return
            
        # Initialize the video processor
        self.video_processor = VideoProcessor(self.video_path)
        
        # Set hardware acceleration based on checkbox
        self.video_processor.hw_acceleration_enabled = self.hw_accel_checkbox.isChecked()
        
        # Connect signals for timeline updates
        self.video_processor.position_changed.connect(self.update_timeline)
        self.video_processor.duration_changed.connect(self.update_duration)
        
        # Start the video processor thread
        self.video_processor.start()
        
        # Set up the display timer based on the video frame rate
        # For high frame rates, we need to ensure smooth playback
        interval = max(1, int(1000 / self.video_processor.frame_rate))
        self.display_timer.start(interval)
        
        # Update button states
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # Enable timeline
        self.timeline.setEnabled(True)
        
    def stop_video(self):
        # Stop the display timer
        self.display_timer.stop()
        
        # Stop the video processor
        if self.video_processor and self.video_processor.running:
            self.video_processor.stop()
            
        # Update button states
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
    def update_display(self):
        if self.video_processor and self.video_processor.running:
            frame = self.video_processor.frame_buffer.get_latest()
            if frame is not None:
                self.player.set_frame(frame)
    
    def update_approval_button_states(self):
        if not self.video_path:
            return
            
        status = self.get_video_approval_status()
        if status == "approved":
            self.approve_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px 15px;")
            self.reject_button.setStyleSheet("padding: 5px 15px;")
        elif status == "rejected":
            self.approve_button.setStyleSheet("padding: 5px 15px;")
            self.reject_button.setStyleSheet("background-color: #f44336; color: white; padding: 5px 15px;")
        else:
            self.approve_button.setStyleSheet("padding: 5px 15px;")
            self.reject_button.setStyleSheet("padding: 5px 15px;")

    def get_video_approval_status(self):
        if not self.video_path:
            return None
            
        approval_file = Path(os.path.dirname(self.video_path)) / "approval.json"
        if approval_file.exists():
            try:
                with open(approval_file, 'r') as f:
                    approvals = json.load(f)
                return approvals.get(os.path.basename(self.video_path))
            except json.JSONDecodeError:
                return None
        return None
    
    def save_video_approval_status(self, status):
        if not self.video_path:
            return
            
        approval_file = Path(os.path.dirname(self.video_path)) / "approval.json"
        approvals = {}
        
        # Load existing approvals if file exists
        if approval_file.exists():
            try:
                with open(approval_file, 'r') as f:
                    approvals = json.load(f)
            except json.JSONDecodeError:
                pass
        
        # Update approval status
        approvals[os.path.basename(self.video_path)] = status
        
        # Save to file
        with open(approval_file, 'w') as f:
            json.dump(approvals, f, indent=2)
        
        # Update both button states and video border
        self.update_approval_states()
    
    def approve_video(self):
        self.save_video_approval_status("approved")
    
    def reject_video(self):
        self.save_video_approval_status("rejected")

    def closeEvent(self, event):
        # Ensure clean shutdown
        self.stop_video()
        event.accept()

    def initialize_approval_system(self):
        """Initialize the approval system by ensuring approval.json exists in the current directory"""
        self.approval_file = Path(os.getcwd()) / "approval.json"
        if not self.approval_file.exists():
            try:
                with open(self.approval_file, 'w') as f:
                    json.dump({}, f, indent=2)
                print(f"Created new approval file: {self.approval_file}")
            except Exception as e:
                print(f"Error creating approval file: {e}")

    def update_approval_states(self):
        """Update both button states and video border"""
        if not self.video_path:
            return
            
        status = self.get_video_approval_status()
        # Update button states
        self.update_approval_button_states()
        # Update video border
        self.player.set_approval_status(status)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
