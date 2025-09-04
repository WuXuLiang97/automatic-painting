#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
from core.common import map_pos_info
from utils.log.logging_setup import logger
from global_fields import screenshot_util
from static_fields import (
    RECT_MINMAPS
)


class MiniMapUtil:
    def __init__(self):
        self.minimap_image = None
        self.minimap_name = None

    def min_map_capture(self, map_name):
        """
        截取小地图图片
        :param map_name:
        :return:
        """
        m = map_pos_info.get(map_name)
        min_map = None
        if m:
            logger.info(f"开始截小地图")
            min_map = screenshot_util.get_game_screenshot()[
                m["y1"] : m["y2"], m["x1"] : m["x2"]
            ]

            logger.info(f"小地图截图完毕")
        else:
            print("map_pos_info无小地图数据，请检查common.py文件")
        return min_map

    def set_minimap_name(self, map_name):
        self.minimap_name = map_name

    def get_mimi_map_img(self, im_opencv):
        """
        获取小地图
        :param im_opencv:
        :return:
        """
        y1, y2, x1, x2 = RECT_MINMAPS[self.minimap_name]
        self.minimap_image = im_opencv[y1:y2, x1:x2]

    def get_player_room_id(self, im_opencv):
        """
        获取当前人物所在的房间号
        :param im_opencv:
        :return:
        """

        self.get_mimi_map_img(im_opencv)
        xylist = self.template_match(
            self.hero_template, delta_color=([100, 0, 0], [124, 255, 255]), drag=2
        )
        has_special_room = False
        if xylist:
            room_id = self.compute_room_id(xylist[0][0], xylist[0][1])
            return room_id, has_special_room
        else:
            return None, has_special_room

    def get_boss_room_id(self, im_opencv):
        self.get_mimi_map_img(im_opencv)
        xylist = self.template_match(
            self.boss_template, delta_color=([0, 0, 0], [12, 255, 255])
        )
        if xylist:
            return self.compute_room_id(xylist[0][0], xylist[0][1])
        else:
            return None

    def get_query_room_id(self, im_opencv):
        """
        获取问号房间id
        :param im_opencv:
        :return:
        """

        xylist = self.template_match(self.query_template)
        if xylist:
            return self.compute_room_id(xylist[0][0], xylist[0][1])
        else:
            xylist = self.template_match(self.query_template1)
            if xylist:
                return self.compute_room_id(xylist[0][0], xylist[0][1])
        return None

    def get_elite_room_id(self, im_opencv):
        """
        获取精英房间id
        :param im_opencv:
        :return:
        """
        self.get_mimi_map_img(im_opencv)
        xylist = self.template_match(
            self.elite_template, delta_color=([20, 0, 0], [21, 255, 255])
        )
        if xylist:
            xylist1 = []
            for xy in xylist:
                x, y = xy
                xy1 = self.compute_room_id(x, y)
                xylist1.append(xy1)
            return xylist1
        else:
            return None

    def template_match(self, min_image, delta_color=None, drag=None):
        """
        使用模板匹配来在小地图中查找给定图像的位置。

        Args:
            min_image (numpy.ndarray): 需要在小地图中查找的模板图像。
            :param min_image:
            :param drag:
            :param delta_color:

        Returns:
            tuple 或 None: 如果找到匹配项且匹配度足够高（> 0.7），则返回模板图像在小地图中的中心坐标(x, y)。
                           如果没有找到足够匹配的项，则返回(None, None)。

        """
        if delta_color:
            # 将图像从BGR转换到HSV
            hsv_image = cv2.cvtColor(self.minimap_image, cv2.COLOR_BGR2HSV)
            # 将图像从BGR转换到HSV
            hsv_image2 = cv2.cvtColor(min_image, cv2.COLOR_BGR2HSV)

            # 定义HSV颜色范围
            lower_color = np.array(delta_color[0])
            upper_color = np.array(delta_color[1])

            # 创建一个掩码来只选择落在指定颜色范围内的像素
            mask = cv2.inRange(hsv_image, lower_color, upper_color)
            mask2 = cv2.inRange(hsv_image2, lower_color, upper_color)

            # 使用掩码从原始BGR图像中提取颜色范围内的像素
            color_filtered_image = cv2.bitwise_and(
                self.minimap_image, self.minimap_image, mask=mask
            )
            color_filtered_image2 = cv2.bitwise_and(min_image, min_image, mask=mask2)

            # 转换提取的图像到灰度空间（如果模板是灰度的）
            gray_filtered_image = cv2.cvtColor(color_filtered_image, cv2.COLOR_BGR2GRAY)
            gray_filtered_image2 = cv2.cvtColor(
                color_filtered_image2, cv2.COLOR_BGR2GRAY
            )
            # 模板匹配用
            image = gray_filtered_image
            template_image = gray_filtered_image2

            # 二值化目标图片
            ret, image = cv2.threshold(
                image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            ret, template_image = cv2.threshold(
                template_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
        else:
            # 转换提取的图像到灰度空间（如果模板是灰度的）
            image = cv2.cvtColor(self.minimap_image, cv2.COLOR_BGR2GRAY)
            template_image = cv2.cvtColor(min_image, cv2.COLOR_BGR2GRAY)

        if drag:
            cv2.imshow("image", image)
            # if cv2.waitKey(0) & 0xFF == ord('q'):
            #     cv2.destroyWindow()
            cv2.imshow("template_image", template_image)
            if cv2.waitKey(0) & 0xFF == ord("q"):
                cv2.destroyWindow()
        # 模板匹配：使用cv2.matchTemplate函数在小地图中搜索min_image模板
        result = cv2.matchTemplate(image, template_image, cv2.TM_CCOEFF_NORMED)
        # 找出匹配的区域
        loc = np.where(result >= 0.7)
        # 获取匹配的区域坐标
        # 初始化一个列表来存放匹配结果,这个列表是存放找到当前图片的坐标，每次迭代重新存放
        xy_array = []
        for pt in zip(*loc[::-1]):
            xy_array.append(pt)
        #     # 获取匹配到的模板左上角坐标
        res1 = []
        for xy in xy_array:
            x, y = xy
            # 获取模板图像的高度和宽度
            hero_h, hero_w = min_image.shape[:2]
            # 计算并返回模板图像中心在小地图中的坐标
            # 这里将模板的左上角坐标转换为中心坐标，因为模板匹配找到的是左上角的位置
            x = x + hero_w / 2
            y = y + hero_h / 2
            res1.append((x, y))
        return res1

    def compute_room_id(self, x, y):
        """
        根据小地图中的坐标(x, y)计算并返回房间ID。

        房间ID是通过将坐标映射到房间网格的行和列，并将其转换为字符串格式（列号-行号）来确定的。
        该方法仅在小地图名称为"流雨瀑布"时有效。

        Args:
            x (int): 坐标点的x值（横坐标）。
            y (int): 坐标点的y值（纵坐标）。

        Returns:
            str 或 None: 如果小地图名称为"流雨瀑布"，则返回计算得到的房间ID（列号-行号格式的字符串）。
                         否则，返回None。
        """
        room_id = None
        # 检查小地图名称是否为"流雨瀑布"
        if self.minimap_name == "流雨瀑布":
            # 从minimap字典中获取流雨瀑布小地图的宽度、高度、行数和列数
            width = (
                self.minimap[self.minimap_name]["width"]
                / self.minimap[self.minimap_name]["row"]
            )
            height = (
                self.minimap[self.minimap_name]["height"]
                / self.minimap[self.minimap_name]["col"]
            )
            # 将x和y坐标转换为房间网格的行和列索引
            # 注意：这里假设x和y坐标是像素值，需要根据网格大小进行转换
            row = int(x // width)  # 使用int进行向下取整，因为索引应该是整数
            column = int(y // height)  # 同上
            # 构造并返回房间ID（列号,行号）
            room_id = column, row
            # 返回计算得到的房间ID或None
        elif self.minimap_name == "风暴幽城":
            # 从minimap字典中获取流雨瀑布小地图的宽度、高度、行数和列数
            width = (
                self.minimap[self.minimap_name]["width"]
                / self.minimap[self.minimap_name]["row"]
            )
            height = (
                self.minimap[self.minimap_name]["height"]
                / self.minimap[self.minimap_name]["col"]
            )
            # 将x和y坐标转换为房间网格的行和列索引
            # 注意：这里假设x和y坐标是像素值，需要根据网格大小进行转换
            row = int(x // width)  # 使用int进行向下取整，因为索引应该是整数
            column = int(y // height)  # 同上
            # # 构造并返回房间ID（列号-行号）
            # room_id = str(column) + "-" + str(row)
            # 构造并返回房间ID（列号,行号）
            room_id = column, row
            # 返回计算得到的房间ID或None
        elif self.minimap_name == "风暴逆鳞普通":
            # 从minimap字典中获取流雨瀑布小地图的宽度、高度、行数和列数
            width = (
                self.minimap[self.minimap_name]["width"]
                / self.minimap[self.minimap_name]["row"]
            )
            height = (
                self.minimap[self.minimap_name]["height"]
                / self.minimap[self.minimap_name]["col"]
            )
            # 将x和y坐标转换为房间网格的行和列索引
            # 注意：这里假设x和y坐标是像素值，需要根据网格大小进行转换
            row = int(x // width)  # 使用int进行向下取整，因为索引应该是整数
            column = int(y // height)  # 同上
            # # 构造并返回房间ID（列号-行号）
            # room_id = str(column) + "-" + str(row)
            # 构造并返回房间ID（列号,行号）
            room_id = column, row
            # 返回计算得到的房间ID或None
        elif self.minimap_name == "海伯伦的预言所":
            # 从minimap字典中获取流雨瀑布小地图的宽度、高度、行数和列数
            width = (
                self.minimap[self.minimap_name]["width"]
                / self.minimap[self.minimap_name]["row"]
            )
            height = (
                self.minimap[self.minimap_name]["height"]
                / self.minimap[self.minimap_name]["col"]
            )
            # 将x和y坐标转换为房间网格的行和列索引
            # 注意：这里假设x和y坐标是像素值，需要根据网格大小进行转换
            row = int(x // width)  # 使用int进行向下取整，因为索引应该是整数
            column = int(y // height)  # 同上
            # # 构造并返回房间ID（列号-行号）
            # room_id = str(column) + "-" + str(row)
            # 构造并返回房间ID（列号,行号）
            room_id = column, row
            # 返回计算得到的房间ID或None
        elif self.minimap_name == "德洛斯矿山外围":
            # 从minimap字典中获取流雨瀑布小地图的宽度、高度、行数和列数
            width = (
                self.minimap[self.minimap_name]["width"]
                / self.minimap[self.minimap_name]["row"]
            )
            height = (
                self.minimap[self.minimap_name]["height"]
                / self.minimap[self.minimap_name]["col"]
            )
            # 将x和y坐标转换为房间网格的行和列索引
            # 注意：这里假设x和y坐标是像素值，需要根据网格大小进行转换
            row = int(x // width)  # 使用int进行向下取整，因为索引应该是整数
            column = int(y // height)  # 同上
            # # 构造并返回房间ID（列号-行号）
            # room_id = str(column) + "-" + str(row)
            # 构造并返回房间ID（列号,行号）
            room_id = column, row
            # 返回计算得到的房间ID或None
        elif self.minimap_name == "跌宕群岛":
            # 从minimap字典中获取流雨瀑布小地图的宽度、高度、行数和列数
            width = (
                self.minimap[self.minimap_name]["width"]
                / self.minimap[self.minimap_name]["row"]
            )
            height = (
                self.minimap[self.minimap_name]["height"]
                / self.minimap[self.minimap_name]["col"]
            )
            # 将x和y坐标转换为房间网格的行和列索引
            # 注意：这里假设x和y坐标是像素值，需要根据网格大小进行转换
            row = int(x // width)  # 使用int进行向下取整，因为索引应该是整数
            column = int(y // height)  # 同上
            # # 构造并返回房间ID（列号-行号）
            # room_id = str(column) + "-" + str(row)
            # 构造并返回房间ID（列号,行号）
            room_id = column, row
        elif self.minimap_name == "妖气追踪":
            # 从minimap字典中获取流雨瀑布小地图的宽度、高度、行数和列数
            width = (
                self.minimap[self.minimap_name]["width"]
                / self.minimap[self.minimap_name]["row"]
            )
            height = (
                self.minimap[self.minimap_name]["height"]
                / self.minimap[self.minimap_name]["col"]
            )
            # 将x和y坐标转换为房间网格的行和列索引
            # 注意：这里假设x和y坐标是像素值，需要根据网格大小进行转换
            row = int(x // width)  # 使用int进行向下取整，因为索引应该是整数
            column = int(y // height)  # 同上
            # # 构造并返回房间ID（列号-行号）
            # room_id = str(column) + "-" + str(row)
            # 构造并返回房间ID（列号,行号）
            room_id = column, row
            # 返回计算得到的房间ID或None
        elif self.minimap_name == "通用":
            # 从minimap字典中获取流雨瀑布小地图的宽度、高度、行数和列数
            width = (
                self.minimap[self.minimap_name]["width"]
                / self.minimap[self.minimap_name]["row"]
            )
            height = (
                self.minimap[self.minimap_name]["height"]
                / self.minimap[self.minimap_name]["col"]
            )
            # 将x和y坐标转换为房间网格的行和列索引
            # 注意：这里假设x和y坐标是像素值，需要根据网格大小进行转换
            row = int(x // width)  # 使用int进行向下取整，因为索引应该是整数
            column = int(y // height)  # 同上
            # # 构造并返回房间ID（列号-行号）
            # room_id = str(column) + "-" + str(row)
            # 构造并返回房间ID（列号,行号）
            room_id = column, row
            # 返回计算得到的房间ID或None
        return room_id


miniMapUtil = MiniMapUtil()

if __name__ == "__main__":
    import os
    import cv2
    import hashlib

    def image_hash(image_path):
        """计算图片的哈希值（使用SHA-256）"""
        # 使用OpenCV读取图片
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        # 将图片数据转换为二进制字符串
        img_data = img.tobytes()
        # 计算SHA-256哈希值
        hash_obj = hashlib.sha256(img_data)
        return hash_obj.hexdigest()

    def remove_duplicate_images(folder_path):
        """遍历文件夹并删除重复的图片"""
        image_hashes = {}
        duplicates_to_delete = []

        # 遍历文件夹中的所有文件
        for filename in os.listdir(folder_path):
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                file_path = os.path.join(folder_path, filename)
                hash_value = image_hash(file_path)

                # 检查哈希值是否已存在
                if hash_value in image_hashes:
                    # 如果已存在，则添加当前文件到删除列表
                    duplicates_to_delete.append(file_path)
                else:
                    # 否则，保存文件路径和哈希值
                    image_hashes[hash_value] = file_path

                    # 删除重复的文件
        for file_path in duplicates_to_delete:
            os.remove(file_path)
            print(f"Deleted duplicate: {file_path}")

        print("Duplicates removal completed.")

        # 使用示例

    folder_path = r"D:\dnf-ai-master-fengbao\new_imgs"
    remove_duplicate_images(folder_path)
