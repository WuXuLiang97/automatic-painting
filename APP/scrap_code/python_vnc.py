import vncdotool.api as api
import io
from PIL import Image
import time


def capture_vnc_screen(host, port, password=None, save_path=None):
    """
    通过 VNC 获取屏幕截图并在内存中处理

    参数:
        host: VNC 服务器主机名或 IP
        port: VNC 服务器端口
        password: VNC 密码 (如果需要)
        save_path: 可选，截图保存路径

    返回:
        PIL 图像对象，如果失败则返回 None
    """
    try:
        # 连接到 VNC 服务器
        factory = api.connect(host, port)
        client = factory.protocol

        # 如果需要密码，进行认证
        if password:
            # 这里假设密码输入逻辑与之前相同
            # 实际使用时可能需要根据 VNC 服务器的认证方式调整
            time.sleep(1)
            client.keyPress('Tab')
            time.sleep(0.5)
            client.keyPress('Tab')
            time.sleep(0.5)
            client.keyPress('Tab')
            time.sleep(0.5)
            client.keyPress('Tab')
            time.sleep(0.5)

            for char in password:
                client.keyPress(char)
            client.keyPress('Return')

            # 等待认证完成
            time.sleep(2)

        # 创建内存缓冲区
        buffer = io.BytesIO()

        # 捕获屏幕并保存到内存缓冲区
        client.captureScreen(buffer)

        # 将缓冲区位置重置到开始
        buffer.seek(0)

        # 从缓冲区读取图像
        image = Image.open(buffer)

        # 如果需要保存到文件
        if save_path:
            image.save(save_path)
            print(f"截图已保存到 {save_path}")

        # 关闭连接
        client.disconnect()

        return image

    except Exception as e:
        print(f"截图失败: {e}")
        # 确保断开连接
        try:
            if 'client' in locals():
                client.disconnect()
        except:
            pass
        return None


# 使用示例
if __name__ == "__main__":
    # 配置 VNC 连接信息
    VNC_HOST = "localhost"
    VNC_PORT = 5900
    VNC_PASSWORD = ""  # 替换为实际密码

    # 获取截图
    screenshot = capture_vnc_screen(VNC_HOST, VNC_PORT, VNC_PASSWORD, "screenshot.png")

    if screenshot:
        print(f"截图尺寸: {screenshot.size}")
        # 这里可以对 screenshot 进行进一步处理
        # 例如: 裁剪、调整大小、分析像素等
