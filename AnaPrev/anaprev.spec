# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Platform-specific settings
if sys.platform == 'darwin':  # macOS
    add_binary = [
        ('/usr/local/bin/ffmpeg', '.'),
        ('/usr/local/bin/ffprobe', '.')
    ]
    add_data = [
        ('path/to/your/resources', 'resources')  # Add if you have resources
    ]
elif sys.platform == 'win32':  # Windows
    add_binary = [
        ('C:\\path\\to\\ffmpeg.exe', '.'),
        ('C:\\path\\to\\ffprobe.exe', '.')
    ]
    add_data = [
        ('path\\to\\your\\resources', 'resources')  # Add if you have resources
    ]
else:  # Linux
    add_binary = [
        ('/usr/bin/ffmpeg', '.'),
        ('/usr/bin/ffprobe', '.')
    ]
    add_data = [
        ('path/to/your/resources', 'resources')  # Add if you have resources
    ]

a = Analysis(
    ['anaprev.py'],
    pathex=[],
    binaries=add_binary,
    datas=add_data,
    hiddenimports=['PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AnaPrev',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='AnaPrev.app',
        icon=None,  # Add path to your .icns file if you have one
        bundle_identifier='com.yourdomain.anaprev',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
            'NSRequiresAquaSystemAppearance': 'False',
        },
    )
