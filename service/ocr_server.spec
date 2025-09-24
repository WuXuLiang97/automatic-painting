# -*- mode: python ; coding: utf-8 -*-

# 精简版：已开始排除未使用的大型包。
# 注意：不要使用 optimize=2 (-OO) 因为会剥离 docstring，导致 numpy C 扩展 add_docstring(None) 报错。

block_cipher = None

a = Analysis(
    ['app_server.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('PP-OCRv5_mobile_det\\det.onnx', 'PP-OCRv5_mobile_det'),
        ('PP-OCRv5_mobile_rec\\rec.onnx', 'PP-OCRv5_mobile_rec'),
        ('PP-OCRv5_mobile_rec\\keys.txt', 'PP-OCRv5_mobile_rec'),
        ('yolo\\model_data\\best.onnx', 'yolo\\model_data'),
        ('yolo\\model_data\\min_map_best.onnx', 'yolo\\model_data'),  # 若不用可删
        ('工具人.ini', '.'),  # 若希望外置配置可删
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 深度学习框架
        'paddle', 'paddleocr', 'torch', 'torchvision', 'torchaudio', 'tensorflow', 'tf_keras', 'keras', 'h5py',
        # 科学计算/数据分析（未使用）
        'scipy', 'pandas', 'sklearn', 'sympy', 'numba',
        # 可视化 / 图像增强
        'matplotlib', 'seaborn', 'PIL', 'Pillow', 'albumentations',
        # 交互 / 笔记本 / 测试
        'notebook', 'jupyter', 'ipykernel', 'IPython', 'pytest',
        # 其他常见未用包
        'tqdm', 'Cython', 'mmcv', 'mmdet', 'onnxconverter_common'
    ],
    noarchive=False,
    optimize=0,  # 不能用 2 (-OO)，否则剥离 docstring 引发 numpy add_docstring 报错
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ocr_server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,       # 去除符号表，减小体积（若排查崩溃可改 False）
    upx=False,        # 稳定优先；确认正常后可改 True（需安装 upx）
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
    strip=True,
    upx=False,
    upx_exclude=[],
    name='ocr_server',
)

# 如需进一步缩小，可稍后再尝试 upx=True；保持 optimize=0/1 即可，避免 2。
