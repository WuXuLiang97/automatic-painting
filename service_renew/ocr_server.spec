# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app_server.py'],
    pathex=[],
    binaries=[],
    datas=[('PP-OCRv5_mobile_det\\\\det.onnx', 'PP-OCRv5_mobile_det'), ('PP-OCRv5_mobile_rec\\\\rec.onnx', 'PP-OCRv5_mobile_rec'), ('PP-OCRv5_mobile_rec\\\\keys.txt', 'PP-OCRv5_mobile_rec'), ('yolo\\\\model_data\\\\best.onnx', 'yolo\\\\model_data'), ('yolo\\\\model_data\\\\min_map_best.onnx', 'yolo\\\\model_data'), ('工具人.ini', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ocr_server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ocr_server',
)
