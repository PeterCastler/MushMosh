#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil

def build():
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
        
    # Build the application
    subprocess.run(['pyinstaller', 'anaprev.spec'], check=True)
    
    # Post-build platform-specific tasks
    if sys.platform == 'darwin':
        # Sign the application (if you have a certificate)
        app_path = 'dist/AnaPrev.app'
        if os.path.exists(app_path):
            try:
                subprocess.run(['codesign', '--force', '--deep', '--sign', '-', app_path], check=True)
            except subprocess.CalledProcessError:
                print("Warning: Code signing failed. App may not run properly on macOS.")
    
    print("Build completed successfully!")

if __name__ == '__main__':
    build()