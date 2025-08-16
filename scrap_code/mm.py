# -*- coding: utf-8 -*-
import datetime
import math
import os
import os.path
import queue
import random
import sys
import threading
import time
import timeit
import traceback
from pathlib import Path
from time import sleep

import cv2
import numpy as np
import win32gui
from core.capture import Capture
from root_dir import root_path
from logging_setup import logger

STOP_EVENT = threading.Event()

# 盾术默认f1
fi = 'f1'
# 窗口场次计数
window_1_count = 0

# 创建一个全局变量用来判断启动线程没有
called = False
# 创建一个队列用于存储图片数据
image_queue = queue.Queue()

verbose = False


# def logger.info(*args, **kwargs):
#     if verbose:
#         current_time = datetime.datetime.now()
#         formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
#         logger.info(f"[{formatted_time}] {' '.join(map(str, args))}")


def euclidean_distance(p1, p2):
    """计算两个点之间的欧几里得距离"""
    return int(math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2))


def find_nearest_coordinate(target, coordinates_list):
    """
    找到与给定坐标最近的坐标
    :param target: 给定的坐标，格式为(x, y)
    :param coordinates_list: 坐标列表，每个元素为(x, y)
    :return: 最近的坐标和距离
    """
    min_distance = float('inf')  # 初始化为正无穷大
    nearest_coordinate = None

    for coordinate in coordinates_list:
        distance = euclidean_distance(target, coordinate)
        if distance < min_distance:
            min_distance = distance
            nearest_coordinate = coordinate

    return nearest_coordinate, min_distance


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


def my_imread(my_path):
    # 读取图片
    if is_chinese(my_path):
        img = cv2.imdecode(np.fromfile(my_path, dtype=np.uint8), -1)  # 避免路径有中文
    else:
        img = cv2.imread(my_path)
    return img


def load_images_from_directory():
    """
    从指定的模板路径中加载所有PNG图片到内存,
    并返回文件名到NumPy数组的映射
    """
    # 初始化两个空字典，分别用于存储灰度图像和HSV图像的NumPy数组
    load_image_data_GRAY = {}
    load_image_data_HSV = {}

    # 获取当前时间作为开始时间
    start_time = time.time()
    # 拼接文件路径
    file_path = os.path.join(root_path, "map_depot")
    # 遍历指定模板路径下的所有文件
    for filename in os.listdir(file_path):

        # 检查文件扩展名是否为.png
        if filename.lower().endswith(('.png', '.bmp')):
            # if filename.lower().endswith('.png'):
            # 拼接文件路径
            img_file_path = os.path.join(file_path, filename)
            # 使用OpenCV库读取图片
            # image_BGR = cv2.imread(img_file_path)
            image_BGR = my_imread(img_file_path)
            # my_logger.info(f"加载图片:{img_file_path}")

            # 检查图片是否成功加载
            if image_BGR is not None:
                # 将其转换为灰度图像
                image_GRAY = cv2.cvtColor(image_BGR, cv2.COLOR_BGR2GRAY)
                # 将其转换为HSV图像
                image_HSV = cv2.cvtColor(image_BGR, cv2.COLOR_BGR2HSV)

                # 将文件名和对应的NumPy数组存储到相应的字典中
                load_image_data_GRAY[filename] = image_GRAY
                load_image_data_HSV[filename] = image_HSV

                # 获取当前时间作为结束时间
    end_time = time.time()

    # 计算代码块执行所花费的时间（秒）
    elapsed_time = end_time - start_time

    # 打印代码执行所花费的时间
    logger.info(f"从指定的模板路径中加载所有PNG图片到内存用了 {elapsed_time} 秒")

    # 返回存储了文件名和对应NumPy数组的字典
    return load_image_data_GRAY, load_image_data_HSV


# 加载目录下的所有PNG图片到内存
image_data_GRAY, image_data_HSV = load_images_from_directory()


def my_show_image(frame):
    # 创建一个名为'Image Display'的窗口
    cv2.namedWindow('img', cv2.WINDOW_AUTOSIZE)

    # 尝试设置窗口的位置（x, y）
    # 注意：这个方法可能不总是有效，取决于你的操作系统和GUI后端
    cv2.setWindowProperty('img', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
    cv2.moveWindow('img', 850, 0)  # 将窗口移动到屏幕上的(100, 100)位置
    while True:

        if frame is None:
            break

            # 显示图片
        cv2.imshow('img', frame)

        # 等待按键，如果是'q'则退出循环
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


def highlight_color_range(hsv_image, lower_bound, upper_bound):
    """
    突出指定HSV色彩范围内的颜色，并将其他颜色置为黑色。

    Args:
        hsv_image (np.ndarray): HSV色彩空间的图像数组。
        lower_bound (tuple[int, int, int]): HSV色彩范围的下限，包含三个整数值，分别对应色调(H)、饱和度(S)和明度(V)。
        upper_bound (Tuple[int, int, int]): HSV色彩范围的上限，包含三个整数值，分别对应色调(H)、饱和度(S)和明度(V)。

    Returns:
        np.ndarray: 突出色彩范围后的图像数组，其他颜色被置为黑色。

    """
    # 将输入的HSV色彩范围下限和上限转换为NumPy数组
    lower_bound = np.array(lower_bound, dtype=np.uint8)
    upper_bound = np.array(upper_bound, dtype=np.uint8)

    # 创建一个与原图同样大小的零数组，用于存放结果
    result = np.zeros_like(hsv_image)

    # 使用NumPy的布尔索引来找出色彩范围内的像素
    # 对每个通道应用色彩范围掩码
    mask = (hsv_image >= lower_bound).all(axis=-1) & (hsv_image <= upper_bound).all(axis=-1)

    # 将色彩范围内的像素复制到结果数组中，其他像素置为黑色
    result[mask] = hsv_image[mask]

    return result

    # 用于显示图片


def get_hsv_color_range(hsv_color):
    """
    根据给定的HSV颜色，判断其属于哪个色彩范围，并返回该色彩范围的下限和上限。

    Args:
        hsv_color (Tuple[int, int, int]): HSV颜色，格式为(H, S, V)，其中H为色调(0-179)，S为饱和度(0-255)，V为明度(0-255)。

    Returns:
        Tuple[Tuple[int, int, int], Tuple[int, int, int]]: 色彩范围的下限和上限，格式为((H_low, S_low, V_low), (H_high, S_high, V_high))。
    """
    h, s, v = hsv_color

    # 定义色彩范围的界限（以色调H为主，S和V可以根据需要调整）
    black = ((0, 0, 0), (180, 255, 46))  # 黑色范围
    grey = ((0, 0, 46), (180, 43, 220))  # 灰色范围
    white = ((0, 0, 221), (180, 30, 255))  # 白色范围
    red = ((0, 43, 46), (10, 255, 255))  # 红色范围
    red1 = ((156, 43, 46), (180, 255, 255))  # 红色范围
    orange = ((11, 43, 46), (25, 255, 255))  # 橙色范围
    yellow = ((26, 43, 46), (34, 255, 255))  # 黄色范围
    green = ((35, 43, 46), (77, 255, 255))  # 绿色范围
    cyan = ((78, 43, 46), (99, 255, 255))  # 青色范围
    blue = ((100, 43, 46), (124, 255, 255))  # 蓝色范围
    purple = ((125, 43, 46), (155, 255, 255))  # 紫色范围

    # 其他颜色范围可以根据需要添加

    # 判断颜色属于哪个范围
    for range_low, range_high in [black, grey, white, red, red1, orange, yellow, green, cyan, blue, purple]:
        if range_low[0] <= h <= range_high[0] and range_low[1] <= s <= range_high[1] and range_low[2] <= v <= range_high[2]:
            return range_low, range_high

            # 如果没有匹配到任何范围，返回原始颜色作为范围
    return hsv_color, hsv_color


def find_most_frequent_color_hsv(hsv_image, exclude_color=None):
    """
    查找HSV图像中出现次数最多的颜色，可以排除指定的颜色。

    Args:
        hsv_image (numpy.ndarray): 输入的HSV图像，表示为一个3D的NumPy数组。
        exclude_color (tuple[int, int, int]): 要从统计中排除的HSV颜色，格式为(H, S, V)。

    Returns:
        Tuple[int, int, int]: HSV空间中出现次数最多的颜色（排除指定颜色后），以元组形式返回，包含整数类型的H（色调）、S（饱和度）和V（明度）。

    Raises:
        ValueError: 如果输入不是NumPy数组或者不是表示HSV图像的数组。
    """
    # 确保输入是NumPy数组
    if not isinstance(hsv_image, np.ndarray):
        raise ValueError("输入必须是一个表示HSV图像的NumPy数组。")

        # 将图像展平为二维，以便计算直方图
    hsv_flattened = hsv_image.reshape(-1, 3)

    # 如果指定了要排除的颜色，则将其从数组中排除
    if exclude_color is not None:
        exclude_mask = np.all(hsv_flattened != exclude_color, axis=1)
        hsv_flattened = hsv_flattened[exclude_mask]

        # 计算每个通道的直方图
    hist_h, _ = np.histogram(hsv_flattened[:, 0], bins=180, range=(0, 180))
    hist_s, _ = np.histogram(hsv_flattened[:, 1], bins=256, range=(0, 256))
    hist_v, _ = np.histogram(hsv_flattened[:, 2], bins=256, range=(0, 256))

    # 找出每个通道出现次数最多的bin
    max_h = np.argmax(hist_h)
    max_s = np.argmax(hist_s)
    max_v = np.argmax(hist_v)

    # 将bin索引转换回HSV值
    most_frequent_color_hsv = (max_h, max_s, max_v)

    return most_frequent_color_hsv


def process_coordinates(coordinates):
    """
    从给定的坐标列表中移除与其他坐标点距离小于阈值的点。

    :param coordinates: 原始坐标列表
    :return: 不包含接近点的坐标列表
    """
    # 创建一个新列表来存储不接近的点
    threshold_distance = 10
    # 使用一个集合来存储需要删除的坐标的索引
    to_remove = set()

    # 遍历所有坐标点
    for i in range(len(coordinates)):
        # 遍历剩余的点，与当前点进行比较
        for j in range(i + 1, len(coordinates)):
            # 计算两点之间的距离
            distance = math.sqrt((coordinates[i][0] - coordinates[j][0]) ** 2 + (coordinates[i][1] - coordinates[j][1]) ** 2)

            # 如果距离小于阈值，则标记需要删除的点
            if distance < threshold_distance:
                to_remove.add(j)

                # 创建一个新列表，只包含未被标记为需要删除的点
    cleaned_coordinates = [coordinate for index, coordinate in enumerate(coordinates) if index not in to_remove]

    return cleaned_coordinates


def draw_rectangle_if_needed(color_image, maxloc, template_width, template_height, drag, box_color=(0, 255, 0)):
    """
    如果drag为True,则在目标图像上绘制矩形框标记模板位置。

    参数:
    color_image: numpy.ndarray, 目标图像
    maxloc: tuple, 匹配图像在原图中的位置坐标 (x, y)
    template_width: int, 模板图像的宽度
    template_height: int, 模板图像的高度
    pard: int, 偏移量
    x1, y1: int, 坐标调整值
    drag: bool, 是否需要绘制矩形框
    called: bool, 控制是否将图片数据放入队列中

    返回值:
    None
    """
    if drag:
        x, y = maxloc[0], maxloc[1]
        cv2.rectangle(color_image, (x, y), (x + template_width, y + template_height), box_color, thickness=2)


def FindPic_dnf_outline(img, pixel_size=(650, 2500), region_size=([63, 200], [10, 15]), drag=None, delta_color=([0, 0, 0], [179, 255, 255])):
    """
    @param img: 图片数组
    @param pixel_size:像素区域：(最小像素，最大像素)
    @param region_size:宽高限制：([最小宽度, 最大宽度], [最小高度, 最大高度])
    @param drag:是否显示图片，不等于None则显示
    @param delta_color:(min[H, S, V], max[H, S, V])
    @return:[(),()]
    """
    # if delta_color is not None:
    #
    #     # BGR转HSV颜色空间
    #     hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # else:
    #     # BGR转灰度颜色空间
    #     hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #
    # logger.info(f'耗时:{time.time() - st}')
    #
    # # 高斯去噪
    # # 这里，ksize=(5, 5)是核的大小，sigmaX=0表示从ksize自动计算sigma
    # # blurred = cv2.GaussianBlur(hsv_img, (1, 1), 0)
    # if delta_color is not None:  # 填了参数就是HSV的处理方式
    #
    #     hsv_lower = np.array(delta_color[0])
    #     hsv_upper = np.array(delta_color[1])
    #
    #     # logger.info(hsv_lower,hsv_upper)
    #
    #     # 创建掩码
    #     mask = cv2.inRange(hsv_img, hsv_lower, hsv_upper)
    #
    #     # 将掩码应用于原始图像，得到彩色图像
    #     colored_image = cv2.bitwise_and(img, img, mask=mask)
    #
    #     # cv2.imshow('Image', colored_image)
    #     # cv2.waitKey(0)
    #     # cv2.destroyAllWindows()
    #
    #     logger.info(f'耗时:{time.time() - st}')
    #
    #     # 将不在掩码中的区域设置为黑色
    #     black_image = cv2.bitwise_not(mask)
    #     black_image = cv2.bitwise_and(img, np.zeros_like(img), mask=black_image)
    #
    #     # 合并彩色图像和黑色图像
    #     final_image = cv2.add(colored_image, black_image)
    #
    #     image = cv2.cvtColor(final_image, cv2.COLOR_HSV2BGR)
    #
    #     # 灰度化  后边统一都要灰度化的
    #     image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 根据是否提供delta_color来决定是否进行颜色过滤
    if delta_color is not None:
        hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hsv_lower = np.array(delta_color[0])
        hsv_upper = np.array(delta_color[1])
        mask = cv2.inRange(hsv_img, hsv_lower, hsv_upper)
        # 掩码应用到原图上，得到只包含指定颜色的图像
        colored_image = cv2.bitwise_and(img, img, mask=mask)
        # 直接将彩色图像转换为灰度
        gray_image = cv2.cvtColor(colored_image, cv2.COLOR_BGR2GRAY)
    else:
        # 如果没有delta_color，直接转换为灰度图
        gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # # 如果需要，可以显示或保存图像
    # cv2.imshow('Binary Image', gray_image)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    # 二值化
    ret, binary_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 创建结构元素，这里使用3x3的矩形结构元素
    kernel = np.ones((2, 4), np.uint8)

    # 执行膨胀操作
    dilated_img = cv2.dilate(binary_image, kernel, iterations=1)

    if drag is not None:
        # 显示预处理后的图像
        # 显示原图和膨胀后的图像
        cv2.imshow('Original Image', binary_image)
        cv2.imshow('Dilated Image', dilated_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # 获取连通组件的数量
    # 获取连通组件的数量、标签、统计信息和质心
    num_components, labels, stats, centroids = cv2.connectedComponentsWithStats(dilated_img)

    # 创建一个空列表来存储处理过的坐标
    xy_list = []
    # 设定一个阈值，比如500像素，用于过滤小组件
    min_size = pixel_size[0]
    if drag is not None:
        # 统计每个连通组件中的白色像素数量
        white_pixel_counts = []
        for i in range(1, num_components):  # 跳过背景标签0
            # 检查当前组件的面积是否大于阈值
            if stats[i, cv2.CC_STAT_AREA] >= min_size:
                size = stats[i, cv2.CC_STAT_AREA]
                white_pixel_counts.append(size)
                # 输出结果
                logger.info("每个连通组件中的白色像素数量：", white_pixel_counts)
                logger.info("总白色像素数量：", sum(white_pixel_counts))

    # 遍历所有组件（从1开始，因为0是背景）
    for i in range(1, num_components):

        # 检查当前组件的面积是否大于阈值
        if pixel_size[1] > stats[i, cv2.CC_STAT_AREA] >= min_size:

            if drag is not None:
                x, y, w, h = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
                logger.info(f"x={x}, y={y}, w={w}, h={h}")
                # 创建一个与原始图像大小相同的掩码，并初始化为0
                mask = np.zeros(dilated_img.shape[:2], dtype=np.uint8)

                # 将当前组件的像素在掩码中标记为1
                mask[labels == i] = 1
                # 使用掩码从原始图像中提取当前组件的图像
                component_image = cv2.bitwise_and(dilated_img, dilated_img, mask=mask)
                cv2.imshow('component_image', component_image)
                cv2.waitKey(0)
                cv2.destroyAllWindows()

            # 获取当前连通组件的边界框
            # 获取当前连通组件的边界框信息
            x, y, w, h = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            if y > 250:
                if region_size[0][1] > w > region_size[0][0] and region_size[1][1] > h > region_size[1][0]:
                    x1 = x + w // 2 - 10
                    y1 = y + 12
                    x2 = x + w // 2 + 10
                    y2 = y + 30
                    xy_list.append([x1, y1, x2, y2])
                    # logger.info(x, y, w, h)
                    # logger.info(xy_list)
                    if drag is not None:
                        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.imshow("img", img)
                        cv2.waitKey()
                        cv2.destroyAllWindows()

    return xy_list


def get_hwnd():
    dnf_hwnd = win32gui.FindWindow('地下城与勇士', '地下城与勇士：创新世纪')
    if dnf_hwnd != 0:
        logger.info("地下城与勇士：创新世纪窗口的句柄:", dnf_hwnd)
    return dnf_hwnd


try:
    hwnd = get_hwnd()

except Exception as e:
    logger.info("update_settings_group_data:", e)
    logger.info("完整堆栈：")
    traceback.logger.info_exc()


class MM:
    def __init__(self, img_path=None, ):
        self.hwnd = hwnd
        # 检查找图路径是否在实例时添加了
        if img_path:
            self.target_image = my_imread(img_path)
            logger.info(f"读取路径为:{img_path}")
        # 初始化存放找到坐标的数组
        self.arr_ret = []
        self.target_image = None
        self.path = img_path
        self.count = 0

        # 加载目录下的所有PNG图片到内存
        self.image_data_GRAY, self.image_data_HSV = image_data_GRAY, image_data_HSV
        # 显示图片用数组
        self.screenshot_show_image = None
        self.VNC = None

    # def screenshot_OCR(self, x1, y1, x2, y2, image_template_name, sim, get_colour=None, drag=None):
    #     """
    #
    #     :param x1: 截图区域的左上角x坐标。
    #     :param y1: 截图区域的左上角y坐标。
    #     :param x2: 截图区域的右下角x坐标。
    #     :param y2: 截图区域的右下角y坐标。
    #     :param image_template_name: 包含模板图像名称的字符串，多个模板名称之间用"|"分隔。
    #     :param sim: 模板匹配的最小相似度阈值。
    #     :param get_colour: HSV空间的色彩范围，下限和上限
    #             # 定义要检测的颜色范围（红色）
    #             lower_blue = np.array([0, 220, 220])
    #             upper_blue = np.array([360, 230, 255])
    #             参考写法screenshot_OCR(self,x1, y1, x2, y2, gray_image_template, sim,([0, 220, 220],[360, 230, 255]))
    #     :param drag:
    #     :return: int: 识别到的与模板匹配的数字，如果未识别到任何元素则返回-1。
    #     """
    #     # 捕获指定区域的屏幕截图
    #     screenshot_np = None
    #     # 如果指定了路径，读取路径中的图片
    #     if self.path is not None:
    #         if drag is not None:
    #             logger.info("读取路径中的图片")
    #         # 读取图片，默认读取是BGR格式
    #         screenshot_np = cv2.imread(self.path)
    #         # 这里用做画出找到位置显示的图片
    #         self.screenshot_show_image = screenshot_np  # 转为灰度图像  # self.target_image = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
    #     elif self.hwnd is not None:
    #         screenshot_np = Capture(self.hwnd, x1, y1, x2, y2)
    #         if drag is not None:
    #             logger.info("保存到内存中")
    #         # 这里用做画出找到位置显示的图片
    #         self.screenshot_show_image = screenshot_np
    #
    #         # 转为灰度图像  # self.target_image = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
    #
    #     if get_colour is not None:
    #
    #         # BGR转HSV颜色空间
    #         hsv_img = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2HSV)
    #     else:
    #         # BGR转灰度颜色空间
    #         hsv_img = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
    #
    #     # 目标图片处理
    #     imge_s, _ = self.image_pretreatment(hsv_img, get_colour=get_colour, drag=drag)
    #     # logger.info(imge_s)
    #
    #     # 使用split()方法分割字符串看看传进几个图片
    #     teamp_img_name_array = image_template_name.split("|")
    #
    #     # logger.info(teamp_img_name_array)
    #
    #     # 调用全局打印
    #     logger.info(teamp_img_name_array)
    #
    #     # 收集匹配结果
    #     retstring = ''
    #
    #     # 遍历截图的连通组件
    #     # 迭代并显示每个组件图像
    #     for i, component_image in enumerate(imge_s):
    #         # 检查图像是否有效
    #         if component_image is not None and component_image.size > 0:
    #
    #             if drag is not None:
    #                 pass
    #
    #                 # cv2.imshow('component_image', component_image)  # cv2.waitKey(0)  # cv2.destroyAllWindows()
    #
    #             # 遍历预定义的图像名称数组
    #             for idx1, teamp_img_name in enumerate(teamp_img_name_array):
    #
    #                 # logger.info(f'id=={id},teamp_img_name == {teamp_img_name}')
    #
    #                 # 输入图片名返回预加载的图片数据
    #                 template_image = self.get_image(teamp_img_name, color_space=get_colour)  # 如果有参数就是HSV色彩空间的图片
    #
    #                 # logger.info(f'144--{template_image}')
    #                 # logger.info(f'145--{type(template_image)}')
    #
    #                 # 对模板图像进行预处理
    #                 _, templates = self.image_pretreatment(template_image, get_colour=get_colour, drag=drag)
    #                 # 遍历截图的连通组件
    #                 # 迭代并显示每个组件图像
    #                 for j, temp_image in enumerate(templates):
    #                     # 检查图像是否有效
    #                     if temp_image is not None and temp_image.size > 0:
    #
    #                         if drag is not None:
    #                             pass  # cv2.imshow(f'tempimage{j}', temp_image)  # cv2.waitKey(0)  # cv2.destroyAllWindows()
    #
    #                     # 使用模板匹配算法在组件图像中查找模板
    #                     result = cv2.matchTemplate(component_image, temp_image, cv2.TM_CCOEFF_NORMED)
    #
    #                     # 找出匹配的区域
    #                     loc = np.where(result >= sim)
    #                     """如果多个符合相似度则返回多个的坐标，例如(array([210, 310, 310, 310, 410, 410, 410, 510, 510], dtype=int64),
    #                     array([320, 319, 320, 321, 319, 320, 321, 319, 320], dtype=int64))前面的arrary()是y坐标,后面的arrary()是x坐标"""
    #
    #                     # 使用 loc 中的索引从 result 中获取对应的相似度的值
    #                     arr_ = result[loc[0], loc[1]]
    #
    #                     # 看下是否筛选出数据
    #                     if arr_.size > 0:
    #                         # 如果大于阈值则认为识别到图片，记下第几张，第几张对应数字比如第一张为0则对应数字0
    #                         if np.max(arr_) >= sim:
    #                             # 将匹配到的模板ID拼接到retstring中
    #                             retstring += str(idx1)
    #
    #         else:
    #             logger.info(f"Invalid image at index {i}")
    #
    #             #         # logger.info(type(arr_))
    #     #         # <class 'numpy.ndarray'>
    #
    #     #         # # 在原图像上绘制匹配到的模板位置
    #     #         # for pt in zip(*loc[::-1]):
    #     #         #     cv2.rectangle(image, pt, (pt[0] + template.shape[1], pt[1] + template.shape[0]), (0, 0, 255), 2)
    #     #         #     # 如果启用，则打印匹配到的最大值和位置
    #     #         #     my_logger.info(max_val)
    #     #         #     my_logger.info(pt)
    #     #         #
    #
    #     # 如果retstring不为空，则识别到了升级点
    #     if retstring:
    #
    #         return retstring  # 直接返回原始字符串
    #
    #     else:
    #
    #         # 如果没有识别到数字，则返回-1
    #         return -1
    def screenshot_OCR_str(self, x1, y1, x2, y2, image_template_name, sim, get_colour=None, drag=None):
        """
        优化后的数字识别方法，专注于识别数字字符
        """
        # 捕获指定区域的屏幕截图
        if not self.hwnd:
            logger.info("错误：无效的窗口句柄")
            return ''

        try:
            if self.VNC is not None:
                screenshot_np = self.VNC.capture()[0:600, 0:1067]
            else:
                # 捕获屏幕区域
                screenshot_np = Capture(self.hwnd, 0, 0, 1067, 600)
            region = screenshot_np[y1:y2, x1:x2]

            # 保存原始图像用于调试
            if drag is not None:
                cv2.imwrite("debug_original.png", region)
                logger.info(f"保存原始图像到 debug_original.png")
        except Exception as e:
            logger.info(f"捕获屏幕区域时出错: {e}")
            return ''

        # 颜色空间转换
        if get_colour is not None:
            try:
                processed_img = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
            except Exception as e:
                logger.info(f"颜色空间转换错误: {e}")
                return ''
        else:
            try:
                processed_img = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            except Exception as e:
                logger.info(f"灰度转换错误: {e}")
                return ''

        # 预处理目标图像 - 获取裁剪后的数字区域
        try:
            _, target_components = self.image_pretreatment(
                processed_img,
                get_colour=get_colour,
                drag=drag
            )
            logger.info(f"找到 {len(target_components)} 个数字区域")
        except Exception as e:
            logger.info(f"图像预处理错误: {e}")
            return ''

        # 处理模板图像
        template_names = image_template_name.split("|")
        templates = {}  # {数字字符: 模板图像}

        for name in template_names:
            try:
                label = name.split(".")[0]  # 假设文件名就是数字字符
                logger.info(f"处理模板: {label}")

                # 加载模板图像
                template_img = self.get_image(name, color_space=get_colour)

                # 预处理模板 - 只取第一个有效的连通组件
                _, template_components = self.image_pretreatment(
                    template_img,
                    get_colour=get_colour,
                    drag=drag
                )

                # 只取第一个有效组件（数字模板）
                if template_components and template_components[0].size > 0:
                    templates[label] = template_components[0]
                    logger.info(f"模板 '{label}' 尺寸: {template_components[0].shape}")

                    # 调试显示
                    if drag is not None:
                        cv2.imshow(f'Template: {label}', template_components[0])
                        cv2.waitKey(1000)  # 等待1秒而不是立即关闭
                else:
                    logger.info(f"警告: 模板 '{label}' 未找到有效组件")
            except Exception as e:
                logger.info(f"处理模板 '{name}' 时出错: {e}")

        # 识别结果
        recognized_digits = []

        logger.info(f"开始匹配 {len(target_components)} 个数字区域...")

        # 遍历目标图像中的每个数字区域
        for i, digit_region in enumerate(target_components):
            if digit_region is None or digit_region.size == 0:
                logger.info(f"数字区域 {i} 无效 - 跳过")
                continue

            logger.info(f"处理数字区域 {i} - 尺寸: {digit_region.shape}")

            # 调试显示
            if drag is not None:
                cv2.imshow(f'Digit Region {i}', digit_region)
                cv2.waitKey(1000)  # 等待1秒而不是立即关闭

            best_match = None
            best_similarity = 0
            best_template = None

            # 与所有模板进行匹配
            for digit_char, template_img in templates.items():
                # 检查模板尺寸是否适合目标区域
                if template_img.shape[0] > digit_region.shape[0] or template_img.shape[1] > digit_region.shape[1]:
                    logger.info(f"  模板 '{digit_char}' 太大 ({template_img.shape} vs {digit_region.shape}) - 跳过")
                    continue

                try:
                    # 调整模板尺寸以匹配目标区域（如果需要）
                    if template_img.shape != digit_region.shape:
                        resized_template = cv2.resize(template_img, (digit_region.shape[1], digit_region.shape[0]))
                        logger.info(f"  调整模板 '{digit_char}' 尺寸: {template_img.shape} -> {digit_region.shape}")
                    else:
                        resized_template = template_img

                    # 模板匹配
                    result = cv2.matchTemplate(digit_region, resized_template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                    logger.info(f"  匹配 '{digit_char}': 最大相似度 = {max_val:.4f}")

                    # 更新最佳匹配
                    if max_val > best_similarity:
                        best_similarity = max_val
                        best_match = digit_char
                        best_template = resized_template

                        # 调试显示匹配结果
                        if drag is not None and max_val >= sim:
                            h, w = resized_template.shape
                            top_left = max_loc
                            bottom_right = (top_left[0] + w, top_left[1] + h)

                            # 创建带匹配框的副本
                            match_vis = digit_region.copy()
                            cv2.rectangle(match_vis, top_left, bottom_right, 128, 2)
                            cv2.imshow(f'Match: {digit_char} ({max_val:.2f})', match_vis)
                            cv2.waitKey(500)
                except Exception as e:
                    logger.info(f"  匹配模板 '{digit_char}' 时出错: {e}")

            # 保存有效匹配
            if best_match and best_similarity >= sim:
                logger.info(f"  最佳匹配: '{best_match}' (相似度 = {best_similarity:.4f})")
                recognized_digits.append(best_match)
            else:
                logger.info(f"  未找到有效匹配 (最高相似度 = {best_similarity:.4f})")

        # 返回识别结果
        result = ''.join(recognized_digits)
        logger.info(f"最终识别结果: '{result}'")
        return result

    def image_pretreatment(self, image, get_colour=None, drag=None):
        """
        优化后的图像预处理方法，专注于数字识别
        """
        # 如果是彩色图像但未指定颜色范围，转换为灰度
        if len(image.shape) == 3 and get_colour is None:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # HSV颜色处理
        if get_colour is not None:
            try:
                # 确保是HSV图像
                if len(image.shape) == 2 or image.shape[2] != 3:
                    logger.info("警告: 非HSV图像，跳过颜色处理")
                else:
                    hsv_lower = np.array(get_colour[0])
                    hsv_upper = np.array(get_colour[1])

                    # 创建掩码
                    mask = cv2.inRange(image, hsv_lower, hsv_upper)

                    # 应用掩码
                    colored_image = cv2.bitwise_and(image, image, mask=mask)
                    black_image = cv2.bitwise_not(mask)
                    black_image = cv2.bitwise_and(image, np.zeros_like(image), mask=black_image)
                    final_image = cv2.add(colored_image, black_image)

                    # 转换为灰度图
                    image = cv2.cvtColor(final_image, cv2.COLOR_HSV2BGR)
                    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            except Exception as e:
                logger.info(f"HSV处理错误: {e}")

        # 二值化
        try:
            _, binary_image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        except Exception as e:
            logger.info(f"二值化错误: {e}")
            return [], []

        # # 形态学操作 - 优化数字识别
        # try:
        #     kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        #     cleaned_image = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel)
        #     cleaned_image = cv2.morphologyEx(cleaned_image, cv2.MORPH_CLOSE, kernel)
        # except Exception as e:
        #     logger.info(f"形态学操作错误: {e}")
        #     cleaned_image = binary_image

        # 调试显示
        if drag is not None:
            cv2.imshow('Original', image)
            cv2.waitKey(500)
            cv2.imshow('Binary', binary_image)
            cv2.waitKey(500)

        # 查找连通组件
        try:
            num_components, labels, stats, centroids = cv2.connectedComponentsWithStats(
                binary_image, connectivity=8
            )
            logger.info(f"找到 {num_components - 1} 个连通组件")
        except Exception as e:
            logger.info(f"连通组件分析错误: {e}")
            return [], []

        # 存储组件信息
        components = []
        cropped_components = []

        # 遍历所有组件（跳过背景）
        for i in range(1, num_components):
            try:
                # 提取组件区域
                x, y, w, h = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], \
                    stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]

                # # 过滤掉太小的组件（可能是噪声）
                # if w < 5 or h < 5:
                #     logger.info(f"  跳过小组件: {w}x{h} (位置: {x},{y})")
                #     continue

                logger.info(f"  组件 {i}: {w}x{h} (位置: {x},{y})")

                # 创建组件掩码
                component_mask = np.zeros_like(binary_image)
                component_mask[labels == i] = 255

                # 提取完整组件图像
                component_image = cv2.bitwise_and(binary_image, binary_image, mask=component_mask)
                components.append(component_image)

                # 裁剪组件区域
                cropped = binary_image[y:y + h, x:x + w]
                cropped_components.append(cropped)

                # 调试显示
                if drag is not None:
                    cv2.imshow(f'Component {i}', cropped)
                    cv2.waitKey(500)
            except Exception as e:
                logger.info(f"处理组件 {i} 时出错: {e}")

        # 按X坐标排序（从左到右）
        try:
            sorted_indices = sorted(range(len(components)), key=lambda i: stats[i + 1, cv2.CC_STAT_LEFT])
            sorted_components = [components[i] for i in sorted_indices]
            sorted_cropped = [cropped_components[i] for i in sorted_indices]
        except Exception as e:
            logger.info(f"排序错误: {e}")
            sorted_components = components
            sorted_cropped = cropped_components

        return sorted_components, sorted_cropped

    # def screenshot_OCR_str(self, x1, y1, x2, y2, image_template_name, sim, get_colour=None, drag=None):
    #     """
    #     对指定屏幕区域进行截图，并应用OCR（光学字符识别）技术识别截图中与给定模板匹配的元素。
    #
    #     Args:
    #         x1 (int): 截图区域的左上角x坐标。
    #         y1 (int): 截图区域的左上角y坐标。
    #         x2 (int): 截图区域的右下角x坐标。
    #         y2 (int): 截图区域的右下角y坐标。
    #         image_template_name (str): 包含模板图像名称的字符串，多个模板名称之间用"|"分隔。
    #         Sim (float): 模板匹配的最小相似度阈值。
    #
    #     Returns:
    #         str: 识别到的与模板匹配的数字，如果未识别到任何元素则返回-1。
    #
    #     get_colour:HSV空间的色彩范围，下限和上限
    #             # 定义要检测的颜色范围（红色）
    #             lower_blue = np.array([0, 220, 220])
    #             upper_blue = np.array([360, 230, 255])
    #             参考写法screenshot_OCR(self,x1, y1, x2, y2, gray_image_template, Sim,([0, 220, 220],[360, 230, 255]))
    #
    #     """
    #     # 捕获指定区域的屏幕截图
    #     if self.hwnd:
    #         screenshot_np = Capture(self.hwnd, 0, 0, 1067, 600)
    #         BGR = screenshot_np[y1:y2, x1:x2]
    #
    #     if get_colour is not None:
    #
    #         # BGR转HSV颜色空间
    #         hsv_img = cv2.cvtColor(BGR, cv2.COLOR_BGR2HSV)
    #     else:
    #         # BGR转灰度颜色空间
    #         hsv_img = cv2.cvtColor(BGR, cv2.COLOR_BGR2GRAY)
    #
    #     # 目标图片处理
    #     imge_s, _ = self.image_pretreatment(hsv_img, get_colour=get_colour, drag=drag)
    #     # logger.info(imge_s)
    #
    #     # 使用split()方法分割字符串看看传进几个图片
    #     teamp_img_name_array = image_template_name.split("|")
    #
    #     # logger.info(teamp_img_name_array)
    #
    #     # 收集匹配结果
    #     retstring = ''
    #
    #     labels = {}
    #     # 遍历预定义的图像名称数组
    #     for id, teamp_img_name in enumerate(teamp_img_name_array):
    #
    #         label = teamp_img_name.split(".")[0]
    #
    #         # 输入图片名返回预加载的图片数据
    #         template_image = self.get_image(teamp_img_name, color_space=get_colour)  # 如果有参数就是HSV色彩空间的图片
    #
    #         # 对模板图像进行预处理
    #         _, templates = self.image_pretreatment(template_image, get_colour=get_colour, drag=drag)
    #         # 遍历截图的连通组件
    #         # 迭代并显示每个组件图像
    #         for i, temp_image in enumerate(templates, start=0):
    #             # 检查图像是否有效
    #             if temp_image is not None and temp_image.size > 0:
    #                 # 把标签和图片添加到字典里
    #                 labels[label] = temp_image
    #                 if drag is not None:
    #                     cv2.imshow('temp_image', temp_image)
    #                     cv2.waitKey(0)
    #                     cv2.destroyAllWindows()
    #
    #     # # 遍历截图的连通组件
    #     # # 迭代并显示每个组件图像
    #     for i, component_image in enumerate(imge_s):
    #         # 检查图像是否有效
    #         if component_image is not None and component_image.size > 0:
    #
    #             if drag is not None:
    #                 cv2.imshow('component_image', component_image)
    #                 cv2.waitKey(0)
    #                 cv2.destroyAllWindows()
    #
    #             for key, value in labels.items():
    #
    #                 # 使用模板匹配算法在组件图像中查找模板
    #                 result = cv2.matchTemplate(component_image, value, cv2.TM_CCOEFF_NORMED)
    #
    #                 # 找出匹配的区域
    #                 loc = np.where(result >= sim)
    #                 # 如果找到了匹配项
    #                 if loc[0].size > 0 and loc[1].size > 0:
    #                     # 获取所有匹配项的相似度值（这一步其实是多余的，因为我们已经通过 np.where 筛选过了）
    #                     # 但为了保持与原始代码的逻辑一致，这里还是保留了
    #                     arr_ = result[loc[0], loc[1]]
    #
    #                     # 将匹配到的模板ID拼接到retstring中，并添加分隔符（例如逗号）
    #                     # 注意：这里假设您想要记录所有匹配到的模板ID，而不仅仅是相似度最高的那一个
    #                     # 如果您只想记录相似度最高的那一个，您应该使用 np.argmax() 或类似的方法来找到它
    #                     for _ in range(arr_.size):  # 由于我们不知道会有多少个匹配项，所以使用 arr_.size 来迭代
    #                         retstring += str(key)  # 添加模板ID
    #                     # 如果不需要在最后一个模板ID后面也添加分隔符，可以移除上面循环中的最后一个逗号
    #                     # 或者在循环结束后使用 retstring.rstrip(",") 来移除末尾的多余分隔符
    #
    #     # 如果retstring不为空，则识别到了升级点
    #     if retstring:
    #
    #         return retstring  # 直接返回原始字符串
    #
    #     else:
    #
    #         # 如果没有识别到数字，则返回-1
    #         return ''
    #
    # def image_pretreatment(self, image, get_colour=None, drag=None):  # 找数字预处理
    #     """
    #     对给定的灰度图像进行预处理，以识别其中的数字模板。  get_colouro默认参数为处理灰度图像,当get_colour为色彩上下限时时处理HSV图像
    #
    #     Args:
    #         self (object): 类实例对象本身。
    #         image (numpy.ndarray): 根据需要选择要输入的灰度图像或HSV图像，应为二维数组，数据类型为uint8。
    #         get_colour:色彩范围颜色列表
    #         drag：是否显示图片
    #
    #     Returns:
    #         numpy.ndarray: 经过预处理后的数字图像。
    #
    #     cut_out: 如果cut_out写了参数，则返回裁剪过的连通组件 用做模板图片进行匹配
    #             如果cut_out没写参数，则返回没裁切过的前连通组件用作 目标图片进行匹配
    #
    #     """
    #
    #     if get_colour is not None:  # 填了参数就是HSV的处理方式
    #
    #         hsv_lower = np.array(get_colour[0])
    #         hsv_upper = np.array(get_colour[1])
    #
    #         # logger.info(hsv_lower,hsv_upper)
    #
    #         # 创建掩码
    #         mask = cv2.inRange(image, hsv_lower, hsv_upper)
    #
    #         # 将掩码应用于原始图像，得到彩色图像
    #         colored_image = cv2.bitwise_and(image, image, mask=mask)
    #
    #         # 将不在掩码中的区域设置为黑色
    #         black_image = cv2.bitwise_not(mask)
    #         black_image = cv2.bitwise_and(image, np.zeros_like(image), mask=black_image)
    #
    #         # 合并彩色图像和黑色图像
    #         final_image = cv2.add(colored_image, black_image)
    #
    #         image = cv2.cvtColor(final_image, cv2.COLOR_HSV2BGR)
    #
    #         # 灰度化  后边统一都要灰度化的
    #         image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    #
    #         # 二值化
    #     ret, binary_image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    #
    #     # 去噪
    #     kernel = np.ones((3, 3), np.uint8)
    #     opening = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel, iterations=2)
    #
    #     # 对比度增强
    #     equalized_image = cv2.equalizeHist(image)
    #
    #     if drag is not None:
    #         # 显示预处理后的图像
    #
    #         cv2.imshow('Binary Image', binary_image)
    #         cv2.imshow('Opening Image', opening)
    #         cv2.imshow('Equalized Image', equalized_image)
    #         cv2.waitKey(0)
    #         cv2.destroyAllWindows()
    #
    #     # 假设你已经有了一个二值化的图像 binary_image
    #     # 查找连通组件
    #     # 检测二值图像中的连通组件，并返回标签和组件数量
    #     ret, labels = cv2.connectedComponents(binary_image)
    #
    #     # 创建一个掩码，其中连通组件标记为白色，背景为黑色
    #     # 创建一个与二值图像相同大小和类型的全黑图像
    #     mask = np.zeros_like(binary_image)
    #     # 将标签大于0的位置设置为白色，即只标记连通组件
    #     mask[labels > 0] = 255
    #
    #     # 获取连通组件的数量
    #     # 获取连通组件的数量、标签、统计信息和质心
    #     num_components, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_image)
    #
    #     # 用来返回处理过的图片
    #
    #     # 现在你可以遍历每个连通组件，并单独处理每个数字
    #     # 遍历每个连通组件
    #     # 创建一个空列表来存储每个组件的图像
    #     component_images = []
    #     temp_imge_component_images = []
    #     # 创建一个字典来存储组件索引、掩码和裁剪后的图像
    #     components_dict = {}
    #     # 遍历所有组件（从1开始，因为0是背景）
    #     for i in range(1, num_components):
    #         # 创建一个与原始图像大小相同的掩码，并初始化为0
    #         mask = np.zeros(binary_image.shape[:2], dtype=np.uint8)
    #
    #         # 将当前组件的像素在掩码中标记为1
    #         mask[labels == i] = 1
    #
    #         # 使用掩码从原始图像中提取当前组件的图像
    #         component_image = cv2.bitwise_and(binary_image, binary_image, mask=mask)
    #         #
    #         # # 将提取的组件图像添加到列表中
    #         # component_images.append(component_image)
    #         # logger.info(component_image)
    #
    #         # cv2.imshow('component_image', component_image)
    #         # cv2.waitKey(0)
    #         # cv2.destroyAllWindows()
    #
    #         '''下面这里是模板图片需要的裁剪过的小图'''
    #
    #         # 获取当前连通组件的边界框
    #         # 获取当前连通组件的边界框信息
    #         x, y, w, h = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
    #
    #         # 使用边界框裁剪原始图像
    #         # 根据边界框信息裁剪出当前连通组件的图像
    #         cropped_component = binary_image[y:y + h, x:x + w]
    #
    #         # 裁切过模板图片
    #         temp_imge_component_images.append(cropped_component)
    #
    #         # 将信息存储到字典中，以x坐标作为键（或作为值的一部分，然后排序）
    #         components_dict[i] = {
    #             'x': x,
    #             'component_image': component_image,
    #             'cropped_component': cropped_component
    #         }
    #
    #         # if drag is not None:
    #
    #         #     # 显示预处理后的图像
    #
    #     # 根据x坐标对字典中的组件进行排序
    #     sorted_components = sorted(components_dict.items(), key=lambda item: item[1]['x'])
    #
    #     # 提取排序后的组件图像和裁剪后的图像
    #     sorted_component_images = [item[1]['component_image'] for item in sorted_components]
    #
    #     return sorted_component_images, temp_imge_component_images

    # def image_pretreatment(self, image, get_colour=None, drag=None):  # 找数字预处理
    #     """
    #     对给定的灰度图像进行预处理，以识别其中的数字模板。  get_colouro默认参数为处理灰度图像,当get_colour为色彩上下限时时处理HSV图像
    #
    #     Args:
    #         self (object): 类实例对象本身。
    #         image (numpy.ndarray): 根据需要选择要输入的灰度图像或HSV图像，应为二维数组，数据类型为uint8。
    #         get_colour:色彩范围颜色列表
    #         drag：是否显示图片
    #
    #     Returns:
    #         numpy.ndarray: 经过预处理后的数字图像。
    #
    #     cut_out: 如果cut_out写了参数，则返回裁剪过的连通组件 用做模板图片进行匹配
    #             如果cut_out没写参数，则返回没裁切过的前连通组件用作 目标图片进行匹配
    #             :param image:
    #             :param get_colour:
    #             :param drag:
    #
    #     """
    #     # 高斯去噪
    #     # 这里，ksize=(5, 5)是核的大小，sigmaX=0表示从ksize自动计算sigma
    #     blurred = cv2.GaussianBlur(image, (1, 1), 0)
    #     if get_colour is not None:  # 填了参数就是HSV的处理方式
    #
    #         hsv_lower = np.array(get_colour[0])
    #         hsv_upper = np.array(get_colour[1])
    #
    #         # logger.info(hsv_lower,hsv_upper)
    #
    #         # 创建掩码
    #         mask = cv2.inRange(blurred, hsv_lower, hsv_upper)
    #
    #         # 将掩码应用于原始图像，得到彩色图像
    #         colored_image = cv2.bitwise_and(image, image, mask=mask)
    #
    #         # 将不在掩码中的区域设置为黑色
    #         black_image = cv2.bitwise_not(mask)
    #         black_image = cv2.bitwise_and(image, np.zeros_like(image), mask=black_image)
    #
    #         # 合并彩色图像和黑色图像
    #         final_image = cv2.add(colored_image, black_image)
    #
    #         image = cv2.cvtColor(final_image, cv2.COLOR_HSV2BGR)
    #
    #         # 灰度化  后边统一都要灰度化的
    #         image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    #
    #         # 二值化
    #     ret, binary_image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    #
    #     # 去噪
    #     kernel = np.ones((1, 1), np.uint8)
    #     opening = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel, iterations=2)
    #
    #     # 对比度增强
    #     equalized_image = cv2.equalizeHist(image)
    #
    #     # if drag is not None:
    #     #     # 显示预处理后的图像
    #     #
    #     #     cv2.imshow('Binary Image', binary_image)
    #     #     cv2.waitKey(0)
    #     #     cv2.destroyAllWindows()
    #     #     cv2.imshow('Opening Image', opening)
    #     #     cv2.waitKey(0)
    #     #     cv2.destroyAllWindows()
    #     #     cv2.imshow('Equalized Image', equalized_image)
    #     #     cv2.waitKey(0)
    #     #     cv2.destroyAllWindows()
    #
    #     # 假设你已经有了一个二值化的图像 binary_image
    #     # 查找连通组件
    #     # 检测二值图像中的连通组件，并返回标签和组件数量
    #     ret, labels = cv2.connectedComponents(binary_image)
    #
    #     # 创建一个掩码，其中连通组件标记为白色，背景为黑色
    #     # 创建一个与二值图像相同大小和类型的全黑图像
    #     mask = np.zeros_like(binary_image)
    #     # 将标签大于0的位置设置为白色，即只标记连通组件
    #     mask[labels > 0] = 255
    #
    #     # 获取连通组件的数量
    #     # 获取连通组件的数量、标签、统计信息和质心
    #     num_components, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_image)
    #
    #     # 用来返回处理过的图片
    #
    #     # 现在你可以遍历每个连通组件，并单独处理每个数字
    #     # 遍历每个连通组件
    #     # 创建一个空列表来存储每个组件的图像
    #     component_images = []
    #     temp_imge_component_images = []
    #     # 设定一个阈值，比如500像素，用于过滤小组件
    #     min_size = 10
    #
    #     # 遍历所有组件（从1开始，因为0是背景）
    #     for i in range(1, num_components):
    #
    #         # 检查当前组件的面积是否大于阈值
    #         if stats[i, cv2.CC_STAT_AREA] >= min_size:
    #
    #             # 创建一个与原始图像大小相同的掩码，并初始化为0
    #             mask = np.zeros(binary_image.shape[:2], dtype=np.uint8)
    #
    #             # 将当前组件的像素在掩码中标记为1
    #             mask[labels == i] = 1
    #
    #             # 使用掩码从原始图像中提取当前组件的图像
    #             component_image = cv2.bitwise_and(binary_image, binary_image, mask=mask)
    #
    #             # 将提取的组件图像添加到列表中
    #             component_images.append(component_image)
    #             # logger.info(component_image)
    #
    #             # cv2.imshow('component_image', component_image)
    #             # cv2.waitKey(0)
    #             # cv2.destroyAllWindows()
    #
    #             '''下面这里是模板图片需要的裁剪过的小图'''
    #
    #             # 获取当前连通组件的边界框
    #             # 获取当前连通组件的边界框信息
    #             x, y, w, h = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
    #
    #             # 使用边界框裁剪原始图像
    #             # 根据边界框信息裁剪出当前连通组件的图像
    #             cropped_component = binary_image[y:y + h, x:x + w]
    #
    #             # 裁切过模板图片
    #             temp_imge_component_images.append(cropped_component)
    #
    #             if drag is not None:
    #                 self.count += 1
    #                 my_path = r"C:\Users\Administrator\Desktop\ultralytics-8.1.0\yys\imgs"
    #                 # filename = f"/{i}.png"
    #                 filename = os.path.join(my_path, f"{self.count}.png")
    #                 cv2.imwrite(filename, cropped_component)
    #                 if os.path.exists(filename) and os.path.isfile(filename):
    #                     logger.info(f"图像已保存到：{filename}")
    #                 else:
    #                     logger.info(f"路径 '{filename}' 不存在或不是一个文件")
    #
    #         # if drag is not None:
    #
    #         #     # 显示预处理后的图像
    #
    #     return component_images, temp_imge_component_images

    def get_image(self, filename, color_space=None):
        """
        不输入参数则默认读取灰度图像, 输入参数则为HSV空间图像
        假设所有图像都是.png格式的
        """
        # if not filename.endswith('.png'):
        if not filename.lower().endswith(('.png', '.bmp')):
            # 如果文件名没有以.png结尾，则添加它
            filename += '.png'
        if color_space is None:
            """根据文件名从内存中获取对应的图片数据"""
            return self.image_data_GRAY.get(filename)
        else:
            """根据文件名从内存中获取对应的图片数据"""
            return self.image_data_HSV.get(filename)

    def show_image(self, filename):
        # 显示预加载的图片
        image = self.get_image(filename)
        if image is not None:
            cv2.imshow('Image', image)
            cv2.waitKey(0)  # 等待用户按键
            cv2.destroyAllWindows()  # 关闭所有窗口

    # 判断字符串是否为中文

    def FindPic_sleep(self, x1, y1, x2, y2, img_name, sim=0.7, mc=False, drag=None, time_s=None, my_sleep=0.1, delta_color=([0, 0, 0], [179, 255, 255])):
        """
        在指定区域内查找图片，支持超时设置。

        Args:
            delta_color: hsv色彩空间中的最小值，和最大值(lower_color,upper_color)
            x1 (int): 查找区域的左上角 x 坐标。
            y1 (int): 查找区域的左上角 y 坐标。
            x2 (int): 查找区域的右下角 x 坐标。
            y2 (int): 查找区域的右下角 y 坐标。
            img_name (str): 要查找的图片的文件名或路径。
            sim (float, optional): 图片相似度阈值，默认值为 0.7。
            mc (bool, optional): 是否返回多个匹配坐标，默认值为 False。
            drag (Any, optional): 其他可选参数，具体取决于 FindPic 方法的实现。
            time_s (float, optional): 超时时间（秒），超过该时间后停止查找。如果为 None，则只执行一次 FindPic 方法。如果为 0，则无限期等待直到找到图片。
            my_sleep (float, optional): 每次找图间隔多长时间
        Returns:
            list: 包含找到的图片坐标的列表，如果未找到图片或超时则返回空列表。
        # 使用示例
        # 只查找一次
        result = self.FindPic_sleep(x1, y1, x2, y2, 'img.png',0.9,1)

        # 无限期查找图片
        result = self.FindPic_sleep(x1, y1, x2, y2, 'img.png',0.9,1, time_s=0)

        # 超时查找图片
        result = self.FindPic_sleep(x1, y1, x2, y2, 'img.png',0.9,1, time_s=5)
        """
        if time_s is None:
            # 如果 time_s 未提供或为 None，则只查找一次
            return self.FindPic(x1, y1, x2, y2, img_name, sim=sim, mc=mc, drag=drag, delta_color=delta_color)
        elif time_s == 0:
            # 如果 time_s 为 0，则无限期查找图片，直到找到为止
            while not STOP_EVENT.is_set():  # 线程检测STOP_EVENT是否为False，如果是则继续循环
                result = self.FindPic(x1, y1, x2, y2, img_name, sim=sim, mc=mc, drag=drag, delta_color=delta_color)
                if result:
                    # 如果找到了图片，返回结果
                    return result
                time.sleep(1)  # 每次尝试之间休眠 1 秒

        else:
            # 如果 time_s 大于 0，则循环查找，直到超时
            start_time = time.time()
            while not STOP_EVENT.is_set():  # 线程检测STOP_EVENT是否为False，如果是则继续循环
                result = self.FindPic(x1, y1, x2, y2, img_name, sim=sim, mc=mc, drag=drag, delta_color=delta_color)
                if result:
                    # 如果找到了图片，返回结果
                    return result
                elapsed_time = time.time() - start_time
                if elapsed_time >= time_s:
                    # 如果超时，则打印信息并返回空列表
                    logger.info(f"已超时，未找到图片：{img_name}。")
                    return []
                logger.info(f"在 {time_s - elapsed_time} 秒后超时，未找到图片:{img_name}。")
                time.sleep(my_sleep)  # 每次循环等待 0.5 秒
        if STOP_EVENT.is_set():
            logger.info("搜索已停止。")
            return []

    def FindPic(self, x1: int, y1: int, x2: int, y2: int, img_name, sim=0.7, mc=False, drag=None, delta_color=([0, 0, 0], [179, 255, 255]), add_offset=True, img_numpy=None):
        """
        FindPic(self,x1, y1, x2, y2,img_name,sim=0.7,use_hsv=False,Multiple_coordinates=False,drag=None)
        找到图就返回[[id,x,y]],找不到图则返回[],这里的id,为第几张图片,从0开始:x,y为找到图的中心坐标+随机偏移 0 到 2 。
        x1 整形数:区域的左上X坐标
        y1 整形数:区域的左上Y坐标
        x2 整形数:区域的右下X坐标
        y2 整形数:区域的右下Y坐标
        img_name 字符串:
            图片名,可以是多个图片,比如"test.png|test2.png|test3.png,要用"|"隔开；图片的路径和名字不能有中文,比如"1.png,test2.png"
        sim 浮点数:
            相似度,取值范围0.1-1.0
        mc:
            布尔值,True或False、1或0 ,默认False,为True或1时返回找到的多个坐标,否则只返回找到的第一个坐标
        drag:
            是否在找到的位置画图并显示,默认不画
            drag==1时画图并显示，彩色图片
            drag==2时画图并显示，过滤颜色后的图片
            drag==3时画图并显示，过滤颜色后的灰度图片
            drag==4时画图并显示，过滤颜色后的二值化图片
        delta_color：
            hsv空间的过滤色彩范围
        add_offset:
            是否在找图结果加上随机偏移0~2
        返回值：[[0, 338, 232, 320, 210], [0, 339, 332, 321, 310], [0, 338, 431, 321, 410], [0, 337, 531, 320, 510]]
            在返回的多个坐标中：
                每个列表代表找到的一个位置,arr[i][0]代表img_name中的第一张图,arr[i][1]代表img_name中的第二张图
                arr[0][1]arr[0][2]为找到图片的中心（加了随机偏移+2)坐标;arr[0][3]arr[0][4]为找到图片的左上角的坐标
        """
        screenshot_np = None
        start_time = timeit.default_timer()  # 获取当前时间作为开始时间
        # 初始化一个列表来存放返回结果
        self.arr_ret = []
        # 打印截图路径
        if drag is not None:
            logger.info(f"打印大图路径:{self.path}")
        # 指定截图区域的大小
        try:

            # 如果指定了路径，读取路径中的图片
            if self.path is not None:
                if drag is not None:
                    logger.info("读取路径中的图片")
                # 读取图片，默认读取是BGR格式
                screenshot_np = cv2.imread(self.path)
                # 这里用做画出找到位置显示的图片
                self.screenshot_show_image = screenshot_np  # 转为灰度图像  # self.target_image = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
            elif img_numpy is not None:
                screenshot_np = img_numpy[y1:y2, x1:x2]
                self.screenshot_show_image = screenshot_np

            elif self.hwnd is not None:
                screenshot_np = Capture(self.hwnd, 0, 0, 1067, 600)
                screenshot_np = screenshot_np[y1:y2, x1:x2]
                if drag is not None:
                    logger.info("保存到内存中")
                # 这里用做画出找到位置显示的图片
                self.screenshot_show_image = screenshot_np
            elif self.VNC is not None:
                logger.info("VNC截图")
                screenshot_np = self.VNC.capture()[0:600, 0:1067]
                # 这里用做画出找到位置显示的图片
                self.screenshot_show_image = screenshot_np

                # 转为灰度图像  # self.target_image = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)

        except Exception as ee:
            if drag is not None:
                logger.info(f"截图或保存失败: {ee}")
            return self.arr_ret
        # 将图像从BGR转换到HSV
        hsv_image = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2HSV)

        # 定义HSV颜色范围
        lower_color = np.array(delta_color[0])
        upper_color = np.array(delta_color[1])

        # 创建一个掩码来只选择落在指定颜色范围内的像素
        mask = cv2.inRange(hsv_image, lower_color, upper_color)

        # 使用掩码从原始BGR图像中提取颜色范围内的像素
        color_filtered_image = cv2.bitwise_and(screenshot_np, screenshot_np, mask=mask)

        # 转换提取的图像到灰度空间（如果模板是灰度的）
        gray_filtered_image = cv2.cvtColor(color_filtered_image, cv2.COLOR_BGR2GRAY)

        # 使用split()方法分割字符串看看传进几个图片
        img_name_array = img_name.split("|")

        for id, img_name in enumerate(img_name_array):

            # 输入图片名返回预加载的图片数据
            template_image = self.get_image(img_name)
            if template_image is None:
                logger.info(f"模板图片：{img_name}不存在")
                sys.exit(0)
            # 获取图片的尺寸
            h, w = template_image.shape

            # 打印图像尺寸信息
            # logger.info_if_enabled(f"模板图像template_image尺寸: 宽 {w}, 高 {h}")

            # 提取四个角上的像素值
            top_left = template_image[0, 0]  # 左上角
            top_right = template_image[-1, 0]  # 右上角
            bottom_left = template_image[0, -1]  # 左下角
            bottom_right = template_image[-1, -1]  # 右下角
            # 打印这四个像素值
            # logger.info(f"Top Left: {top_left}")
            # logger.info_if_enabled(f"Top Right: {top_right}")
            # logger.info_if_enabled(f"Bottom Left: {bottom_left}")
            # logger.info_if_enabled(f"Bottom Right: {bottom_right}")

            percentage = None

            # 对比这四个像素值，使用列表推导式和all函数来比较所有像素是否相同
            if all(np.array_equal(top_left, pixel) for pixel in [top_right, bottom_left, bottom_right]):
                # logger.info("四个角上的像素值——相同。")
                if top_left < 200:
                    # 如果四个角上的像素值相同，我们创建一个掩码，其中与左上角像素不同的区域被设置为0（黑色）
                    # 假设 templ 是一个形状为 (height, width, 3) 的三通道图像数组
                    # 假设 top_left 是一个形状为 (3,) 的数组，包含 RGB 三个通道的值

                    # 使用NumPy的向量化操作创建掩码
                    mask = (template_image != top_left).any(axis=-1).astype(np.uint8)

                    # 应用掩码到模板图像：将掩码中为0的像素在模板图像中对应位置设置为0
                    template_image[mask == 0] = 0  # 假设0是模板匹配中不会匹配的值

                else:
                    logger.info("如果是透明图请将透明部分用大漠综合工具设置为黑色，注意透明部分不能为白色")
            else:
                pass
                # logger.info("四个角上的像素值——不相同。")
                # 匹配图像
            if gray_filtered_image.shape[0] < h or gray_filtered_image.shape[1] < w:
                continue
            result = cv2.matchTemplate(gray_filtered_image, template_image, 5)

            # if percentage is not None:
            #     Sim = Sim - percentage

            # 找出匹配的区域
            loc = np.where(result >= sim)
            """如果多个符合相似度则返回多个的坐标，例如(array([210, 310, 310, 310, 410, 410, 410, 510, 510], dtype=int64),
             array([320, 319, 320, 321, 319, 320, 321, 319, 320], dtype=int64))前面的arrary()是y坐标,后面的arrary()是x坐标"""

            # 使用 loc 中的索引从 result 中获取对应的相似度的值
            values = result[loc[0], loc[1]]
            # logger.info_if_enabled(values)
            # 输出[0.9536035  0.9617588  0.96420443 0.9806926  0.95081407 0.9815434   0.9661575  0.9131024  0.95362145]

            # 初始化一个列表来存放匹配结果,这个列表是存放找到当前图片的坐标，每次迭代重新存放
            xy_array = []
            # 获取匹配的区域坐标
            for pt in zip(*loc[::-1]):
                xy_array.append(pt)

            xy_array = self.process_coordinates(xy_array)

            # 初始化计数器
            count = 0

            for xy in xy_array:

                # 生成随机坐标偏移量
                pard = random.randint(0, 2)

                # 如果最大相似度大于我们设定的值则把找到的坐标加入存放坐标的数组

                self.print_and_append_coordinates(img_name, values[count], xy, w, h, pard, x1, y1, id)

                count += 1

                if drag == 1:
                    self.screenshot_show_image = cv2.cvtColor(self.screenshot_show_image, cv2.COLOR_BGRA2BGR)
                    # 如果drag为True,则在目标图像上绘制矩形框标记模板位置
                    self.draw_rectangle_if_needed(self.screenshot_show_image, xy, w, h, drag)
                elif drag == 2:
                    self.screenshot_show_image = color_filtered_image
                    # 如果drag为True,则在目标图像上绘制矩形框标记模板位置
                    self.draw_rectangle_if_needed(self.screenshot_show_image, xy, w, h, drag)
                elif drag == 3:
                    self.screenshot_show_image = gray_filtered_image
                    # 如果drag为True,则在目标图像上绘制矩形框标记模板位置
                    self.draw_rectangle_if_needed(self.screenshot_show_image, xy, w, h, drag)
                # # 如果drag为True,则在目标图像上绘制矩形框标记模板位置
                # self.draw_rectangle_if_needed(self.screenshot_show_image, xy, w, h, drag)

                # 如果Multiple_coordinates为False，默认为False则只找到第一个坐标后退出循环
                if not mc:
                    break

            # 用全局变量called来判断是否启动多线程显示图片，默认为False
            if called is True:
                # 将图片数据放入队列中
                image_queue.put(self.screenshot_show_image)
            else:
                end_time = timeit.default_timer()  # 获取当前时间作为结束时间
                elapsed_time = end_time - start_time  # 计算代码块执行所花费的时间（秒)
                if drag == 1:
                    while True:
                        # 显示帧
                        cv2.imshow('image', self.screenshot_show_image)
                        # 等待按键
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                elif drag == 2:
                    while True:
                        # 显示帧
                        cv2.imshow('image', color_filtered_image)
                        # 等待按键
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                elif drag == 3:
                    while True:
                        # 显示帧
                        cv2.imshow('image', gray_filtered_image)
                        # 等待按键
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
            # 找到图片就不继续找后边的图了
            if len(loc) > 0:
                if not mc:
                    break

        return self.arr_ret

    def process_coordinates(self, coordinates):
        """
        从给定的坐标列表中移除与其他坐标点距离小于阈值的点。

        :param coordinates: 原始坐标列表
        :param threshold_distance: 相近的距离阈值
        :return: 不包含接近点的坐标列表
        """
        # 创建一个新列表来存储不接近的点
        threshold_distance = 10
        # 使用一个集合来存储需要删除的坐标的索引
        to_remove = set()

        # 遍历所有坐标点
        for i in range(len(coordinates)):
            # 遍历剩余的点，与当前点进行比较
            for j in range(i + 1, len(coordinates)):
                # 计算两点之间的距离
                distance = math.sqrt((coordinates[i][0] - coordinates[j][0]) ** 2 + (coordinates[i][1] - coordinates[j][1]) ** 2)

                # 如果距离小于阈值，则标记需要删除的点
                if distance < threshold_distance:
                    to_remove.add(j)

                    # 创建一个新列表，只包含未被标记为需要删除的点
        cleaned_coordinates = [coordinate for index, coordinate in enumerate(coordinates) if index not in to_remove]

        return cleaned_coordinates

    def print_and_append_coordinates(self, img_name, maxVal, maxLoc, template_width, template_height, pard, x1, y1, id):
        """
        打印匹配的图像信息，并将坐标信息添加到给定的数组中。

        参数:
        img_name: str, 匹配的图像名称
        maxVal: float, 相似度值
        maxLoc: tuple, 匹配图像在原图中的位置坐标 (x, y)
        template_width: int, 模板图像的宽度
        template_height: int, 模板图像的高度
        pard: int, 偏移量
        x1, y1: int, 坐标调整值
        arr_ret: list, 存储坐标信息的列表
        id: int, 标识信息

        返回值:
        None
        """
        center_x = maxLoc[0] + template_width / 2
        center_y = maxLoc[1] + template_height / 2
        adjusted_center_x = int(center_x + pard + x1)
        adjusted_center_y = int(center_y + pard + y1)
        logger.info_str = f"找到图片：{img_name},相似度：{maxVal};\n"

        if x1 != 0 or y1 != 0:
            logger.info_str += f"       屏幕上的绝对坐标xx: {maxLoc[0] + x1},y:{maxLoc[1] + y1};"
        else:
            logger.info_str += f"       屏幕上的绝对坐标x: {maxLoc[0]},y:{maxLoc[1]};"
        logger.info_str += f"加上按钮中心坐标后x: {adjusted_center_x},y: {adjusted_center_y}\n"

        self.arr_ret.append([id, adjusted_center_x, adjusted_center_y, maxLoc[0] + x1, maxLoc[1] + y1, maxVal, img_name])

    def get_mask(self, input_image, hsv_range, component=False):
        """
        根据给定的HSV颜色范围从输入图像中创建掩码。

        参数:
        input_image (numpy.ndarray): 输入的BGR图像。
        hsv_range (tuple): 包含两个numpy数组的元组，分别表示HSV颜色范围的下限和上限。

        返回:
        numpy.ndarray: 一个二值掩码，其中满足颜色条件的像素为255，不满足条件的像素为0。
        """
        hsv_lower = np.array(hsv_range[0])
        hsv_upper = np.array(hsv_range[1])

        # 转换到HSV色彩空间
        hsv_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2HSV)

        # 创建掩码
        mask = cv2.inRange(hsv_image, hsv_lower, hsv_upper)

        if component:
            # cv2.imshow('mask1', mask)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()
            # 定义一个膨胀核，这里我们使用一个3x3的矩形核作为示例
            kernel = np.ones((2, 5), np.uint8)

            # 对掩码进行膨胀
            dilated_mask = cv2.dilate(mask, kernel, iterations=1)

            # 获取连通组件的数量、标签、统计信息和质心
            num_components, labels, stats, centroids = cv2.connectedComponentsWithStats(dilated_mask)

            # 遍历所有组件（从1开始，因为0是背景）
            for i in range(1, num_components):
                # 获取当前连通组件的原始边界框信息
                left, top, width, height = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
                mask = mask[top:top + height, left:left + width]
                cv2.imshow('mask2', mask)
                cv2.waitKey(0)
                cv2.destroyAllWindows()

        return mask

    def draw_rectangle_if_needed(self, Color_Image, maxLoc, template_width, template_height, drag):
        """
        如果drag为True，则在目标图像上绘制矩形框标记模板位置。

        参数:
        Color_Image: numpy.ndarray, 目标图像，应该是一个有效的OpenCV图像（cv2.Mat或兼容的numpy数组）
        maxLoc: tuple, 匹配图像在原图中的位置坐标 (x, y)
        template_width: int, 模板图像的宽度
        template_height: int, 模板图像的高度
        drag: bool, 是否需要绘制矩形框

        返回值:
        None
        """
        if drag:
            x, y = maxLoc
            # 打印调试信息，确保Color_Image是numpy数组且形状合理
            logger.info(type(Color_Image))  # 应该输出 <class 'numpy.ndarray'>
            logger.info(Color_Image.shape)  # 应该输出图像的形状，如 (height, width, channels)
            # 打印将要绘制的矩形的坐标和颜色
            logger.info((x, y), (x + template_width, y + template_height), (0, 255, 0))
            # 在Color_Image上绘制矩形
            cv2.rectangle(Color_Image, (x, y), (x + template_width, y + template_height), (0, 255, 0), thickness=2)

    def get_goods(self, x, y, x1, y1, input_img, box_range, drag=None, delta_color=([0, 0, 0], [179, 255, 255])):
        input_img = input_img[y: y1, x:x1]
        max_image = self.get_mask(input_img, delta_color)
        # 定义一个膨胀核，这里我们使用一个3x3的矩形核作为示例
        kernel = np.ones((2, 5), np.uint8)
        # 对掩码进行膨胀
        dilated_mask = cv2.dilate(max_image, kernel, iterations=2)
        if drag:
            cv2.imshow("dilated_mask", dilated_mask)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        # 获取连通组件的数量、标签、统计信息和质心
        num_components, labels, stats, centroids = cv2.connectedComponentsWithStats(dilated_mask)
        min_w, max_w = box_range[0], box_range[1]
        min_h, max_h = box_range[2], box_range[3]
        data = []
        # 遍历所有组件（从1开始，因为0是背景）
        for i in range(1, num_components):

            # 获取当前连通组件的原始边界框信息
            left, top, width, height = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            if max_w >= width >= min_w and max_h >= height >= min_h:
                # 假设x1和y1是之前定义的偏移量
                adjusted_left = left + x  # 偏移后的左边界
                adjusted_top = top + y  # 偏移后的顶边界（注意：您代码中y + y1 - 15可能是一个特定的调整，这里我保持为y + y1）

                # 计算调整后的边界框坐标
                right = adjusted_left + width  # 右边界
                bottom = adjusted_top + height  # 底边界
                data.append((adjusted_left, adjusted_top, right, bottom))
        return data

    def is_colored(self, skill_img: np.ndarray, threshold=30):
        """
        判断图像是否为彩色的。阈值用于确定彩色和灰色的界限。
        """
        # 转换为灰度图像
        gray = cv2.cvtColor(skill_img, cv2.COLOR_BGR2GRAY)

        # 计算每个像素的绝对差值
        diff = cv2.absdiff(skill_img, cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
        diff_sum = np.sum(diff, axis=2)  # 求和RGB通道的差值
        # logger.info(np.mean(diff_sum))
        logger.info(f"mm-is_colored:{np.mean(diff_sum)}")
        # 判断差值是否大于阈值
        return np.mean(diff_sum) > threshold

    def show_image(self, image: np.array):
        cv2.imshow('show_image', image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


def convert_images_by_extension_opencv(source_extension, target_extension):
    """
    根据源扩展名和目标扩展名使用OpenCV转换图像格式。

    :param source_extension: 源图像的扩展名（例如，'.jpg'）。
    :param target_extension: 目标图像的扩展名（例如，'.png'）。
    # 示例用法
    # convert_images_by_extension_opencv('.jpg', '.png')
    """
    # 获取当前文件的绝对路径的目录部分
    base_dir = Path(os.path.dirname(os.path.abspath(__file__)))

    # 构建源目录路径，包含待转换的图像文件
    source_directory = base_dir / "Button_Mouse_Image" / "01"

    # 根据目标扩展名确定目标文件夹名称
    destination_directory = source_directory / f'converted_{target_extension[1:].lower()}'

    # 如果目标文件夹不存在，则创建它
    if not destination_directory.exists():
        destination_directory.mkdir(parents=True)

        # 遍历源目录中的所有文件
    for filename in os.listdir(source_directory):
        # 检查文件是否以源扩展名结尾
        if filename.lower().endswith(source_extension):
            # 构建源文件和目标文件的完整路径
            source_path = source_directory / filename
            destination_path = destination_directory / (os.path.splitext(filename)[0] + target_extension)

            try:
                # 打开图像文件
                img = cv2.imread(str(source_path), cv2.IMREAD_COLOR)

                if img is not None:
                    # 以目标格式保存图像
                    cv2.imwrite(str(destination_path), img)

                    # 打印转换进度
                    logger.info(f'已将 {source_path} 转换为 {destination_path}')
                else:
                    logger.info(f'无法打开文件 {source_path}')

            except Exception as ee:
                # 打印转换过程中的错误
                logger.info(f'转换 {source_path} 时出错: {ee}')

                # 打印转换完成的消息
    logger.info(f'所有以 {source_extension.upper()} 结尾的图像已转换为 {target_extension.upper()} 格式，并保存在 "{destination_directory}" 文件夹中。')


def is_bgr_image(array):
    # 检查数组是否为三维的
    if array.ndim != 3:
        return False

        # 检查最后一个维度的大小是否为3
    if array.shape[-1] != 3:
        return False

        # 检查数据类型是否为uint8
    if array.dtype != np.uint8:
        return False

        # 到这里，我们可以假设它是一个BGR图像，但这不是绝对的
    # 因为即使条件满足，也不能保证数据确实是图像数据
    # 或者图像数据确实是BGR格式的
    return True


# 线程函数，用于显示图片
def show_images_thread():
    # 创建一个名为'Image Display'的窗口
    cv2.namedWindow('img', cv2.WINDOW_AUTOSIZE)

    # 尝试设置窗口的位置（x, y）
    # 注意：这个方法可能不总是有效，取决于你的操作系统和GUI后端
    cv2.setWindowProperty('img', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
    cv2.moveWindow('img', 850, 0)  # 将窗口移动到屏幕上的(100, 100)位置
    while True:
        # 从队列中获取图片数据，如果队列为空则阻塞
        frame = image_queue.get()

        # 如果接收到特定的结束信号（例如None），则退出循环
        if frame is None:
            break

            # 显示图片
        cv2.imshow('img', frame)

        # 等待按键，如果是'q'则退出循环
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


def Test_Find_Mouse():
    # path=r"C:\Users\Administrator.DESKTOP-455QQ3O\Desktop\logi\mousceshi.png"

    # mm=MM(path)
    mm = MM()
    global called
    # 修改全局变量x的值
    called = True
    # 创建并启动显示图片的线程
    display_thread = threading.Thread(target=show_images_thread, daemon=True)
    display_thread.start()
    # 初始化一个空字符串
    result_string = ""

    # 遍历从1到10
    for i in range(1, 11):
        # 格式化迭代次数为两位数，不足两位时前面补零
        formatted_i = "{:04d}".format(i)
        # 在字符串后面添加格式化后的迭代次数和"|"，但最后一次迭代除外
        if i < 10:
            result_string += formatted_i + ".png|"
        else:
            result_string += formatted_i + ".png"

            # 打印结果字符串
    logger.info(result_string)

    logger.info("请在5秒内把鼠标移动到头像位置上")
    for j in range(1, 6):
        logger.info(f"{j}秒")
        sleep(1)

    for i in range(300):
        mm.FindPic(0, 64, 813, 679, result_string, 0.8, True, True)

        # sleep(0.001)

    # 发送结束信号到显示线程
    image_queue.put(None)

    # 等待显示线程结束
    display_thread.join()

    # 销毁所有OpenCV窗口
    cv2.destroyAllWindows()


def bgr_to_hex(bgr):
    # 确保bgr是一个包含三个整数的列表
    assert len(bgr) == 3, "bgr must be a list of three integers"
    assert all(0 <= c <= 255 for c in bgr), "color channel values must be between 0 and 255"

    # 使用format方法将每个十进制数转换为两位的16进制数
    # 注意这里的顺序是红色、绿色、蓝色（RGB）
    return "#{:02x}{:02x}{:02x}".format(bgr[2], bgr[1], bgr[0])


def calculate_hsv_limits_and_colors(hsv_color, hue_tolerance_deg=10, saturation_tolerance_pct=10, value_tolerance_pct=10):
    """
    计算给定HSV颜色的上下限，并转换成颜色输出。

    :param hsv_color: 一个包含色调、饱和度和值的元组 (h, s, v)，其中h是0-360的度数，s和v是0-255的整数。
    :param hue_tolerance_deg: 色调的容差值，单位为度数。
    :param saturation_tolerance_pct: 饱和度的容差值，单位为百分比。
    :param value_tolerance_pct: 值的容差值，单位为百分比。
    :return: 一个包含上下限HSV颜色对应的16进制颜色代码的元组 ((lower_color, upper_color))。
    """
    hue, saturation, value = hsv_color
    hue_tolerance = hue_tolerance_deg
    saturation_tolerance = int(saturation * saturation_tolerance_pct / 100)
    value_tolerance = int(value * value_tolerance_pct / 100)

    # 计算上下限HSV值
    h_min = max(0, hue - hue_tolerance)
    h_max = min(360, hue + hue_tolerance)
    s_min = max(0, saturation - saturation_tolerance)
    s_max = min(255, saturation + saturation_tolerance)
    v_min = max(0, value - value_tolerance)
    v_max = min(255, value + value_tolerance)

    # 创建HSV颜色范围的下限和上限
    lower_color = np.array([h_min, s_min, v_min])
    upper_color = np.array([h_max, s_max, v_max])

    return lower_color, upper_color


def batch_deduct_background(input_directory, hsv_lower, hsv_upper, output_subfolder='processed'):
    """
    批量扣除图片背景的函数。

    参数:
    input_directory (str): 输入目录，包含原始图片。
    hsv_lower (np.array): HSV颜色空间的下限。
    hsv_upper (np.array): HSV颜色空间的上限。
    output_subfolder (str, 可选): 在输入目录下创建的用于保存处理后图片的文件夹名称。默认为'processed'。

    返回:
    None
    """
    # 检查输入目录是否存在
    if not os.path.exists(input_directory):
        logger.info(f"输入目录不存在: {input_directory}")
        return

        # 在输入目录下创建输出子文件夹
    output_directory = os.path.join(input_directory, output_subfolder)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

        # 遍历输入目录下的所有文件
    for filename in os.listdir(input_directory):
        # 忽略非图片文件
        if not filename.lower().endswith(('.bmp', '.jpg', '.jpeg', '.png', '.tiff', '.gif')):
            continue

            # 读取图片
        image_path = os.path.join(input_directory, filename)
        image = cv2.imread(image_path)
        logger.info(image_path)
        if image is None:
            logger.info(f"无法读取图像: {image_path}")
            continue

            # 将图像从BGR转换为HSV
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 创建掩码，以选取不在指定HSV范围内的颜色
        mask = cv2.inRange(hsv_image, hsv_lower, hsv_upper)
        # 对掩码取反，得到在指定HSV范围内的颜色
        mask_inverse = cv2.bitwise_not(mask)

        # 对原图像应用反向掩码，得到不包含指定颜色范围的图像
        result = cv2.bitwise_and(image, image, mask=mask_inverse)

        # # 显示结果
        # cv2.imshow('Image with Bounding Box', result)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        # break

        """
        下面代码主要用途是处理一个二值化的掩码图像（通常用于表示某种特定区域或对象的位置），并在另一个图像上绘制出这个掩码所定义的区域的边界框。以下是具体的步骤和用途：

        初始化坐标变量：定义四个变量来存储边界框的左上角和右下角的坐标。

        寻找边界框的坐标：

        从左到右扫描掩码图像，找到最左边的非零像素（值为255的像素）的列坐标。
        从上到下扫描掩码图像，找到最上边的非零像素的行坐标。
        从右到左扫描掩码图像，找到最右边的非零像素的列坐标。
        从下到上扫描掩码图像，找到最下边的非零像素的行坐标。
        验证边界框的有效性：确保找到了所有四个边界的坐标，即确保掩码图像中至少有一个连通区域。

        计算边界框的尺寸：根据找到的坐标，计算边界框的宽度和高度。

        绘制边界框：在另一个图像（image）上，使用OpenCV的rectangle函数绘制出绿色（BGR颜色空间中的(0, 255, 0)）的矩形框。

        裁剪图像：使用计算出的边界框坐标，从原始图像（result）中裁剪出这个区域。

        保存结果：将裁剪后的图像保存到指定的输出目录。

        打印信息：打印出边界框的坐标、尺寸信息，以及裁剪后图像保存的路径。

        这个代码段通常用于图像处理任务中，比如对象检测、图像分割等，其中掩码图像用于指示感兴趣的区域或对象的位置，而另一个图像则可能是原始图像或其他需要标注的图像。
        通过这段代码，用户可以快速地在图像上标注出掩码所定义的区域，并将这个区域单独保存或进行进一步的处理。
        """

        # 初始化坐标变量
        left_most = None  # 最左边的边界坐标
        top_most = None  # 最上边的边界坐标
        right_most = None  # 最右边的边界坐标
        bottom_most = None  # 最下边的边界坐标

        # 从左到右扫描找到最左边的1（即第一个非零像素）
        for col in range(mask_inverse.shape[1]):
            if np.any(mask_inverse[:, col] == 255):
                left_most = col
                break

                # 从上到下扫描找到最上边的1
        for row in range(mask_inverse.shape[0]):
            if np.any(mask_inverse[row, :] == 255):
                top_most = row
                break

                # 从右到左扫描找到最右边的1
        for col in range(mask_inverse.shape[1] - 1, -1, -1):
            if np.any(mask_inverse[:, col] == 255):
                right_most = col
                break

                # 从下到上扫描找到最下边的1
        for row in range(mask_inverse.shape[0] - 1, -1, -1):
            if np.any(mask_inverse[row, :] == 255):
                bottom_most = row
                break

                # 检查是否找到了有效的边界（即四个边界坐标都不为None）
        if left_most is not None and top_most is not None and right_most is not None and bottom_most is not None:
            # 计算最大区域的坐标
            x, y, w, h = left_most, top_most, right_most - left_most + 1, bottom_most - top_most + 1

            # 在原图像或另一个图像上绘制矩形框（这里假设image变量已经定义并加载了图像）
            # image = cv2.imread('path_to_your_image.jpg')
            w1 = x + w  # 矩形框的右边界坐标
            h1 = y + h  # 矩形框的下边界坐标
            cv2.rectangle(image, (x, y), (w1, h1), (0, 255, 0), 2)  # 绘制绿色矩形框，线宽为2

            logger.info((x, y), (w1, h1))  # 打印矩形框的坐标

            # 打印坐标信息
            logger.info(f"Bounding Box: ({x}, {y}), Width: {w}, Height: {h}")

            # 裁剪四个角都是同一个颜色的位置图片
            result = result[y:h1, x - 1:w1]  # 使用计算出的坐标裁剪图像
        else:
            logger.info("No region found with mask value 1.")  # 如果没有找到值为1的区域，则打印提示信息

        # 保存结果图像到输出目录
        output_image_path = os.path.join(output_directory, filename)  # 构建输出图像的完整路径
        cv2.imwrite(output_image_path, result)  # 保存裁剪后的图像到指定路径

        logger.info(f"处理完成并保存到: {output_image_path}")  # 打印保存完成的消息及文件路径

        # # 显示结果  # cv2.imshow('Image with Bounding Box', result)  # cv2.waitKey(0)  # cv2.destroyAllWindows()  # break


def get_color_at_point(image_path, x, y):
    """
    读取图片，将其转为HSV空间，并获取指定坐标点的颜色。

    参数:
    image_path: 图片的路径
    x: 目标点的x坐标
    y: 目标点的y坐标

    返回:
    一个包含HSV颜色值的元组 (H, S, V)
    """
    # 读取图片
    image = cv2.imread(image_path)

    # 检查图片是否正确读取
    if image is None:
        raise ValueError("无法读取图片")

        # 将图片从BGR空间转为HSV空间
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 获取指定坐标点的颜色
    color = hsv_image[y, x]

    # 返回HSV颜色值
    return color


if __name__ == '__main__':
    mm = MM()
    # results = mm.screenshot_OCR_str(348, 466, 388, 479, '0.bmp|1.bmp|2.bmp|3.bmp|4.bmp|5.bmp|6.bmp|7.bmp|8.bmp|9.bmp', 0.9, get_colour=([62, 130, 159], [65, 141, 163]))
    time.sleep(5)
    results = mm.screenshot_OCR_str(878, 569, 926, 593, '0.png|1.png|2.png|3.png|4.png|5.png|6.png|7.png|8.png|9.png', 0.9, get_colour=([0, 0, 0], [0, 0, 255]))

    logger.info(results)
    pass
