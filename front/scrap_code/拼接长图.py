# -*- coding: utf-8 -*-
import cv2
import os
import numpy as np
import re


def merge_images_with_cv2(folder_path, output_path):
    """使用OpenCV按文件名顺序垂直拼接图片"""
    # 获取图片文件列表
    image_files = [f for f in os.listdir(folder_path)
                   if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]

    if not image_files:
        print("未找到图片文件")
        return

    # 改进的自然排序算法（处理数字部分）
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split(r'(\d+)', s)]

    image_files.sort(key=natural_sort_key)

    # 读取所有图片
    images = []
    for filename in image_files:
        img_path = os.path.join(folder_path, filename)
        img = cv2.imread(img_path)
        if img is not None:
            images.append(img)
        else:
            print(f"无法读取图片: {filename}")

    if not images:
        print("没有可处理的图片")
        return

    # 获取最大宽度和总高度
    max_width = max(img.shape[1] for img in images)
    total_height = sum(img.shape[0] for img in images)

    # 创建空白画布（白色背景）
    result = np.ones((total_height, max_width, 3), dtype=np.uint8) * 255

    # 垂直拼接图片（居中放置）
    current_height = 0
    for img in images:
        h, w = img.shape[:2]
        # 计算居中偏移量
        x_offset = (max_width - w) // 2
        result[current_height:current_height + h, x_offset:x_offset + w] = img
        current_height += h

    # 保存结果
    success = cv2.imwrite(output_path, result)
    if success:
        print(f"拼接完成，保存至: {output_path}")
    else:
        print(f"保存失败，请检查输出路径: {output_path}")


# 使用示例
folder_path = r"C:/Users/Administrator/Desktop/202131423"  # 替换为实际路径
output_path = r"C:/Users/Administrator/Desktop/202131423/aa.png"  # 替换为实际路径
merge_images_with_cv2(folder_path, output_path)
