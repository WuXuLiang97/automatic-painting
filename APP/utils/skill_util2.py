# -*- coding: utf-8 -*-

import cv2
import numpy as np
import json
import os

from core.capture import Capture
from root_dir import root_path
from utils.screenshot_util import screenshot_util
from utils.logging_setup import logger
from view.key_config_run import DEFAULT_CONFIG

class SkillUtil:
    # 默认配置


    def __init__(self):
        self.skill_region_w = 63
        self.skill_region_h = 218
        self.skill_width = int(self.skill_region_w / 2)
        self.skill_height = int(self.skill_region_h / 7)

        # 初始化默认坐标位置
        self._init_default_positions()

        # 初始化其他属性
        self.skill_dict = {}
        self.skill_image_dict = {}
        self.skill_1 = []
        self.skill_2 = []
        self.already_release_skill = []
        self.boss_skill_release_order = []
        self.is_release_boss_skill = False
        self.player_occupation = ""

        # 键盘配置
        self.key_config = {}
        self.skill_key_mapping = {}  # 技能位置到按键的映射

        # 加载键盘配置
        self.load_key_config()

    def _init_default_positions(self):
        """初始化默认技能位置坐标"""
        self.skill_positions = {}
        base_x = 432
        base_y = 532

        # 初始化14个技能位置（2行7列）
        for row in range(2):
            for col in range(7):
                idx = row * 7 + col
                x1 = base_x + col * self.skill_width
                y1 = base_y + row * self.skill_height
                x2 = x1 + self.skill_width
                y2 = y1 + self.skill_height

                self.skill_positions[idx] = {
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2
                }

    def load_key_config(self):
        """加载键盘配置文件"""
        target_dir = os.path.join(r"C:\Program Files", "json_resources")  # 拼接子目录
        config_file = os.path.join(target_dir, "key_config.json")

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.key_config = json.load(f)
                    self._update_skill_mapping()
                    logger.info(f"成功加载键盘配置: {config_file}")
            else:
                logger.warning(f"键盘配置文件不存在: {config_file}，使用默认配置")
                self.key_config = DEFAULT_CONFIG
                self._update_skill_mapping()
        except Exception as e:
            logger.error(f"加载键盘配置失败: {e}，使用默认配置")
            self.key_config = DEFAULT_CONFIG
            self._update_skill_mapping()

    def _update_skill_mapping(self):
        """根据配置更新技能映射"""
        self.skill_key_mapping = {}

        # 处理技能按键配置
        skills = self.key_config.get('skills', [])
        position_index = 0

        for row_idx, row_data in enumerate(skills):
            for col_idx, key in enumerate(row_data):
                if key:  # 如果按键已设置
                    # 将按键转换为小写，便于统一处理
                    key_lower = key.lower()
                    # 特殊处理组合键，只取最后一个键
                    if '+' in key_lower:
                        key_lower = key_lower.split('+')[-1]

                    self.skill_key_mapping[position_index] = key_lower
                    self.skill_positions[position_index]['key'] = key_lower
                position_index += 1

        logger.info(f"技能按键映射: {self.skill_key_mapping}")

    def init(self, image, player_occupation):
        """初始化技能系统"""
        self.player_occupation = player_occupation
        self.skill_image_dict = {}
        self.skill_dict = {}
        self.skill_1 = []
        self.skill_2 = []

        # 根据职业设置初始boss技能
        if self.player_occupation != "黑暗武士-黑暗武士":
            # 查找第7个技能（索引6）
            if 6 in self.skill_key_mapping:
                self.boss_skill_release_order.append(self.skill_key_mapping[6])
        else:
            # 查找第6个技能（索引5）
            if 5 in self.skill_key_mapping:
                self.boss_skill_release_order.append(self.skill_key_mapping[5])

        # 遍历技能位置
        for position_idx, position_data in self.skill_positions.items():
            if 'key' not in position_data:
                continue

            key = position_data['key']

            # 根据职业限制技能数量
            if self.player_occupation == "黑暗武士-黑暗武士":
                if position_idx > 5:  # 只使用前6个技能
                    continue

            # 裁剪技能图像
            skill_img = image[position_data['y1']:position_data['y2'],
                        position_data['x1']:position_data['x2']]

            # 检查技能是否有效
            gray_img = cv2.cvtColor(skill_img, cv2.COLOR_BGR2GRAY)
            ratio = self.calculate_pixel_ratio_below_threshold(gray_img, 60)

            if ratio > 0.85:
                continue

            # 添加到技能字典
            self.skill_dict[key] = position_data
            self.skill_image_dict[key] = skill_img

            # 分类技能
            if position_idx < 7:  # 第一排
                self.skill_1.append(key)
                if self.player_occupation != "黑暗武士-黑暗武士" and position_idx < 6:
                    self.boss_skill_release_order.append(key)
                elif self.player_occupation == "黑暗武士-黑暗武士" and position_idx < 5:
                    self.boss_skill_release_order.append(key)
            else:  # 第二排
                if self.player_occupation != "黑暗武士-黑暗武士":
                    self.skill_2.append(key)
                    if position_idx != 13:  # 不是最后一个技能
                        self.boss_skill_release_order.append(key)

        logger.info(f"第一排技能: {self.skill_1}")
        logger.info(f"第二排技能: {self.skill_2}")
        logger.info(f"Boss技能释放顺序: {self.boss_skill_release_order}")
        logger.info(f"技能图像字典包含 {len(self.skill_image_dict)} 个图像")

        return len(self.skill_image_dict) > 0

    def get_skill_key_by_position(self, row, col):
        """根据行列获取技能按键"""
        position_index = row * 7 + col
        return self.skill_key_mapping.get(position_index)

    def reload_config(self):
        """重新加载键盘配置"""
        self.load_key_config()
        logger.info("已重新加载键盘配置")

    def reset(self):
        self.already_release_skill.clear()

    def is_colored(self, skill_img: np.ndarray, threshold=30):
        """判断图像是否为彩色的"""
        gray = cv2.cvtColor(skill_img, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(skill_img, cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
        diff_sum = np.sum(diff, axis=2)
        return np.mean(diff_sum) > threshold

    def is_available(self, skill_img, skill_img_dic=None):
        return self.is_colored(skill_img)

    def is_match_template(self, skill_img, skill_img_dic):
        gray_skill_img = cv2.cvtColor(skill_img, cv2.COLOR_BGR2GRAY)
        gray_skill_img_dic = cv2.cvtColor(skill_img_dic, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(gray_skill_img, gray_skill_img_dic, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        return max_val > 0.99

    def get_release_boss_skill(self, game_img):
        """获取可释放的Boss技能键"""
        try:
            for skill_code in self.boss_skill_release_order:
                logger.info(f"检查Boss技能: {skill_code}")

                skill_img_dic = self.skill_image_dict.get(skill_code)
                if skill_img_dic is None:
                    logger.info(f"警告: 未找到技能 {skill_code} 的模板图片")
                    continue

                point = self.skill_dict.get(skill_code)
                if not point:
                    logger.info(f"警告: 未找到技能 {skill_code} 的坐标信息")
                    continue

                skill_img = game_img[point['y1']:point['y2'], point['x1']:point['x2']]

                # 检查是否是特殊技能
                is_special_skill = False
                if self.player_occupation != "黑暗武士-黑暗武士":
                    is_special_skill = (skill_code == self.skill_key_mapping.get(6))
                else:
                    is_special_skill = (skill_code == self.skill_key_mapping.get(5))

                if is_special_skill:
                    if self.is_match_template(skill_img, skill_img_dic):
                        logger.info(f"特殊技能 {skill_code} 可用")
                        return skill_code
                else:
                    # 普通技能检查
                    if self.player_occupation == "弓箭手-奇美拉":
                        lower = np.array([0, 0, 0])
                        upper = np.array([140, 255, 255])
                        hsv = cv2.cvtColor(skill_img, cv2.COLOR_BGR2HSV)
                        mask = cv2.inRange(hsv, lower, upper)
                        result = cv2.bitwise_and(skill_img, skill_img, mask=mask)
                        if self.is_available(result, skill_img_dic):
                            logger.info(f"弓箭手技能 {skill_code} 可用")
                            if skill_code not in self.already_release_skill:
                                self.already_release_skill.append(skill_code)
                            return skill_code
                    else:
                        if self.is_available(skill_img, skill_img_dic):
                            logger.info(f"技能 {skill_code} 可用")
                            if skill_code not in self.already_release_skill:
                                self.already_release_skill.append(skill_code)
                            return skill_code

            if self.skill_status(game_img):
                logger.info("所有Boss技能不可用，返回普通攻击 'x'")
                return "x"

        except Exception as e:
            logger.error(f"释放Boss技能错误: {e}")
            import traceback
            traceback.print_exc()

        return None

    def get_release_skill(self, game_img):
        """获取可释放的技能键"""
        logger.info(f"已释放技能列表: {self.already_release_skill}")

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
                    lower = np.array([0, 0, 0])
                    upper = np.array([140, 255, 255])
                    hsv = cv2.cvtColor(skill_img, cv2.COLOR_BGR2HSV)
                    mask = cv2.inRange(hsv, lower, upper)
                    result = cv2.bitwise_and(skill_img, skill_img, mask=mask)
                    if self.is_available(result, template_img):
                        logger.info(f"弓箭手技能 {skill_code} 可用")
                        if skill_code not in self.already_release_skill:
                            self.already_release_skill.append(skill_code)
                        return skill_code
                else:
                    if self.is_available(skill_img, template_img):
                        logger.info(f"技能 {skill_code} 可用")
                        if skill_code not in self.already_release_skill:
                            self.already_release_skill.append(skill_code)
                        return skill_code

            return None

        # 检查第一排技能
        if skill := find_available_skill(self.skill_1, "第一排技能 - "):
            return skill

        # 检查第二排技能
        if skill := find_available_skill(self.skill_2, "第二排技能 - "):
            return skill

        # 重新检查第一排技能（冷却可能已结束）
        logger.info("重新检查第一排技能")
        if skill := find_available_skill(self.skill_1, "第一排技能(重试) - "):
            return skill

        if self.skill_status(game_img):
            logger.info("所有技能不可用，返回普通攻击 'x'")
            return "x"

        logger.info("警告: 没有找到可用技能")
        return None

    def get_release_displacement_skill(self, skill_code):
        """获得释放位移技能键"""
        game_img = screenshot_util.get_game_screenshot()
        logger.info(f"检查位移技能: {skill_code}")

        if not self.already_release_skill:
            point = self.skill_dict.get(skill_code)
            if point:
                skill_img = game_img[point['y1']:point['y2'], point['x1']:point['x2']]
                skill_img_dic = self.skill_image_dict.get(skill_code)

                if skill_img_dic is not None and self.is_available(skill_img, skill_img_dic):
                    self.already_release_skill.append(skill_code)
                    return skill_code

        return None

    def skill_status(self, game_img):
        """检查技能状态（通过最后一个技能判断）"""
        try:
            # 根据职业获取最后一个技能的位置
            if self.player_occupation != "黑暗武士-黑暗武士":
                position_idx = 13  # 第14个位置
            else:
                position_idx = 5  # 第6个位置

            skill_key = self.skill_key_mapping.get(position_idx)
            if not skill_key:
                return False

            point = self.skill_positions.get(position_idx)
            if not point:
                return False

            skill_img = game_img[point['y1']:point['y2'], point['x1']:point['x2']]
            skill_img_dic = self.skill_image_dict.get(skill_key)

            if skill_img_dic is None:
                return False

            result = cv2.matchTemplate(skill_img, skill_img_dic, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            return max_val > 0.95

        except Exception as e:
            logger.error(f"检查技能状态失败: {e}")
            return False

    def calculate_pixel_ratio_below_threshold(self, image, threshold):
        """计算图像中低于指定阈值的像素比例"""
        if image is None or image.size == 0:
            return 0.0

        total_pixels = image.size
        num_pixels_below_threshold = np.sum(image < threshold)
        ratio = num_pixels_below_threshold / total_pixels

        return ratio


skill_util = SkillUtil()
