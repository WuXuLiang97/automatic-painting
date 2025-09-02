@echo off
chcp 65001  # 解决中文乱码

echo ==============================================
echo 🔧 开始创建dxfend环境并自动安装PyTorch...
echo ==============================================

:: 1. 创建基础环境（从environment.yml）
echo [1/3] 创建基础Conda环境...
conda env create -f environment.yml --force
if %errorlevel% neq 0 (
    echo ❌ 基础环境创建失败！
    pause
    exit /b 1
)

:: 2. 激活环境
echo [2/3] 激活dxfend环境...
call conda activate dxfend
if %errorlevel% neq 0 (
    echo ❌ 环境激活失败！请手动激活后运行auto_install_torch.py
    pause
    exit /b 1
)

:: 3. 运行PyTorch自动安装脚本
echo [3/3] 自动检测GPU并安装PyTorch...
python auto_install_torch.py
if %errorlevel% neq 0 (
    echo ❌ PyTorch安装失败！
    pause
    exit /b 1
)

echo ==============================================
echo ✅ 环境配置完成！已自动适配CPU/GPU
echo 后续使用：conda activate dxfend
echo ==============================================
pause