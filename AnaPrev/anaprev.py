#!/usr/bin/env python3
import sys
import os

def validate_imports():
    required_imports = {
        'PyQt5.QtWidgets': [
            'QApplication',
            'QWidget',
            'QMainWindow',
            'QVBoxLayout',
            'QHBoxLayout',
            'QPushButton',
            'QGraphicsBlurEffect',
            'QGraphicsScene',
            'QGraphicsPixmapItem',
            'QSlider',
            'QLabel',
            'QCheckBox',
            'QFileDialog'  # Added for file opening dialog
        ],
        'PyQt5.QtGui': [
            'QImage',
            'QPixmap',
            'QPainter',
            'QFont',
            'QPen'  # Added for drawing
        ],
        'PyQt5.QtCore': [
            'Qt',
            'QTimer',
            'QThread',
            'pyqtSignal',
            'QMutex',
            'QRect',
            'QUrl'  # Added for drag and drop functionality
        ],
        'other': [
            ('numpy', 'np'),
            ('psutil', 'psutil'),
            ('ffmpeg', 'ffmpeg')
        ]
    }

    missing = []
    
    # Check PyQt5 imports
    for module, classes in required_imports.items():
        if module != 'other':
            try:
                imported_module = __import__(module, fromlist=classes)
                for class_name in classes:
                    if not hasattr(imported_module, class_name):
                        missing.append(f"{module}.{class_name}")
            except ImportError as e:
                missing.extend([f"{module}.{class_name}" for class_name in classes])

    # Check other imports
    for package, alias in required_imports['other']:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print("Error: Missing required imports:")
        for m in missing:
            print(f"  - {m}")
        print("\nPlease install required packages:")
        print("pip install PyQt5 numpy psutil ffmpeg-python")
        sys.exit(1)

    return True

# Validate imports before proceeding
validate_imports()

# If validation passes, do regular imports
import subprocess
import time
import re
import threading
import json
from pathlib import Path
from datetime import datetime
import logging
import numpy as np

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QGraphicsBlurEffect,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QSlider,
    QLabel,
    QCheckBox,
    QFileDialog
)
from PyQt5.QtGui import (
    QImage, 
    QPixmap, 
    QPainter, 
    QFont,
    QPen
)
from PyQt5.QtCore import (
    Qt, 
    QTimer, 
    QThread, 
    pyqtSignal, 
    QMutex, 
    QRect,
    QUrl
)

import psutil
import ffmpeg

def setup_logger():
    """Configure logging with detailed formatting and both file/console output"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.expanduser('~/Library/Logs/AnaPrev') if sys.platform == 'darwin' else 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a timestamp-based log filename
    log_file = os.path.join(log_dir, f'anaprev_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    # Configure root logger
    logger = logging.getLogger('AnaPrev')
    logger.setLevel(logging.DEBUG)
    
    # Add import debugging
    logger.debug("Importing PyQt5 modules...")
    try:
        from PyQt5.QtGui import QImage, QPixmap, QPainter, QFont
        logger.debug("Successfully imported QtGui components")
    except ImportError as e:
        logger.error(f"Failed to import QtGui components: {e}")
        raise
        
    try:
        from PyQt5.QtWidgets import (QWidget, QMainWindow, QVBoxLayout, 
                                   QHBoxLayout, QPushButton, QGraphicsBlurEffect, 
                                   QGraphicsScene, QGraphicsPixmapItem)
        logger.debug("Successfully imported QtWidgets components")
    except ImportError as e:
        logger.error(f"Failed to import QtWidgets components: {e}")
        raise
    
    # Detailed formatter
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with full debug output
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console handler with info level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add both handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info("Logging system initialized")
    logger.debug(f"Log file created at: {log_file}")
    
    return logger

class FrameBuffer:
    def __init__(self, max_size=None):
        self.buffer = []
        self.max_size = max_size  # Set to None for unlimited size
        self.mutex = QMutex()
        
    def push(self, frame):
        if not self.mutex.tryLock(1000):  # 1 second timeout
            print("WARNING: Failed to acquire mutex for push operation")
            return False
        try:
            if self.max_size and len(self.buffer) >= self.max_size:
                self.buffer.pop(0)  # Remove oldest frame if at capacity
            self.buffer.append(frame)
            print(f"Buffer size: {len(self.buffer)}")  # Monitor buffer growth
            return True
        finally:
            self.mutex.unlock()
        
    def get_latest(self):
        if not self.mutex.tryLock(1000):  # 1 second timeout
            print("WARNING: Failed to acquire mutex for get_latest operation")
            return None
        try:
            if not self.buffer:
                return None
            return self.buffer[-1]
        finally:
            self.mutex.unlock()
        
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
        self.logger = logging.getLogger('AnaPrev.VideoProcessor')
        self.video_path = video_path
        self.logger.info(f"Initializing VideoProcessor for: {video_path}")
        
        # Initialize running state
        self.running = True
        
        # Log system info
        self.logger.debug(f"Available RAM: {psutil.virtual_memory().available / (1024**3):.2f}GB")
        self.logger.debug(f"CPU cores: {psutil.cpu_count()}")
        
        try:
            # Get video information using ffprobe
            self.logger.debug("Retrieving video information...")
            probe = ffmpeg.probe(video_path)
            print(f"Video info: {probe['streams'][0]}")  # Let's see what we're dealing with
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            
            self.width = int(video_info['width'])
            self.height = int(video_info['height'])
            self.frame_rate = float(eval(video_info['r_frame_rate']))
            self.duration = float(video_info['duration']) * 1000  # ms
            
            self.logger.info(f"Video specs: {self.width}x{self.height} @ {self.frame_rate}fps, "
                           f"duration: {self.duration/1000:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error getting video information: {e}", exc_info=True)
            # Set fallback values
            self.width = 640
            self.height = 480
            self.frame_rate = 30.0
            self.duration = 60000
            
        # Create frame buffer with no size limit
        self.frame_buffer = FrameBuffer(max_size=None)
        self.preload_complete = False
        self.frames_loaded = 0
        self.total_frames = int(self.frame_rate * (self.duration / 1000))
        
        self.logger.debug(f"Estimated total frames: {self.total_frames}")
        self.logger.debug(f"Estimated memory per frame: "
                         f"{(self.width * self.height * 3) / (1024*1024):.2f}MB")
        self.logger.debug(f"Estimated total memory needed: "
                         f"{(self.width * self.height * 3 * self.total_frames) / (1024*1024*1024):.2f}GB")
        
        # Add flag for preloading
        self.preload_complete = False
        
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
    
    def preload_video(self):
        """Preload entire video into memory"""
        print(f"Starting video preload: {self.video_path}")
        print(f"Video specs: {self.width}x{self.height} @ {self.frame_rate}fps")
        print(f"Initial memory usage: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB")
        
        cmd = [
            'ffmpeg',
            '-i', self.video_path,
            # Removed the -t 5 limitation
            '-f', 'image2pipe',
            '-pix_fmt', 'rgb24',
            '-vcodec', 'rawvideo',
            '-'
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=10**8
        )
        
        try:
            frame_size = self.width * self.height * 3
            frames_loaded = 0
            expected_frames = int(self.frame_rate * (self.duration / 1000))
            
            while True:
                if frames_loaded % 30 == 0:  # Update every 30 frames (quarter second at 120fps)
                    print(f"Loaded {frames_loaded}/{expected_frames} frames "
                          f"({(frames_loaded/expected_frames)*100:.1f}%)")
                    print(f"Current memory usage: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB")
                
                raw_frame = process.stdout.read(frame_size)
                if not raw_frame:
                    stderr_output = process.stderr.read()
                    if stderr_output:
                        print(f"FFmpeg stderr: {stderr_output.decode('utf-8')}")
                    break
                
                frame = np.frombuffer(raw_frame, np.uint8).reshape(
                    (self.height, self.width, 3)
                )
                
                if not self.frame_buffer.push(frame.copy()):
                    print("Failed to push frame to buffer - stopping preload")
                    break
                    
                frames_loaded += 1
            
        except Exception as e:
            print(f"Error during preload: {e}")
            traceback.print_exc()
        finally:
            process.terminate()
            print(f"Preload ended after {frames_loaded} frames")
            print(f"Final memory usage: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB")
    
    def run(self):
        if not self.preload_complete:
            self.preload_video()
        
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
        self.blurred_preview = None
        self.is_loading = False
        self.setMinimumSize(320, 180)
        self.aspect_ratio = 2.39  # Standard anamorphic aspect ratio
        self.pixel_aspect_ratio = 2.0  # Default PAR for anamorphic content
        self.logger = logging.getLogger('AnaPrev.VideoPlayerWidget')
        
        # Add border styling
        self.setStyleSheet("border: none;")  # Default state
        
    def set_frame(self, frame):
        height, width = frame.shape[:2]
        # Apply PAR correction for anamorphic content
        self.aspect_ratio = (width * self.pixel_aspect_ratio) / height
        bytes_per_line = 3 * width
        self.image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        self.is_loading = False
        self.update()
        
    def set_loading_preview(self, frame):
        """Set a blurred preview frame during loading"""
        try:
            # Convert numpy array to QImage
            height, width = frame.shape[:2]
            bytes_per_line = 3 * width
            q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).copy()  # Make a deep copy
            
            # Create pixmap and apply blur effect
            pixmap = QPixmap.fromImage(q_img)
            
            # Create a new QGraphicsScene and QGraphicsPixmapItem
            scene = QGraphicsScene()
            item = QGraphicsPixmapItem()
            item.setPixmap(pixmap)
            
            # Apply blur effect
            blur = QGraphicsBlurEffect()
            blur.setBlurRadius(15)  # Reduced blur radius for better performance
            item.setGraphicsEffect(blur)
            scene.addItem(item)
            
            # Create result image
            result = QImage(pixmap.size(), QImage.Format_RGB888)
            painter = QPainter(result)
            scene.render(painter)
            painter.end()
            
            self.blurred_preview = result
            self.is_loading = True
            self.update()
            
        except Exception as e:
            print(f"Error creating blurred preview: {e}")

    def paintEvent(self, event):
        if not self.image and not self.blurred_preview:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Get widget dimensions
        widget_width = self.width()
        widget_height = self.height()
        
        if self.is_loading and self.blurred_preview:
            # Display blurred preview during loading
            image_to_draw = self.blurred_preview
            # Add loading text overlay
            painter.setFont(QFont('Arial', 14))
            painter.setPen(Qt.white)
            painter.drawText(self.rect(), Qt.AlignCenter, "Loading video...")
        else:
            # Display normal frame
            image_to_draw = self.image
            
        if image_to_draw:
            # Calculate aspect ratio preserving dimensions
            if widget_width / widget_height > self.aspect_ratio:
                target_width = int(widget_height * self.aspect_ratio)
                target_height = widget_height
            else:
                target_width = widget_width
                target_height = int(target_width / self.aspect_ratio)
            
            # Calculate position to center the image
            x = (widget_width - target_width) // 2
            y = (widget_height - target_height) // 2
            
            # Draw the image with proper aspect ratio
            target_rect = QRect(x, y, target_width, target_height)
            painter.drawImage(target_rect, image_to_draw)
        
    def set_approval_status(self, status):
        if status == "approved":
            self.setStyleSheet("border: 1px solid #4CAF50;")  # Green border
        elif status == "rejected":
            self.setStyleSheet("border: 1px solid #f44336;")  # Red border
        else:
            self.setStyleSheet("border: none;")  # No border


class MainWindow(QMainWindow):
    # Class-level signal declaration
    update_ui_after_preload = pyqtSignal()

    def __init__(self):
        super().__init__()
        # Initialize logger
        self.logger = logging.getLogger('AnaPrev.MainWindow')
        
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
        
        # Connect the signal to the slot
        self.update_ui_after_preload.connect(self._update_ui_after_preload)

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
        try:
            print("Drop event started")  # Basic console output
            if event.mimeData().hasUrls():
                url = event.mimeData().urls()[0]
                file_path = url.toLocalFile()
                print(f"Processing file: {file_path}")  # Basic console output
                
                video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']
                if any(file_path.lower().endswith(ext) for ext in video_extensions):
                    self.load_video(file_path)
        except Exception as e:
            print(f"Crash in drop event: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def load_video(self, file_path):
        print("1. Entering load_video")
        
        # Stop any current playback
        if self.video_processor and self.video_processor.running:
            print("2. Stopping current video")
            self.stop_video()
        
        print("3. Creating new video processor")
        # Create a new video processor
        self.video_processor = VideoProcessor(file_path)
        
        # Get and display blurred preview frame first
        self.display_blurred_preview(file_path)
        
        # Start preloading in a separate thread to not block the UI
        preload_thread = threading.Thread(target=self.start_preloading)
        preload_thread.daemon = True
        preload_thread.start()

    def display_blurred_preview(self, file_path):
        try:
            cmd = [
                'ffmpeg',
                '-i', file_path,
                '-vframes', '1',  # Get only first frame
                '-f', 'image2pipe',
                '-pix_fmt', 'rgb24',
                '-vcodec', 'rawvideo',
                '-'
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )
            
            frame_size = self.video_processor.width * self.video_processor.height * 3
            raw_frame = process.stdout.read(frame_size)
            
            if raw_frame:
                frame = np.frombuffer(raw_frame, np.uint8).reshape(
                    (self.video_processor.height, self.video_processor.width, 3)
                )
                self.player.set_loading_preview(frame)
                
        except Exception as e:
            print(f"Error creating preview: {e}")
            traceback.print_exc()
        finally:
            if process:
                process.terminate()

    def start_preloading(self):
        print("Starting full video preload")
        
        # Start loading the full video
        self.video_processor.preload_video()
        
        # Update UI elements after preload is complete
        # Using Qt's signal system to safely update UI from another thread
        self.update_ui_after_preload.emit()

    def _update_ui_after_preload(self):
        # Update info label with video details
        self.info_label.setText(
            f"{os.path.basename(self.video_processor.video_path)} - "
            f"{self.video_processor.width}x{self.video_processor.height} "
            f"@ {self.video_processor.frame_rate:.1f}fps (Fully loaded in RAM)"
        )
        
        # Update timeline duration
        if self.video_processor.duration > 0:
            self.timeline.setMaximum(self.video_processor.duration)
            self.duration_label.setText(self.format_time(self.video_processor.duration))
        
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
