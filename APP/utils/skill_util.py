# -*- coding: utf-8 -*-

import cv2
import numpy as np

from core.capture import Capture
# from utils.cv_recognizer import hwnd
from utils.screenshot_util import screenshot_util
from utils.logging_setup import logger


class SkillUtil:
    def __init__(self):
        self.skill_region_w = 63
        self.skill_region_h = 218
        self.skill_width = int(self.skill_region_w / 2)
        self.skill_height = int(self.skill_region_h / 7)
        self.q = {"x1": 432, "y1": 532, "x2": 432 + self.skill_width, "y2": 532 + self.skill_height}
        self.w = {"x1": 432 + self.skill_width, "y1": 532, "x2": 432 + self.skill_width * 2, "y2": 532 + self.skill_height}
        self.e = {"x1": 432 + self.skill_width * 2, "y1": 532, "x2": 432 + self.skill_width * 3, "y2": 532 + self.skill_height}
        self.r = {"x1": 432 + self.skill_width * 3, "y1": 532, "x2": 432 + self.skill_width * 4, "y2": 532 + self.skill_height}
        self.t = {"x1": 432 + self.skill_width * 4, "y1": 532, "x2": 432 + self.skill_width * 5, "y2": 532 + self.skill_height}
        self.y = {"x1": 432 + self.skill_width * 5, "y1": 532, "x2": 432 + self.skill_width * 6, "y2": 532 + self.skill_height}
        self.ctrl = {"x1": 432 + self.skill_width * 6, "y1": 532, "x2": 432 + self.skill_width * 7, "y2": 532 + self.skill_height}
        self.a = {"x1": 432, "y1": 532 + self.skill_height, "x2": 432 + self.skill_width, "y2": 532 + self.skill_height * 2}
        self.s = {"x1": 432 + self.skill_width, "y1": 532 + self.skill_height, "x2": 432 + self.skill_width * 2, "y2": 532 + self.skill_height * 2}
        self.d = {"x1": 432 + self.skill_width * 2, "y1": 532 + self.skill_height, "x2": 432 + self.skill_width * 3, "y2": 532 + self.skill_height * 2}
        self.f = {"x1": 432 + self.skill_width * 3, "y1": 532 + self.skill_height, "x2": 432 + self.skill_width * 4, "y2": 532 + self.skill_height * 2}
        self.g = {"x1": 432 + self.skill_width * 4, "y1": 532 + self.skill_height, "x2": 432 + self.skill_width * 5, "y2": 532 + self.skill_height * 2}
        self.h = {"x1": 432 + self.skill_width * 5, "y1": 532 + self.skill_height, "x2": 432 + self.skill_width * 6, "y2": 532 + self.skill_height * 2}
        self.v = {"x1": 432 + self.skill_width * 6, "y1": 532 + self.skill_height, "x2": 432 + self.skill_width * 7, "y2": 532 + self.skill_height * 2}
        self.skill_dict = {"q": self.q, "w": self.w, "e": self.e, "r": self.r, "t": self.t, "y": self.y, "ctrl": self.ctrl, "a": self.a, "s": self.s, "d": self.d, "f": self.f, "g": self.g, "h": self.h, "v": self.v}
        self.skill_image_dict = {}  # 图片字典
        self.skill_1 = []  # 第一排
        self.skill_2 = []  # 第二排
        self.already_release_skill = []  # 已经释放过的技能
        self.boss_skill_release_order = ['u']
        self.is_release_boss_skill = False
        self.player_occupation = ""

    def init(self, image, player_occupation):
        """
                初始化，并处理图像中的技能区域。

                Args:
                    image (numpy.ndarray): 加载的图像数据，应为OpenCV可处理的格式。

                Returns:
                    bool: 如果成功找到并处理了技能图像，则返回True；否则返回False。
                    :param image:
                    :param player_occupation:
                """
        self.player_occupation = player_occupation
        self.skill_image_dict = {}  # 图片字典
        self.skill_1 = []  # 第一排
        self.skill_2 = []  # 第二排
        if self.player_occupation != "黑暗武士-黑暗武士":
            self.boss_skill_release_order = ['ctrl']
            self.skill_dict = {"q": self.q, "w": self.w, "e": self.e, "r": self.r, "t": self.t, "y": self.y, "ctrl": self.ctrl, "a": self.a, "s": self.s, "d": self.d, "f": self.f, "g": self.g, "h": self.h, "v": self.v}
        else:
            self.boss_skill_release_order = ['t']
            self.skill_dict = {"q": self.q, "w": self.w, "e": self.e, "r": self.r, "t": self.t, "y": self.y}
        # 遍历技能字典中的每个技能
        for key in self.skill_dict:
            # 根据技能字典中的坐标裁剪出技能图像
            skill_img = image[self.skill_dict[key]['y1']:self.skill_dict[key]['y2'], self.skill_dict[key]['x1']:self.skill_dict[key]['x2']]

            # 将裁剪出的技能图像转换为灰度图像
            gray_img = cv2.cvtColor(skill_img, cv2.COLOR_BGR2GRAY)
            # 计算灰度图像中像素值低于60的像素所占的比例
            ratio = self.calculate_pixel_ratio_below_threshold(gray_img, 60)
            # 如果低于阈值的像素比例大于0.85，则跳过该技能
            if ratio > 0.85:
                continue  # 根据技能键的分类，将技能添加到不同的列表中
            if self.player_occupation != "黑暗武士-黑暗武士":
                if key in ['q', 'w', 'e', 'r', 't', 'y']:
                    self.skill_1.append(key)
                if key in ['a', 's', 'd', 'f', 'g', 'h']:
                    self.skill_2.append(key)
                if key != "v":
                    # 将技能添加到BOSS技能释放顺序列表中
                    self.boss_skill_release_order.append(key)
            else:
                if key in ['q', 'w', 'e', 'r', 't']:
                    self.skill_1.append(key)
                if key != "y":
                    # 将技能添加到BOSS技能释放顺序列表中
                    self.boss_skill_release_order.append(key)
            # 将技能图像及其键存储到技能图像字典中
            self.skill_image_dict[key] = skill_img
        logger.info("self.skill_1:{}".format(self.skill_1))
        logger.info("self.skill_2:{}".format(self.skill_2))
        logger.info("boss_skill_release_order:{}".format(self.boss_skill_release_order))
        logger.info("存放图像的字典有:{}个图像".format(len(self.skill_image_dict)))
        # 检查是否成功找到了任何技能图像
        if len(self.skill_image_dict) == 0:
            return False
        return True

    def reset(self):
        self.already_release_skill.clear()

    def is_colored(self, skill_img: np.ndarray, threshold=30):
        """
        判断图像是否为彩色的。阈值用于确定彩色和灰色的界限。
        """
        # 转换为灰度图像
        gray = cv2.cvtColor(skill_img, cv2.COLOR_BGR2GRAY)

        # 计算每个像素的绝对差值
        diff = cv2.absdiff(skill_img, cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
        diff_sum = np.sum(diff, axis=2)  # 求和RGB通道的差值
        # logger.info(f"is_colored:{np.mean(diff_sum)}")

        # 判断差值是否大于阈值
        return np.mean(diff_sum) > threshold

    # def is_colored(self, skill_img: np.ndarray, threshold=30, color_percent=0.1):
    #     """
    #     判断图像是否为彩色的。
    #     当图像中彩色像素的比例超过指定百分比时，认为是彩色图像。
    #     """
    #     # 转换为灰度图像
    #     gray = cv2.cvtColor(skill_img, cv2.COLOR_BGR2GRAY)
    #
    #     # 计算每个像素的绝对差值
    #     diff = cv2.absdiff(skill_img, cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
    #     diff_sum = np.sum(diff, axis=2)  # 求和RGB通道的差值
    #
    #     # 计算彩色像素的比例（差值大于0的像素）
    #     color_pixels = np.count_nonzero(diff_sum > threshold)
    #     total_pixels = diff_sum.size
    #     color_ratio = color_pixels / total_pixels
    #
    #     logger.info(f"Color ratio: {color_ratio:.2%}")
    #     return color_ratio > color_percent

    def is_available(self, skill_img, skill_img_dic=None):
        # result = cv2.matchTemplate(skill_img, skill_img_dic, cv2.TM_CCOEFF_NORMED)
        # _, max_val, _, max_loc = cv2.minMaxLoc(result)
        # if max_val > 0.99:
        #     return True
        # return False
        return self.is_colored(skill_img)

    def is_match_template(self, skill_img, skill_img_dic):
        # 转换提取的图像到灰度空间（如果模板是灰度的）
        gray_skill_img = cv2.cvtColor(skill_img, cv2.COLOR_BGR2GRAY)
        gray_skill_img_dic = cv2.cvtColor(skill_img_dic, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(gray_skill_img, gray_skill_img_dic, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val > 0.99:
            return True
        return False

    def get_release_boss_skill(self, game_img):
        """
        获取可释放的Boss技能键（优化版本）
        :param game_img: 游戏截图
        :return: 技能键字符串，若无可用技能则返回"x"或None
        """
        try:
            # 特殊技能处理函数（针对黑暗武士职业的特殊逻辑）
            def handle_special_skill(skill_code):
                # 针对黑暗武士的特殊逻辑
                is_dark_knight = (self.player_occupation == "黑暗武士-黑暗武士")

                # 特殊技能处理规则：
                # 1. 非黑暗武士职业处理"ctrl"键
                # 2. 黑暗武士职业处理"y"键
                if (skill_code == "ctrl" and not is_dark_knight) or (skill_code == "y" and is_dark_knight):
                    return self.is_match_template(skill_img, skill_img_dic)
                return False

            # 遍历预定义的Boss技能释放顺序
            for skill_code in self.boss_skill_release_order:
                logger.info(f"检查Boss技能: {skill_code}")

                # 获取技能模板图片
                skill_img_dic = self.skill_image_dict.get(skill_code)
                if skill_img_dic is None:
                    logger.info(f"警告: 未找到技能 {skill_code} 的模板图片")
                    continue

                # 获取技能坐标
                point = self.skill_dict.get(skill_code)
                if not point:
                    logger.info(f"警告: 未找到技能 {skill_code} 的坐标信息")
                    continue

                # 截取技能区域图片
                skill_img = game_img[point['y1']:point['y2'], point['x1']:point['x2']]

                # 特殊技能处理
                if handle_special_skill(skill_code):
                    logger.info(f"特殊技能 {skill_code} 可用 (职业: {self.player_occupation})")
                    return skill_code

                if skill_code not in ("ctrl", "y"):
                    if self.player_occupation == "弓箭手-奇美拉":
                        # 创建HSV范围数组
                        lower = np.array([0, 0, 0])
                        upper = np.array([140, 255, 255])
                        # 将图像转换为HSV颜色空间
                        hsv = cv2.cvtColor(skill_img, cv2.COLOR_BGR2HSV)
                        # 创建掩码
                        mask = cv2.inRange(hsv, lower, upper)
                        # 将不在范围内的区域设为黑色
                        result = cv2.bitwise_and(skill_img, skill_img, mask=mask)
                        if self.is_available(result, skill_img_dic):
                            logger.info(f"弓箭手-奇美拉 找到可用技能: {skill_code}")
                            # 添加到已释放列表（如果尚未添加）
                            if skill_code not in self.already_release_skill:
                                self.already_release_skill.append(skill_code)
                            return skill_code
                    else:
                        if self.is_available(skill_img, skill_img_dic):
                            logger.info(f"找到可用技能: {skill_code}")
                            # 添加到已释放列表（如果尚未添加）
                            if skill_code not in self.already_release_skill:
                                self.already_release_skill.append(skill_code)
                            return skill_code

            # 所有技能都不可用时检查普通攻击
            if self.skill_status(game_img):
                logger.info("所有Boss技能不可用，返回普通攻击 'x'")
                return "x"

        except Exception as e:
            logger.info(f"释放Boss技能错误: {e}")
            import traceback
            traceback.print_exc()

        return None

    # def get_release_boss_skill(self, game_img):
    #     try:
    #         # game_img = screenshot_util.get_game_screenshot()
    #         for skill_code in self.boss_skill_release_order:
    #             logger.info(f"当前检查boss技能:{skill_code}")
    #             skill_img_dic = self.skill_image_dict.get(skill_code)
    #             if skill_img_dic is None:
    #                 continue
    #             point = self.skill_dict.get(skill_code)
    #
    #             skill_img = game_img[point['y1']:point['y2'], point['x1']:point['x2']]
    #             # 从图片字典中取得图片
    #             skill_img_dic = self.skill_image_dict.get(skill_code)
    #             if (skill_code == "ctrl" and self.player_occupation != "黑暗武士-黑暗武士") or (skill_code == "y" and self.player_occupation == "黑暗武士-黑暗武士"):
    #                 # if self.is_available(skill_img, skill_img_dic):
    #                 #     return skill_code  # else:  #     continue  #
    #                 if self.is_match_template(skill_img, skill_img_dic):
    #                     return skill_code
    #             else:
    #                 if self.is_available(skill_img, skill_img_dic):
    #                     # 如果是彩色的加入已经按过的列表，并返回这个键
    #                     self.already_release_skill.append(skill_code)
    #                     return skill_code
    #                 if self.is_available(skill_img, skill_img_dic):
    #                     logger.info(f"当前检查boss技能:{skill_code}\t可用")
    #                     return skill_code
    #         # 判断技能是否已释放结束
    #         if self.skill_status(game_img):
    #             return "x"
    #     except Exception as e:
    #         logger.info(e)
    #     return None

    # def get_release_skill(self, game_img):
    #     """
    #     获得释放技能键
    #     :param game_img: 图像
    #     :return: str
    #     """
    #     # game_img = screenshot_util.get_game_screenshot()
    #     logger.info(f"self.already_release_skill:{self.already_release_skill}")
    #     # 如果没有释放过技能
    #     if not self.already_release_skill:
    #         # 遍历第一排技能
    #         for skill_code in self.skill_1:
    #             logger.info("第一排技能：{}".format(skill_code))
    #             # 得到当前元素的坐标
    #             point = self.skill_dict.get(skill_code)
    #             # 截图
    #             skill_img = game_img[point['y1']:point['y2'], point['x1']:point['x2']]
    #             # 从图片字典中取得图片
    #             skill_img_dic = self.skill_image_dict.get(skill_code)
    #             # 如果截图的技能是否是彩色的
    #             if self.is_available(skill_img, skill_img_dic):
    #                 # 如果是彩色的加入已经按过的列表，并返回这个键
    #                 self.already_release_skill.append(skill_code)
    #                 return skill_code
    #     # 如果释放过技能
    #     if self.already_release_skill:
    #         # 遍历第二排技能
    #         for skill_code in self.skill_2:
    #             logger.info("第二排技能：{}".format(skill_code))
    #             point = self.skill_dict.get(skill_code)
    #             skill_img = game_img[point['y1']:point['y2'], point['x1']:point['x2']]
    #             skill_img_dic = self.skill_image_dict.get(skill_code)
    #             if self.is_available(skill_img, skill_img_dic):
    #                 self.already_release_skill.append(skill_code)
    #                 return skill_code
    #     # 如果第二排技能都释放了，就随机释放第一排技能
    #     for skill_code in self.skill_1:
    #         logger.info("第二排技能已释放过，现在释放第一排技能：{}".format(skill_code))
    #         point = self.skill_dict.get(skill_code)
    #         skill_img = game_img[point['y1']:point['y2'], point['x1']:point['x2']]
    #         skill_img_dic = self.skill_image_dict.get(skill_code)
    #         if self.is_available(skill_img, skill_img_dic):
    #             self.already_release_skill.append(skill_code)
    #             return skill_code
    #     # 判断技能是否已释放结束
    #     if self.skill_status(game_img):
    #         return "x"
    def get_release_skill(self, game_img):
        """
        获取可释放的技能键（修复技能释放逻辑）
        :param game_img: 游戏截图
        :return: 技能键字符串，若无可用技能则返回"x"
        """
        logger.info(f"已释放技能列表: {self.already_release_skill}")

        # 检查技能是否可用并返回第一个可用的技能键
        def find_available_skill(skill_codes, prefix=""):
            for skill_code in skill_codes:
                logger.info(f"{prefix}检查技能: {skill_code}")
                point = self.skill_dict.get(skill_code)
                if not point:
                    logger.info(f"警告: 未找到技能 {skill_code} 的坐标信息")
                    continue

                skill_img = game_img[point['y1']:point['y2'], point['x1']:point['x2']]
                template_img = self.skill_image_dict.get(skill_code)

                if template_img is None:
                    logger.info(f"警告: 未找到技能 {skill_code} 的模板图片")
                    continue
                if self.player_occupation == "弓箭手-奇美拉":
                    # 创建HSV范围数组
                    lower = np.array([0, 0, 0])
                    upper = np.array([140, 255, 255])
                    # 将图像转换为HSV颜色空间
                    hsv = cv2.cvtColor(skill_img, cv2.COLOR_BGR2HSV)
                    # 创建掩码
                    mask = cv2.inRange(hsv, lower, upper)
                    # 将不在范围内的区域设为黑色
                    result = cv2.bitwise_and(skill_img, skill_img, mask=mask)
                    if self.is_available(result, template_img):
                        logger.info(f"弓箭手-奇美拉 找到可用技能: {skill_code}")
                        # 添加到已释放列表（如果尚未添加）
                        if skill_code not in self.already_release_skill:
                            self.already_release_skill.append(skill_code)
                        return skill_code
                else:
                    if self.is_available(skill_img, template_img):
                        logger.info(f"找到可用技能: {skill_code}")
                        # 添加到已释放列表（如果尚未添加）
                        if skill_code not in self.already_release_skill:
                            self.already_release_skill.append(skill_code)
                        return skill_code

            return None

        # 1. 总是优先检查第一排技能（无论是否释放过）
        if skill := find_available_skill(self.skill_1, "第一排技能 - "):
            return skill

        # 2. 如果第一排没有可用技能，再检查第二排技能
        if skill := find_available_skill(self.skill_2, "第二排技能 - "):
            return skill

        # 3. 如果第二排也没有可用技能，尝试重置并重新检查第一排
        # （防止技能冷却后因历史记录被跳过）
        logger.info("尝试重置检查第一排技能（冷却可能已结束）")
        if skill := find_available_skill(self.skill_1, "第一排技能(重置检查) - "):
            return skill

        # 4. 所有技能都不可用，检查是否可以释放普通攻击
        if self.skill_status(game_img):
            logger.info("所有技能不可用，返回普通攻击 'x'")
            return "x"

        # 5. 没有任何可用技能或攻击
        logger.info("警告: 没有找到可用技能且无法普通攻击")
        return None

    def get_release_displacement_skill(self, skill_code):
        """
        获得释放技能键
        :param game_img: 图像
        :return: str
        """
        game_img = screenshot_util.get_game_screenshot()
        game_img = cv2.cvtColor(game_img, cv2.COLOR_RGB2BGR)
        logger.info(f"self.already_release_skill:{self.already_release_skill}")
        # 如果没有释放过技能
        if not self.already_release_skill:

            # 得到当前元素的坐标
            point = self.skill_dict.get(skill_code)
            # 截图
            skill_img = game_img[point['y1']:point['y2'], point['x1']:point['x2']]
            # 从图片字典中取得图片
            skill_img_dic = self.skill_image_dict.get(skill_code)
            # 如果截图的技能是否是彩色的
            if self.is_available(skill_img, skill_img_dic):
                # 如果是彩色的加入已经按过的列表，并返回这个键
                self.already_release_skill.append(skill_code)
                return skill_code

    def skill_status(self, game_img):
        """
        技能状态
        :param game_img:
        :return: bool
        """
        try:
            if self.player_occupation != "黑暗武士-黑暗武士":
                point = self.skill_dict.get('v')
                skill_img = game_img[point['y1']:point['y2'], point['x1']:point['x2']]
                skill_img_dic = self.skill_image_dict.get("v")
                logger.info(f"检查技能位置：v")
            else:
                point = self.skill_dict.get('y')
                skill_img = game_img[point['y1']:point['y2'], point['x1']:point['x2']]
                skill_img_dic = self.skill_image_dict.get("y")
                logger.info(f"检查技能位置：y")
            result = cv2.matchTemplate(skill_img, skill_img_dic, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > 0.95:
                return True
            return False
        except Exception as e:
            return False

    def calculate_pixel_ratio_below_threshold(self, image, threshold):
        """
            计算图像中低于指定阈值的像素比例

            Args:
                image (numpy.ndarray): 输入的图像数据，应为二维（灰度图像）或三维数组（彩色图像，但通常只处理第一维作为灰度值或单独通道）。
                threshold (int/float): 阈值，用于与图像中的像素值进行比较。低于此值的像素将被视为符合条件。

            Returns:
                float: 低于阈值的像素占总像素数的比例。如果图像为空或大小为零，则返回0.0。

            注意：
                - 此函数假设输入的`image`是一个有效的numpy数组，并且可以直接通过索引访问其像素值。
                - 如果`image`是多维数组（如彩色图像的RGB通道），函数将仅考虑第一个通道（假设为灰度通道或感兴趣的特定通道）。
                - 在处理大型图像时，请考虑性能优化，因为双重循环遍历每个像素可能非常耗时。
            """
        if image is None or image.size == 0:
            return 0.0

        total_pixels = image.size
        num_pixels_below_threshold = 0

        # 遍历图像的每个像素
        for y in range(image.shape[0]):
            for x in range(image.shape[1]):
                # 获取像素值
                pixel_value = image[y, x]
                # 检查像素值是否低于阈值
                if pixel_value < threshold:
                    num_pixels_below_threshold += 1

        # 计算比例
        ratio = num_pixels_below_threshold / total_pixels

        return ratio


skill_util = SkillUtil()
# if __name__ == "__main__":
#     img = Capture(hwnd, 0, 0, 1067, 600)
#     skill_util.init(img, "弓箭手-奇美拉")
#     for key, value in skill_util.skill_image_dict.items():
#         logger.info(key)
#         # logger.info(value)
#         # cv2.imwrite(f"{key}.png", value)
#     while True:
#         img = Capture(hwnd, 0, 0, 1067, 600)
#         RET = skill_util.get_release_skill(img)
#         logger.info(RET)
#     # logger.info(skill_util.is_available(skill_util.skill_image_dict["s"]))
#     # time.sleep(5)
#     # img = Capture(hwnd, 0, 0, 1067, 600)
#     # logger.info(skill_util.skill_status(img))
