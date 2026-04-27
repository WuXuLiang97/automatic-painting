import cv2
from pyperclip import copy  # 拷贝到剪切板
import numpy as np
import matplotlib.pyplot as plt

# 设置matplotlib以显示中文
plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定默认字体为SimHei
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
dist = {}


# 判断字符串是否为中文
def is_chinese(string):
    """
    检查整个字符串是否包含中文
    :param string: 需要检查的字符串
    :return: bool
    """
    for ch in string:
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
    return False


def my_imread(path):
    # 读取图片
    if is_chinese(path):
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), -1)  # 避免路径有中文
    else:
        img = cv2.imread(path)
    return img


def hsv_h_min_and_max(path):
    lower_color = []
    upper_color = []
    # 读取图像
    image = my_imread(path)
    print(image.shape)
    # 将图像转换为HSV颜色空间
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # 获取HSV的范围
    h_min, s_min, v_min = hsv_image.min(axis=(0, 1))
    h_max, s_max, v_max = hsv_image.max(axis=(0, 1))
    lower_color.append(h_min)
    lower_color.append(s_min)
    lower_color.append(v_min)
    upper_color.append(h_max)
    upper_color.append(s_max)
    upper_color.append(v_max)
    print(path)
    print("H范围：", h_min, "-", h_max)
    print("S范围：", s_min, "-", s_max)
    print("V范围：", v_min, "-", v_max)
    print((lower_color, upper_color))
    copy(f"{(lower_color, upper_color)}")
    # 计算Hue通道的直方图
    # 注意Hue通道的范围是0-179，所以我们不需要归一化到[0, 1]
    hue_channels = hsv_image[:, :, 0]

    # 定义Hue通道的bin数量
    num_bins = 180
    # 计算Hue通道的直方图
    # 注意Hue通道的范围是0-179
    hue_channels = hsv_image[:, :, 0]
    hue_hist, hue_bin_edges = np.histogram(hue_channels.ravel(), num_bins, [0, 180])

    # 计算Saturation通道的直方图
    # 注意Saturation通道的范围是0-255
    sat_channels = hsv_image[:, :, 1]
    sat_hist, sat_bin_edges = np.histogram(sat_channels.ravel(), num_bins, [0, 256])

    # 计算Value通道的直方图
    # 注意Value通道的范围是0-255
    val_channels = hsv_image[:, :, 2]
    val_hist, val_bin_edges = np.histogram(val_channels.ravel(), num_bins, [0, 256])

    # 绘制Hue通道的直方图
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 3, 1)
    plt.plot(hue_bin_edges[:-1], hue_hist, color='b', label='Hue')
    plt.xlabel('色调区间')
    plt.ylabel('像素数量')
    plt.title('色调直方图')
    plt.legend()
    plt.grid(True)

    # 绘制Saturation通道的直方图
    plt.subplot(1, 3, 2)
    plt.plot(sat_bin_edges[:-1], sat_hist, color='g', label='Saturation')
    plt.xlabel('饱和度区间')
    plt.ylabel('像素数量')
    plt.title('饱和度直方图')
    plt.legend()
    plt.grid(True)

    # 绘制Value通道的直方图
    plt.subplot(1, 3, 3)
    plt.plot(val_bin_edges[:-1], val_hist, color='r', label='Value')
    plt.xlabel('亮度区间')
    plt.ylabel('像素数量')
    plt.title('亮度直方图')
    plt.legend()
    plt.grid(True)

    # 显示所有子图
    plt.tight_layout()
    plt.show()
    return lower_color, upper_color


# for i in range(1,8):
#     path = f"map_depot/shizhong_{i}.png"
#     mane = f"shizhong_{i}.png"
#     list = hsv_h_min_and_max(path)
#     dist.update({mane: list})
# for key, value in dist.items():
#     print(f'{key}: {value}')
# "donghuangtaiyi.png|wenshutianzun.png|yunzhongzi.png|longjigongzhu.png|taiyizhenren.png|shijiniangniang.png"
from core.capture import Capture
from mm import hwnd

img = Capture(hwnd, 0, 0, 1038, 768)
x1, y1, x2, y2 = 0, 0, 1067, 600
min_img = img[y1:y2, x1:x2]
path = r"D:\automatic-painting\utils\ctrl.png"
hsv_range = hsv_h_min_and_max(path)

# 将图像从BGR转换到HSV
hsv_image = cv2.cvtColor(min_img, cv2.COLOR_BGR2HSV)

# 定义HSV颜色范围
# lower_color = np.array(hsv_range[0])
hsv_range = ([80, 0, 0], [99, 145, 238])
lower_color = np.array([hsv_range[0]])
upper_color = np.array(hsv_range[1])

# 创建一个掩码来只选择落在指定颜色范围内的像素
mask = cv2.inRange(hsv_image, lower_color, upper_color)

# 使用掩码从原始BGR图像中提取颜色范围内的像素
color_filtered_image = cv2.bitwise_and(min_img, min_img, mask=mask)

cv2.imshow('img', color_filtered_image)
cv2.waitKey(0)
cv2.destroyAllWindows()
# import pyttsx3
#
#
# def speak(text, rate=150):  # 你可以设置默认的语速，或者作为函数参数传入
#     engine = pyttsx3.init()
#     engine.setProperty('rate', rate)  # 设置语速
#     engine.say(text)
#     engine.runAndWait()
#
#
# speak('老君来啦')
# speak('掉线啦')
