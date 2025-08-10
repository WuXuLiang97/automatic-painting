# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['server_upgrade.py'],
    pathex=['D:\\automatic-painting'],
    binaries=[
        # CUDA 10.2 所需的 DLL
        ('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v10.2/bin/cudart64_102.dll', '.'),
        ('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v10.2/bin/cublas64_10.dll', '.'),
        ('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v10.2/bin/cudnn64_7.dll', '.')
    ],
    datas=[
        # 添加 ultralytics 数据
        ('C:/ProgramData/miniconda3/envs/dnf/Lib/site-packages/ultralytics/*', 'ultralytics'),
        # 添加 OCR 模型
        ('D:/automatic-painting/ch_PP-OCRv4_det_infer/*', 'ch_PP-OCRv4_det_infer'),
        ('D:/automatic-painting/ch_PP-OCRv4_rec_infer/*', 'ch_PP-OCRv4_rec_infer'),
        # 添加 yolo 数据
        ('D:/automatic-painting/yolo/*', 'yolo')
    ],
    hiddenimports=[
        'paddle.inference',
        'paddle.fluid.core_avx',
        'paddle.fluid.libpaddle',
        'cv2',
        'numpy',
        'scipy',
        'ultralytics',
        'paddleocr.tools.infer'
    ],
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

# 关键修改：使用 COLLECT 代替 EXE 以生成文件夹
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='server_upgrade',
)