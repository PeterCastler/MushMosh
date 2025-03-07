#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import platform
import argparse
import time

def build(target_platform=None, debug=False):
    """
    Build the application for the specified platform or current platform if not specified.
    
    Args:
        target_platform: Optional platform to build for ('windows', 'macos', or None for current platform)
        debug: If True, builds with console window for debugging
    """
    current_platform = sys.platform
    build_platform = target_platform or current_platform
    
    print(f"Building AnaPrev for platform: {build_platform}")
    
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    main_script = 'anaprev.py'
    if not os.path.exists(main_script):
        print(f"Error: Main script '{main_script}' not found!")
        return False
    
    spec_file = 'anaprev.spec'
    
    try:
        if os.path.exists(spec_file):
            print(f"Using existing spec file: {spec_file}")
            subprocess.run(['pyinstaller', spec_file], check=True)
        else:
            # Build command with debug options
            build_cmd = [
                'pyinstaller',
                '--name=AnaPrev',
                '--onefile',
                '--clean',
            ]
            
            # Add debug options
            if debug:
                build_cmd.extend([
                    '--debug=all',  # Enable all debug options
                    '--console',    # Show console window for output
                ])
            else:
                build_cmd.append('--windowed')  # No console in production
            
            # Add platform-specific options
            if current_platform == 'darwin':
                build_cmd.extend([
                    '--target-arch=universal2',  # Build for both Intel and Apple Silicon
                    '--osx-bundle-identifier=com.yourdomain.anaprev',
                ])
            
            # Add the main script
            build_cmd.append(main_script)
            
            print(f"Building with command: {' '.join(build_cmd)}")
            subprocess.run(build_cmd, check=True)
        
        print("PyInstaller build completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error during PyInstaller build: {e}")
        return False
    
    # Post-build platform-specific tasks
    if current_platform == 'darwin':
        app_path = 'dist/AnaPrev.app'
        if os.path.exists(app_path):
            try:
                # Create logs directory inside the app bundle
                logs_dir = os.path.join(app_path, 'Contents/Resources/logs')
                os.makedirs(logs_dir, exist_ok=True)
                
                # Add logging wrapper script
                wrapper_script = os.path.join(app_path, 'Contents/MacOS/launch_wrapper.sh')
                with open(wrapper_script, 'w') as f:
                    f.write('''#!/bin/bash
exec 2>> "$HOME/Library/Logs/AnaPrev/error.log"
exec "$0.original" "$@"
''')
                
                # Make wrapper executable and rename original executable
                os.chmod(wrapper_script, 0o755)
                os.rename(
                    os.path.join(app_path, 'Contents/MacOS/AnaPrev'),
                    os.path.join(app_path, 'Contents/MacOS/AnaPrev.original')
                )
                os.rename(wrapper_script, os.path.join(app_path, 'Contents/MacOS/AnaPrev'))
                
                # Sign the application
                subprocess.run(['codesign', '--force', '--deep', '--sign', '-', app_path], check=True)
                print("macOS code signing completed")
            except subprocess.CalledProcessError:
                print("Warning: Code signing failed. App may not run properly on macOS.")
            except Exception as e:
                print(f"Error during post-processing: {e}")
                return False
    
    elif current_platform == 'win32':
        exe_path = 'dist/AnaPrev.exe'
        if os.path.exists(exe_path):
            print(f"Windows executable created at: {exe_path}")
    
    # Check if build was successful
    if current_platform == 'darwin' and os.path.exists('dist/AnaPrev.app'):
        print("Build completed successfully! Application is at dist/AnaPrev.app")
        print("Logs will be written to ~/Library/Logs/AnaPrev/error.log")
        return True
    elif current_platform == 'win32' and os.path.exists('dist/AnaPrev.exe'):
        print("Build completed successfully! Application is at dist/AnaPrev.exe")
        return True
    else:
        print("Build may have failed. Check the output directory.")
        return False

def main():
    parser = argparse.ArgumentParser(description='Build AnaPrev application')
    parser.add_argument('--platform', choices=['windows', 'macos'], 
                      help='Target platform (windows or macos). Defaults to current platform.')
    parser.add_argument('--clean-spec', action='store_true',
                      help='Regenerate the spec file before building')
    parser.add_argument('--debug', action='store_true',
                      help='Build with debug options and console window')
    
    args = parser.parse_args()
    
    platform_map = {
        'windows': 'win32',
        'macos': 'darwin'
    }
    
    target_platform = platform_map.get(args.platform) if args.platform else None
    
    if target_platform and target_platform != sys.platform:
        print(f"Warning: Cross-compiling from {sys.platform} to {target_platform} may not work correctly.")
        print("PyInstaller generally requires building on the target platform.")
    
    if args.clean_spec and os.path.exists('anaprev.spec'):
        print("Removing existing spec file as requested...")
        os.remove('anaprev.spec')
    
    # Create logs directory before building
    if sys.platform == 'darwin':
        log_dir = os.path.expanduser('~/Library/Logs/AnaPrev')
        os.makedirs(log_dir, exist_ok=True)
    
    start_time = time.time()
    success = build(target_platform, args.debug)
    end_time = time.time()
    
    if success:
        print(f"Build completed in {end_time - start_time:.2f} seconds")
        if args.debug:
            if sys.platform == 'darwin':
                print("\nTo view debug logs after running the app:")
                print("cat ~/Library/Logs/AnaPrev/error.log")
            else:
                print("\nDebug output will be shown in the console window when running the app")
    else:
        print("Build failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
