# -*- mode: python ; coding: utf-8 -*-


import os

a = Analysis(
    [os.path.join(SPECPATH, 'bootloader.py')],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pygame', 'keyboard', 'mouse', 'AppOpener', 'psutil', 'pycaw', 'comtypes', 'youtube_search', 'gtts', 'pydub', 'dotenv', 'requests', 'PIL'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['speech_recognition', 'tensorflow', 'tensorflow_io', 'tf_keras', 'keras', 'transformers', 'torch', 'torchvision', 'torchaudio', 'sklearn', 'onnxruntime', 'librosa', 'h5py', 'cv2', 'yt_dlp', 'av', 'soundfile', 'sounddevice', 'numba', 'llvmlite', 'numpy', 'scipy', 'pandas', 'matplotlib', 'IPython', 'jupyter', 'pytest', 'black', 'deepface', 'tensorboard', 'absl', 'PyQt5', 'PyQt5-Qt5', 'PyQt5-sip', 'PySide2', 'PySide6', 'help_manager', 'PyQt6'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Kesha',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(SPECPATH, '..', 'Media', 'Kesha.ico')],
)
