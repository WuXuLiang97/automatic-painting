import os
import time
import cv2
from loguru import logger
import numpy as np
from utils.common.string import is_chinese
from root_dir import root_path

def read_from_path(my_path):
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
        if filename.lower().endswith((".png", ".bmp")):
            # if filename.lower().endswith('.png'):
            # 拼接文件路径
            img_file_path = os.path.join(file_path, filename)
            # 使用OpenCV库读取图片
            image_BGR = read_from_path(img_file_path)

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
