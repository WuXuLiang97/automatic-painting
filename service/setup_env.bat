@echo off
chcp 65001  # 解决中文乱码

echo ==============================================
echo 🔧 开始创建dxfend环境并自动安装PyTorch + ONNX工具...
echo ==============================================

:: 1. 创建基础环境（从service.yml）
echo [1/4] 创建基础Conda环境...
conda env create -f service.yml --force
if %errorlevel% neq 0 (
    echo ❌ 基础环境创建失败！
    pause
    exit /b 1
)

:: 2. 激活环境
echo [2/4] 激活dxfend环境...
call conda activate dxfend
if %errorlevel% neq 0 (
    echo ❌ 环境激活失败！请手动激活后运行auto_install_torch.py
    pause
    exit /b 1
)

:: 3. 运行PyTorch自动安装脚本（检测GPU/CPU）
echo [3/4] 自动检测GPU并安装PyTorch...
python auto_install_torch.py
if %errorlevel% neq 0 (
    echo ❌ PyTorch安装失败！
    pause
    exit /b 1
)

:: 4. 自动安装ONNX相关工具（根据设备类型）
echo [4/4] 检测设备并安装适配的ONNX工具...
python -c "import torch; print('GPU' if torch.cuda.is_available() else 'CPU')" > device_type.txt
set /p DEVICE_TYPE=<device_type.txt
del device_type.txt

if "%DEVICE_TYPE%"=="GPU" (
    echo 📌 检测到GPU，安装带CUDA加速的ONNX工具...
    pip install onnxruntime-gpu==1.17.0 onnx==1.15.0 onnx-simplifier==0.4.35
) else (
    echo 📌 仅检测到CPU，安装CPU优化的ONNX工具...
    pip install onnxruntime==1.17.0 onnx==1.15.0 onnx-simplifier==0.4.35
    
    :: 额外安装Intel CPU优化工具（可选，提升Intel CPU性能）
    python -c "import platform; print('Intel' in platform.processor())" > is_intel.txt
    set /p IS_INTEL=<is_intel.txt
    del is_intel.txt
    if "%IS_INTEL%"=="True" (
        echo 📌 检测到Intel CPU，额外安装OpenVINO加速工具...
        pip install openvino==2023.2 openvino-dev==2023.2
    )
)

:: 验证ONNX安装
echo 📋 验证ONNX工具安装...
python -c "import onnxruntime; print('ONNX Runtime版本:', onnxruntime.__version__)" > onnx_check.txt 2>&1
if %errorlevel% equ 0 (
    type onnx_check.txt
    echo ✅ ONNX工具安装成功！
) else (
    echo ❌ ONNX工具安装失败！
    type onnx_check.txt
    pause
    exit /b 1
)
del onnx_check.txt

echo ==============================================
echo ✅ 环境配置完成！已自动适配CPU/GPU并安装ONNX工具
echo 后续使用：conda activate dxfend
echo ==============================================
pause