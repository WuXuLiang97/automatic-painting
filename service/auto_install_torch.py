# auto_install_torch.py
import subprocess
import sys
import platform
from typing import Optional


def run_command(cmd: str) -> tuple[Optional[str], Optional[str]]:
    """执行系统命令，返回stdout和stderr"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8"
        )
        return result.stdout.strip(), None
    except subprocess.CalledProcessError as e:
        return None, e.stderr.strip()
    except Exception as e:
        return None, str(e)


def check_nvidia_gpu() -> bool:
    """检测是否有NVIDIA GPU"""
    os_type = platform.system()
    if os_type == "Windows":
        # Windows：查询设备管理器中的NVIDIA设备
        stdout, _ = run_command("wmic path win32_VideoController get Name")
        if stdout and "NVIDIA" in stdout:
            return True
    elif os_type in ["Linux", "Darwin"]:
        # Linux/macOS：通过nvidia-smi检测
        stdout, _ = run_command("nvidia-smi")
        if stdout and "NVIDIA-SMI" in stdout:
            return True
    # 若无GPU或检测失败，默认CPU
    return False


def get_cuda_version() -> Optional[str]:
    """查询系统CUDA版本（返回如"12.1"）"""
    # 优先通过nvcc查询（需安装CUDA Toolkit）
    stdout, _ = run_command("nvcc --version")
    if stdout:
        for line in stdout.splitlines():
            if "release" in line and "V" in line:
                # 提取版本号（如"release 12.1, V12.1.105" → "12.1"）
                version_part = line.split("release")[-1].split(",")[0].strip()
                if version_part:
                    return version_part[:4]  # 保留前3位（如12.1、11.8）
    
    # 若nvcc不存在，通过nvidia-smi查询（仅显示驱动支持的最高CUDA版本）
    stdout, _ = run_command("nvidia-smi")
    if stdout:
        for line in stdout.splitlines():
            if "CUDA Version" in line:
                # 提取版本号（如"CUDA Version: 12.2" → "12.2"）
                version_part = line.split(":")[-1].strip()
                if version_part and version_part != "N/A":
                    return version_part[:4]
    
    return None


def install_torch(cuda_version: Optional[str]):
    """根据CUDA版本安装对应PyTorch"""
    # PyTorch官方安装命令映射（覆盖主流CUDA版本）
    torch_commands = {
        "12.4": "pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu124",
        "12.3": "pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu123",
        "12.2": "pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu121",  # 12.2兼容cu121
        "12.1": "pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu121",
        "12.0": "pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu121",  # 12.0兼容cu121
        "11.8": "pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu118",
        "11.7": "pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu118",  # 11.7兼容cu118
        "11.6": "pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu118",  # 11.6兼容cu118
        "default": "pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cpu"  # CPU默认
    }

    if cuda_version and cuda_version in torch_commands:
        cmd = torch_commands[cuda_version]
        print(f"✅ 检测到CUDA {cuda_version}，安装GPU版PyTorch...")
    else:
        cmd = torch_commands["default"]
        print(f"ℹ️ 未检测到兼容CUDA版本（或无GPU），安装CPU版PyTorch...")

    # 执行安装命令
    print(f"执行命令：{cmd}")
    stdout, stderr = run_command(cmd)
    if stderr:
        print(f"❌ 安装失败：{stderr}")
        sys.exit(1)
    print("✅ PyTorch安装完成！")


if __name__ == "__main__":
    print("=" * 50)
    print("🔍 开始检测硬件并自动安装PyTorch...")
    print("=" * 50)

    # 1. 检测是否有NVIDIA GPU
    has_nvidia = check_nvidia_gpu()
    if not has_nvidia:
        print("ℹ️ 未检测到NVIDIA GPU，将安装CPU版PyTorch")
        install_torch(None)
        sys.exit(0)

    # 2. 有GPU，查询CUDA版本
    print("✅ 检测到NVIDIA GPU，查询CUDA版本...")
    cuda_version = get_cuda_version()
    if not cuda_version:
        print("⚠️ 未查询到CUDA版本（可能未安装CUDA Toolkit），将安装CPU版PyTorch")
        install_torch(None)
        sys.exit(0)

    # 3. 安装对应PyTorch
    print(f"✅ 查询到CUDA版本：{cuda_version}")
    install_torch(cuda_version)