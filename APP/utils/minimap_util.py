#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np

from core.common import map_pos_info
from utils.cv_recognizer import my_imread
from utils.logging_setup import logger
from utils.screenshot_util import screenshot_util
from root_dir import root_path


class MiniMapUtil:
    def __init__(self):
        self.minimap_image = None
        self.minimap_name = None
        self.hero_template = my_imread(root_path + "/res/map_hero.png")
        self.special_room_template = my_imread(root_path + "/res/map_special_room.png")
        self.boss_template = my_imread(root_path + "/res/map_boss.png")
        self.query_template = my_imread(root_path + "/res/map_query.png")
        self.query_template1 = my_imread(root_path + "/res/map_query1.png")
        self.elite_template = my_imread(root_path + "/res/map_elite.png")
        self.minimap = {
            "德洛斯矿山外围": {
                "width": 126, "height": 54, "row": 7, "col": 3
            },
            "流雨瀑布": {
                "width": 126, "height": 54, "row": 7, "col": 3
            },
            "风暴幽城": {
                "width": 108, "height": 54, "row": 6, "col": 3
            },
            "风暴逆鳞普通": {
                "width": 72, "height": 36, "row": 4, "col": 2
            },
            "海伯伦的预言所": {
                "width": 90, "height": 72, "row": 5, "col": 4
            },
            "深渊：终末崇拜者": {
                "width": 126, "height": 54, "row": 7, "col": 3
            },
            "深渊：最终调律者": {
                "width": 126, "height": 54, "row": 7, "col": 3
            },
            "跌宕群岛": {
                "width": 126, "height": 54, "row": 7, "col": 3
            },
            "妖气追踪": {
                "width": 126, "height": 54, "row": 7, "col": 3
            },
            "生命巡礼": {
                "width": 144, "height": 90, "row": 8, "col": 5
            },
            "怀纳千海之天": {
                "width": 144, "height": 90, "row": 8, "col": 5
            },
            "通用": {
                "width": 162, "height": 90, "row": 9, "col": 5
            },
        }

    def min_map_capture(self, map_name):
        """
        截取小地图图片
        :param map_name:
        :return:
        """
        m = map_pos_info.get(map_name)
        min_map = None
        if m:
            # min_map = Capture(hwnd, m["x1"], m["y1"], m["x2"], m["y2"])
            logger.info(f"开始截小地图")
            min_map = screenshot_util.get_game_screenshot()[m["y1"]:m["y2"], m["x1"]:m["x2"]]
            # logger.info(f"截图用时：{time.time() - st}")
            # game_image = Capture(hwnd, 0, 0, 1067, 600)
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
        if self.minimap_name == '流雨瀑布':
            map_opencv = im_opencv[48:48 + 54, 1067 - 6 - 126:1067 - 6]
        elif self.minimap_name == '风暴幽城':
            map_opencv = im_opencv[48:48 + 54, 1067 - 6 - 108:1067 - 6]
        elif self.minimap_name == '风暴逆鳞普通':
            map_opencv = im_opencv[48:48 + 54, 1067 - 6 - 108:1067 - 6]
            # map_opencv = im_opencv[48:48 + 36, 1280 - 6 - 72:1280 - 6]
        elif self.minimap_name == '德洛斯矿山外围':
            map_opencv = im_opencv[52:52 + 54, 1067 - 12 - 126:1067 - 12]
        elif self.minimap_name == '跌宕群岛':
            map_opencv = im_opencv[52:52 + 54, 1067 - 12 - 126:1067 - 12]
        elif self.minimap_name == '妖气追踪':
            map_opencv = im_opencv[52:52 + 54, 1067 - 12 - 126:1067 - 12]
        elif self.minimap_name == '通用':
            map_opencv = im_opencv[52:52 + 90, 1067 - 12 - 162:1067 - 12]
        else:
            map_opencv = im_opencv[48:48 + 54, 1067 - 6 - 126:1067 - 6]

        self.minimap_image = map_opencv

    def get_player_room_id(self, im_opencv):
        """
        获取当前人物所在的房间号
        :param im_opencv:
        :return:
        """

        self.get_mimi_map_img(im_opencv)
        xylist = self.template_match(self.hero_template, delta_color=([100, 0, 0], [124, 255, 255]), drag=2)
        has_special_room = False
        if xylist:
            room_id = self.compute_room_id(xylist[0][0], xylist[0][1])
            return room_id, has_special_room
        else:
            return None, has_special_room

    def get_boss_room_id(self, im_opencv):
        self.get_mimi_map_img(im_opencv)
        xylist = self.template_match(self.boss_template, delta_color=([0, 0, 0], [12, 255, 255]))
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
        xylist = self.template_match(self.elite_template, delta_color=([20, 0, 0], [21, 255, 255]))
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
            color_filtered_image = cv2.bitwise_and(self.minimap_image, self.minimap_image, mask=mask)
            color_filtered_image2 = cv2.bitwise_and(min_image, min_image, mask=mask2)

            # 转换提取的图像到灰度空间（如果模板是灰度的）
            gray_filtered_image = cv2.cvtColor(color_filtered_image, cv2.COLOR_BGR2GRAY)
            gray_filtered_image2 = cv2.cvtColor(color_filtered_image2, cv2.COLOR_BGR2GRAY)
            # 模板匹配用
            image = gray_filtered_image
            template_image = gray_filtered_image2

            # 二值化目标图片
            ret, image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            ret, template_image = cv2.threshold(template_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            # 转换提取的图像到灰度空间（如果模板是灰度的）
            image = cv2.cvtColor(self.minimap_image, cv2.COLOR_BGR2GRAY)
            template_image = cv2.cvtColor(min_image, cv2.COLOR_BGR2GRAY)

        # # 给一个图片数据，以防报错
        # template_image = min_image
        #
        # # 转换提取的图像到灰度空间（如果模板是灰度的）
        # template_image = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
        # if delta_color:
        #
        #     # 获取图片的尺寸
        #     h, w = template_image.shape
        #
        #     # 打印图像尺寸信息
        #     # my_print(f"模板图像template_image尺寸: 宽 {w}, 高 {h}")
        #
        #     # 提取四个角上的像素值
        #     top_left = template_image[0, 0]  # 左上角
        #     top_right = template_image[-1, 0]  # 右上角
        #     bottom_left = template_image[0, -1]  # 左下角
        #     bottom_right = template_image[-1, -1]  # 右下角
        #     # 打印这四个像素值
        #     if drag is not None:
        #         print(f"Top Left: {top_left}")
        #     # print(f"Top Left: {top_left}")
        #     # my_print(f"Top Right: {top_right}")
        #     # my_print(f"Bottom Left: {bottom_left}")
        #     # my_print(f"Bottom Right: {bottom_right}")
        #
        #     # percentage = None
        #
        #     # 对比这四个像素值，使用列表推导式和all函数来比较所有像素是否相同
        #     if all(np.array_equal(top_left, pixel) for pixel in [top_right, bottom_left, bottom_right]):
        #         # print("四个角上的像素值——相同。")
        #         if top_left < 200:
        #             # 如果四个角上的像素值相同，我们创建一个掩码，其中与左上角像素不同的区域被设置为0（黑色）
        #             # 假设 templ 是一个形状为 (height, width, 3) 的三通道图像数组
        #             # 假设 top_left 是一个形状为 (3,) 的数组，包含 RGB 三个通道的值
        #
        #             # 使用NumPy的向量化操作创建掩码
        #             mask = (template_image != top_left).any(axis=-1).astype(np.uint8)
        #
        #             # 应用掩码到模板图像：将掩码中为0的像素在模板图像中对应位置设置为0
        #             template_image[mask == 0] = 0  # 假设0是模板匹配中不会匹配的值
        #
        #             if delta_color:
        #                 # 二值化模板 匹配用
        #                 ret, template_image = cv2.threshold(template_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        #
        #         else:
        #             if drag is not None:
        #                 print("如果是透明图请将透明部分用大漠综合工具设置为黑色，注意透明部分不能为白色")
        #     else:
        #         if drag is not None:
        #             print("四个角上的像素值——不相同。")  # 匹配图像
        if drag:
            cv2.imshow('image', image)
            # if cv2.waitKey(0) & 0xFF == ord('q'):
            #     cv2.destroyWindow()
            cv2.imshow('template_image', template_image)
            if cv2.waitKey(0) & 0xFF == ord('q'):
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
        # print(xy_array)
        # # 找到匹配结果中的最小值和最大值及其位置
        # min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        # print(f"找到匹配结果中的最小值和最大值及其位置:{min_val, max_val, min_loc, max_loc}")
        # if drag is not None:
        #     print(f"找到匹配结果中的最小值和最大值及其位置:{min_val, max_val, min_loc, max_loc}")
        # 如果最大值小于0.7，则认为匹配度不够高，返回None
        # if max_val < 0.8:
        #     return None, None
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
        # x, y = list(max_loc)
        # # 获取模板图像的高度和宽度
        # hero_h, hero_w = min_image.shape[:2]
        # # 计算并返回模板图像中心在小地图中的坐标
        # # 这里将模板的左上角坐标转换为中心坐标，因为模板匹配找到的是左上角的位置
        # x = x + hero_w / 2
        # y = y + hero_h / 2
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
        # 统一判断：只要是支持的地图，就执行通用计算逻辑
        if self.minimap_name in self.minimap:
            # 获取当前地图的配置（避免重复字典查找，优化性能）
            map_config = self.minimap[self.minimap_name]
            # 计算单个网格的宽高
            width = map_config['width'] / map_config['row']
            height = map_config['height'] / map_config['col']
            # 坐标转网格索引
            row = int(x // width)
            column = int(y // height)
            # 赋值房间ID
            room_id = (column, row)
        return room_id


def find_images(folder_path, extensions=('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')):
    """
    查找给定文件夹内的所有图片文件。

    :param folder_path: 文件夹路径
    :param extensions: 要查找的图片文件扩展名列表
    :return: 图片文件名列表
    """
    images = []
    for root, dirs, files in os.walk(folder_path):
        print(root)
        print(files)
        for file in files:
            if os.path.splitext(file)[1].lower() in extensions:
                images.append(os.path.join(root, file))
    return images


miniMapUtil = MiniMapUtil()

if __name__ == '__main__':
    # time.sleep(1)
    # # miniMapUtil.set_minimap_name("流雨瀑布")
    # miniMapUtil.set_minimap_name("风暴幽城")
    # screenshot_util.init_game_hwnd()
    # game_image = screenshot_util.get_game_screenshot()
    # miniMapUtil.get_mimi_map_img(game_image)
    # # cv2.imwrite("query.png", miniMapUtil.minimap_image[36:54, 18:36])
    # # print(miniMapUtil.minimap_image.shape)
    # cv2.imshow('windows', miniMapUtil.minimap_image)
    # if cv2.waitKey(0) & 0xFF == ord('q'):
    #     cv2.destroyWindow()
    # print(miniMapUtil.get_player_room_id(game_image))
    # print(miniMapUtil.get_boss_room_id(game_image))
    # print(miniMapUtil.get_query_room_id(game_image))
    # print(miniMapUtil.get_elite_room_id(game_image))
    # print(type(miniMapUtil.get_boss_room_id(game_image)))
    # # 读取图片然后截取小地图图片
    # folder_path = r'D:\dnf-ai-master-fengbao\imgs'
    # images = find_images(folder_path)
    # print(images)
    # m = map_pos_info.get("流雨瀑布")
    # for img_path in images:
    #     image = cv2.imread(img_path)
    #     img = image[m["y1"]:m["y2"], m["x1"]:m["x2"]]
    #     # 替换路径中的 'imgs' 为 'new_imgs'
    #     replaced_path = img_path.replace('imgs', "new_imgs")
    #     cv2.imwrite(replaced_path,img)

    import os
    import cv2
    import hashlib


    def image_hash(image_path):
        """ 计算图片的哈希值（使用SHA-256） """
        # 使用OpenCV读取图片
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        # 将图片数据转换为二进制字符串
        img_data = img.tobytes()
        # 计算SHA-256哈希值
        hash_obj = hashlib.sha256(img_data)
        return hash_obj.hexdigest()


    def remove_duplicate_images(folder_path):
        """ 遍历文件夹并删除重复的图片 """
        image_hashes = {}
        duplicates_to_delete = []

        # 遍历文件夹中的所有文件
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
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


    folder_path = r'D:\dnf-ai-master-fengbao\new_imgs'
    remove_duplicate_images(folder_path)
