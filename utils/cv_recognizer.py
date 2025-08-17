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

from time import sleep

import cv2
import numpy as np
import win32gui
from root_dir import root_path
from utils.logging_setup import logger

STOP_EVENT = threading.Event()

# 创建一个全局变量用来判断启动线程没有
called = False
# 创建一个队列用于存储图片数据
image_queue = queue.Queue()


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


# def get_hwnd():
#     dnf_hwnd = win32gui.FindWindow('地下城与勇士', '地下城与勇士：创新世纪')
#     if dnf_hwnd != 0:
#         logger.info("地下城与勇士：创新世纪窗口的句柄:", dnf_hwnd)
#     return dnf_hwnd
#
#
# try:
#     hwnd = get_hwnd()
#
# except Exception as e:
#     logger.info("update_settings_group_data:", e)
#     logger.info("完整堆栈：")
#     traceback.logger.info_exc()


class MM:
    def __init__(self, img_path=None, ):
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

    def screenshot_OCR_str(self, x1, y1, x2, y2, templates_dict, sim, get_colour=None, drag=None):
        """
        优化后的数字识别方法，专注于识别数字字符

        :param templates_dict: 字典格式的数字模板 {数字字符: [模板文件名列表]}
            示例: {'0': ['0_1.bmp', '0_2.bmp'], '1': ['1.bmp'], ...}
        """
        # 捕获指定区域的屏幕截图
        try:
            screenshot_np = self.VNC.capture()[0:600, 0:1067]
            if isinstance(screenshot_np, np.ndarray):
                logger.info("vnc_mm截图成功")
            else:
                logger.info("vnc_mm截图失败")
                return ''
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

        # 处理模板图像 - 支持每个数字多个模板
        templates = {}  # {数字字符: 模板图像列表}
        logger.info(f"开始加载模板...")

        for digit_char, filenames in templates_dict.items():
            logger.info(f"处理数字 '{digit_char}' 的模板")
            digit_templates = []

            for filename in filenames:
                try:
                    logger.info(f"  加载模板: {filename}")

                    # 加载模板图像
                    template_img = self.get_image(filename, color_space=get_colour)
                    if template_img is None:
                        logger.info(f"    警告: 模板文件 '{filename}' 未找到")
                        continue

                    # 预处理模板 - 只取第一个有效的连通组件
                    _, template_components = self.image_pretreatment(
                        template_img,
                        get_colour=get_colour,
                        drag=None
                    )

                    # 只取第一个有效组件（数字模板）
                    if template_components and template_components[0].size > 0:
                        digit_templates.append(template_components[0])
                        logger.info(f"    模板 '{filename}' 尺寸: {template_components[0].shape}")

                        # 调试显示
                        if drag is not None:
                            cv2.imshow(f'Template: {digit_char} - {filename}', template_components[0])
                            cv2.waitKey(1)  # 短暂显示
                    else:
                        logger.info(f"    警告: 模板 '{filename}' 未找到有效组件")
                except Exception as e:
                    logger.info(f"    处理模板 '{filename}' 时出错: {e}")

            if digit_templates:
                templates[digit_char] = digit_templates
                logger.info(f"  数字 '{digit_char}' 加载了 {len(digit_templates)} 个有效模板")
            else:
                logger.info(f"  警告: 数字 '{digit_char}' 未找到任何有效模板")

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
                cv2.waitKey(1)  # 短暂显示

            best_match = None
            best_similarity = 0

            # 与所有数字模板进行匹配
            for digit_char, digit_templates in templates.items():
                for template_idx, template_img in enumerate(digit_templates):
                    # 检查模板尺寸是否适合目标区域
                    if template_img.shape[0] > digit_region.shape[0] or template_img.shape[1] > digit_region.shape[1]:
                        # logger.info(f"  模板 '{digit_char}_{template_idx}' 太大 - 跳过")
                        continue

                    try:
                        # 调整模板尺寸以匹配目标区域（如果需要）
                        if template_img.shape != digit_region.shape:
                            resized_template = cv2.resize(template_img, (digit_region.shape[1], digit_region.shape[0]))
                            # logger.info(f"  调整模板 '{digit_char}_{template_idx}' 尺寸")
                        else:
                            resized_template = template_img

                        # 模板匹配
                        result = cv2.matchTemplate(digit_region, resized_template, cv2.TM_CCOEFF_NORMED)
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                        # logger.info(f"  匹配 '{digit_char}' (模板{template_idx}): 相似度 = {max_val:.4f}")

                        # 更新最佳匹配
                        if max_val > best_similarity:
                            best_similarity = max_val
                            best_match = digit_char

                            # 调试显示匹配结果
                            if drag is not None and max_val >= sim:
                                h, w = resized_template.shape
                                top_left = max_loc
                                bottom_right = (top_left[0] + w, top_left[1] + h)

                                # 创建带匹配框的副本
                                match_vis = digit_region.copy()
                                cv2.rectangle(match_vis, top_left, bottom_right, 128, 2)
                                cv2.imshow(f'Match: {digit_char} ({max_val:.2f})', match_vis)
                                cv2.waitKey(1)
                    except Exception as e:
                        logger.info(f"  匹配模板 '{digit_char}_{template_idx}' 时出错: {e}")

            # 保存有效匹配
            if best_match and best_similarity >= sim:
                logger.info(f"  最佳匹配: '{best_match}' (相似度 = {best_similarity:.4f})")
                recognized_digits.append(best_match)
            else:
                logger.info(f"  未找到有效匹配 (最高相似度 = {best_similarity:.4f})")

        # 返回识别结果
        result = ''.join(recognized_digits)
        logger.info(f"最终识别结果: '{result}'")

        # 关闭调试窗口
        if drag is not None:
            cv2.destroyAllWindows()

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
                    image = cv2.cvtColor(colored_image, cv2.COLOR_BGR2GRAY)
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
            cv2.imshow('binary_image', binary_image)
            cv2.waitKey(0)
            # cv2.imshow('Original', image)
            # cv2.waitKey(500)
            # cv2.imshow('Binary', binary_image)
            # cv2.waitKey(500)

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
                # 放宽尺寸限制（允许更小的组件）
                if w < 2 or h < 2:  # 仅过滤极小噪声（根据实际数字尺寸调整）
                    logger.info(f"  跳过小组件: {w}x{h}")
                    continue
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
                    cv2.waitKey(0)
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

            elif self.VNC is not None:
                logger.info("VNC截图")
                screenshot_np = self.VNC.capture()[0:600, 0:1067]
                if isinstance(screenshot_np, np.ndarray):
                    logger.info("vnc_mm截图成功")
                else:
                    logger.info("vnc_mm截图失败")
                    return self.arr_ret
                if screenshot_np is None:
                    logger.error("截图获取为空数组")
                    return self.arr_ret
                screenshot_np = screenshot_np[y1:y2, x1:x2]
                # 这里用做画出找到位置显示的图片
                self.screenshot_show_image = screenshot_np
                # 转为灰度图像  # self.target_image = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)

        except Exception as ee:
            if drag is not None:
                logger.info(f"截图或保存失败: {ee}")
            return self.arr_ret
        if screenshot_np is None:
            logger.error("截图获取为空数组")
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
        # print(f"x1:{x1}\ty1:{y1}")
        # adjusted_center_x = int(center_x + pard)
        # adjusted_center_y = int(center_y + pard)
        logger.info_str = f"找到图片：{img_name},相似度：{maxVal};\n"

        if x1 != 0 or y1 != 0:
            logger.info_str += f"       屏幕上的绝对坐标xx: {maxLoc[0] + x1},y:{maxLoc[1] + y1};"
        else:
            logger.info_str += f"       屏幕上的绝对坐标x: {maxLoc[0]},y:{maxLoc[1]};"
        logger.info_str += f"加上按钮中心坐标后x: {adjusted_center_x},y: {adjusted_center_y}\n"

        self.arr_ret.append([id, adjusted_center_x, adjusted_center_y, maxLoc[0] + x1, maxLoc[1] + y1, maxVal, img_name])

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
            logger.info(f"{(x, y), (x + template_width, y + template_height), (0, 255, 0)}")
            # 在Color_Image上绘制矩形
            cv2.rectangle(Color_Image, (x, y), (x + template_width, y + template_height), (0, 255, 0), thickness=2)

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


vnc_mm = MM()
if __name__ == '__main__':
    mm = MM()
