import cv2
import numpy as np
import matplotlib.pyplot as plt
from pyperclip import copy
from typing import Tuple, List, Optional

# 配置matplotlib中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'WenQuanYi Micro Hei', 'Heiti TC']
plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号


class HSVAnalyzer:
    """HSV颜色范围分析工具，用于提取图像的HSV范围并可视化"""

    def __init__(self, delta_h: int = 2,delta: int = 5):
        """
        初始化分析器
        :param delta: 颜色范围的缓冲值，用于扩大检测范围
        """
        self.delta_h = delta_h
        self.delta = delta
        # HSV各通道的最大值限制
        self.hsv_max_limits = {
            'H': 179,
            'S': 255,
            'V': 255
        }

    @staticmethod
    def is_chinese(string: str) -> bool:
        """检查字符串是否包含中文字符"""
        return any('\u4e00' <= ch <= '\u9fff' for ch in string)

    def read_image(self, path: str) -> Optional[np.ndarray]:
        """
        读取图像，支持中文路径
        :param path: 图像路径
        :return: 读取的BGR图像，失败返回None
        """
        try:
            if self.is_chinese(path):
                # 处理中文路径
                return cv2.imdecode(
                    np.fromfile(path, dtype=np.uint8),
                    cv2.IMREAD_COLOR
                )
            else:
                return cv2.imread(path, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"读取图像失败: {e}")
            return None

    def get_channel_min(self, channel: np.ndarray) -> int:
        """
        计算单个通道的最小值（排除0值）
        :param channel: HSV单通道数据
        :return: 处理后的最小值
        """
        non_zero = channel[channel != 0]
        if len(non_zero) == 0:
            return 0

        min_val = non_zero.min()
        # 减去缓冲值，确保不小于0
        return max(min_val - self.delta, 0)
    def get_channel_min_h(self, channel: np.ndarray) -> int:
        """
        计算单个通道的最小值（排除0值）
        :param channel: HSV单通道数据
        :return: 处理后的最小值
        """
        non_zero = channel[channel != 0]
        if len(non_zero) == 0:
            return 0

        min_val = non_zero.min()
        # 减去缓冲值，确保不小于0
        return max(min_val - self.delta_h, 0)

    def get_channel_max(self, channel: np.ndarray, channel_name: str) -> int:
        """
        计算单个通道的最大值
        :param channel: HSV单通道数据
        :param channel_name: 通道名称（H/S/V）
        :return: 处理后的最大值
        """
        max_val = channel.max()
        # 加上缓冲值，不超过通道最大值限制
        return min(max_val + self.delta, self.hsv_max_limits[channel_name])

    def get_channel_max_h(self, channel: np.ndarray, channel_name: str) -> int:
        """
        计算单个通道的最大值
        :param channel: HSV单通道数据
        :param channel_name: 通道名称（H/S/V）
        :return: 处理后的最大值
        """
        max_val = channel.max()
        # 加上缓冲值，不超过通道最大值限制
        return min(max_val + self.delta_h, self.hsv_max_limits[channel_name])

    def calculate_hsv_range(self, hsv_image: np.ndarray) -> Tuple[List[int], List[int]]:
        """
        计算HSV图像的颜色范围
        :param hsv_image: HSV格式的图像
        :return: (lower_bound, upper_bound) 颜色范围
        """
        # 分离三个通道
        h_channel = hsv_image[:, :, 0]
        s_channel = hsv_image[:, :, 1]
        v_channel = hsv_image[:, :, 2]

        # 计算最小值
        h_min = self.get_channel_min_h(h_channel)
        s_min = self.get_channel_min(s_channel)
        v_min = self.get_channel_min(v_channel)

        # 计算最大值
        h_max = self.get_channel_max_h(h_channel, 'H')
        s_max = self.get_channel_max(s_channel, 'S')
        v_max = self.get_channel_max(v_channel, 'V')

        return [h_min, s_min, v_min], [h_max, s_max, v_max]

    def plot_histograms(self, hsv_image: np.ndarray) -> None:
        """
        绘制HSV三个通道的直方图
        :param hsv_image: HSV格式的图像
        """
        num_bins = 180
        channels = {
            'H': (hsv_image[:, :, 0], [0, 180], 'b', '色调区间', '色调直方图'),
            'S': (hsv_image[:, :, 1], [0, 256], 'g', '饱和度区间', '饱和度直方图'),
            'V': (hsv_image[:, :, 2], [0, 256], 'r', '亮度区间', '亮度直方图')
        }

        plt.figure(figsize=(15, 5))

        for i, (name, (channel, range_, color, xlabel, title)) in enumerate(channels.items(), 1):
            plt.subplot(1, 3, i)
            hist, bin_edges = np.histogram(channel.ravel(), num_bins, range_)
            plt.plot(bin_edges[:-1], hist, color=color, label=name)
            plt.xlabel(xlabel)
            plt.ylabel('像素数量')
            plt.title(title)
            plt.legend()
            plt.grid(alpha=0.3)

        plt.tight_layout()
        plt.show()

    def analyze_image(self, path: str) -> Optional[Tuple[List[int], List[int]]]:
        """
        完整分析流程：读取图像 -> 转换HSV -> 计算范围 -> 可视化 -> 复制结果
        :param path: 图像路径
        :return: HSV颜色范围，失败返回None
        """
        # 读取图像
        bgr_image = self.read_image(path)
        if bgr_image is None or bgr_image.size == 0:
            print("无法处理空图像")
            return None

        print(f"图像尺寸: {bgr_image.shape}")

        # 转换为HSV
        hsv_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)

        # 计算HSV范围
        lower, upper = self.calculate_hsv_range(hsv_image)

        # 输出结果
        print(f"\n分析图像: {path}")
        print(f"H范围：{lower[0]} - {upper[0]}")
        print(f"S范围：{lower[1]} - {upper[1]}")
        print(f"V范围：{lower[2]} - {upper[2]}")
        print(f"HSV范围: {lower}, {upper}")

        # 复制到剪贴板
        copy(f"({lower}, {upper})")
        print("范围已复制到剪贴板")

        # 绘制直方图
        self.plot_histograms(hsv_image)

        return lower, upper


def filter_image_by_hsv(image: np.ndarray, hsv_range: Tuple[List[int], List[int]]) -> np.ndarray:
    """
    根据HSV范围过滤图像
    :param image: BGR格式图像
    :param hsv_range: (lower, upper) HSV范围
    :return: 过滤后的图像
    """
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower = np.array(hsv_range[0], dtype=np.uint8)
    upper = np.array(hsv_range[1], dtype=np.uint8)

    mask = cv2.inRange(hsv_image, lower, upper)
    return cv2.bitwise_and(image, image, mask=mask)




# 示例用法
if __name__ == "__main__":
    # 初始化分析器，可调整缓冲值
    analyzer = HSVAnalyzer(delta=10)

    # 分析单张图像
    image_path = r"C:\Users\Administrator\Downloads\automatic-painting\APP\map_depot\再次挑战.bmp"
    hsv_range = analyzer.analyze_image(image_path)


    # 如果需要处理截图并过滤（示例）
    if hsv_range:
        hsv_range = hsv_range
        try:
            # 这里保留原代码中的截图逻辑（根据实际情况调整）
            from capture import Capture

            # 捕获屏幕区域
            capture = Capture(196966, 0, 0, 1038, 768)
            x1, y1, x2, y2 = 0, 0, 1067, 600
            captured_img = capture[y1:y2, x1:x2]  # 假设capture对象支持切片

            # 应用过滤
            filtered_img = filter_image_by_hsv(captured_img, hsv_range)

            # 显示结果
            cv2.imshow('过滤结果', filtered_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        except Exception as e:
            print(f"处理截图时出错: {e}")

    # # 批量处理示例（注释掉的原代码逻辑）
    # dist = {}
    # for i in range(1, 8):
    #     path = f"map_depot/shizhong_{i}.png"
    #     name = f"shizhong_{i}.png"
    #     result = analyzer.analyze_image(path)
    #     if result:
    #         dist[name] = result
    #
    # for key, value in dist.items():
    #     print(f'{key}: {value}')
