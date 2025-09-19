# -*- coding: utf-8 -*-
import json
import os
import random
import re
import struct
# import re
import time
import traceback
from copy import deepcopy
import datetime

import cv2
import keyboard
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from core.directional_astar import a_star, judge_direction  # A星寻路
from utils.api import test_view_subgroup_config, test_update_subgroup_config
from core.common import Point, occupationInfoMap, Player, MoveInfo, a_mapInfo, a_DictInfo, map_boss_info, MAP_MIN_ROOMS
from core.operator_module import OperatorModule
# from core.player_move import left_right_up_down_move_by, already_left_right_move, \
#     left_right_move, up_down_move,MovementRecorder
from core.player_move import MovementRecorder
# from utils.yjs import yjs
from utils.cv_recognizer import vnc_mm
from utils.common_util import sort_points_by_x, get_date
# from utils.config_util import get_all_role_settings, update_role_brush_date
from utils.minimap_util import miniMapUtil
from utils.cross_control import pyauto
# from utils.ocr_util import ocr_util
from utils.screenshot_util import screenshot_util
# from utils.skill_util import skill_util
from utils.skill_util2 import skill_util
import socket
from core import global_variable as gv

from utils.logging_setup import logger
from view.key_config_run import DEFAULT_CONFIG

current_path = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.abspath(os.path.join(current_path, '../'))
# 基础时间单位（秒）
MINUTE = 60
HOUR = 60 * MINUTE
# 目标物品列表

target_items = ["风化的碎骨", "破旧的皮革", "碎布片", "生锈的铁片", "最下级硬化剂", "最下级砥石", "炉岩核", "协调结晶体", "嘿", "嗯", "呀"]
SIMILARITY_THRESHOLD = 0.7  # 相似度阈值

# min_map_name = 0

target_dir = os.path.join(r"C:\Program Files", "json_resources")  # 拼接子目录
key_config_file = os.path.join(target_dir, "key_config.json")
try:
    if os.path.exists(key_config_file):
        with open(key_config_file, 'r', encoding='utf-8') as f:
            key_config = json.load(f)

            logger.info(f"成功加载键盘配置: {key_config_file}")
    else:
        logger.warning(f"键盘配置文件不存在: {key_config_file}，使用默认配置")
        key_config = DEFAULT_CONFIG
except Exception as e:
    logger.error(f"加载键盘配置失败: {e}，使用默认配置")
    key_config = DEFAULT_CONFIG

one_key_gather_value = key_config['one_key_gather']['key'].lower()  # 一键聚物
move_character_value = key_config['move_character']['key'].lower()  # 移动角色
back_to_selia_value = key_config['back_to_selia']['key'].lower()  # 回赛利亚房间
challenge_again_value = key_config['challenge_again']['key'].lower()  # 再次挑战


class PlayerThread(QThread):
    message = pyqtSignal(str)
    role_table_message = pyqtSignal()
    # player_dynamics_tuple = pyqtSignal(tuple)
    MAX_PICKUP_TIME = 30  # 最大捡取时长

    def __init__(self, dic=None):
        super().__init__()
        # 设定每日开始时间为早上6点
        self.start_hour = 6
        self.today_task_completed = False
        self.door_direction = ''
        self.attack_boss_sy = []
        self.forward = False
        self.big_break_time = None
        self.dic = dic
        self.yolo = None
        self.movement_recorder = MovementRecorder()
        self.special_room_id = None
        self.sock = None
        self.elite_room_id = None
        self.room_info_map = None
        self.query_room_id = None
        self.boss_room_id = None

        self.running = True
        self.operator_module = None
        self.current_role_group = None
        self.all_role_settings = {}
        self.role_index_list = []
        self.player = Player()
        self.current_role_index = -1  # 当前角色指数
        self.player_pos = None  # 玩家坐标
        self.buffer_is_release = False
        self.goods = []  # 金币坐标
        self.monsters = []  # 怪物坐标
        self.doors = []  # 门坐标
        self.box = []  # 障碍坐标
        self.is_boss = False  # 是不是领主
        self.to_door_count = 0
        self.has_continue = False
        self.has_rewards = False  # 有奖励
        self.is_first_attack_monster = False  # 是第一攻击怪物
        self.first_press_to_exit = True
        self.brush_cnt = 0  # 刷图次数
        self.brush_running = True  # 刷图中
        self.ghost_state = False  # 挂了
        self.pass_room_id = []
        self.find_player_direction = "right"  # 查找玩家方向
        self.mm = vnc_mm
        self.save_count = 0
        self.counter_file = None
        self.Image_count_initialization()
        self.sock_connect_flags = False
        self.running_time = None
        self.big_break_time_s = None
        self.big_break_time_text = ''
        # 设置随机大休息时间（3-4小时后）
        self.set_big_break_time()
        self.direction_dic = {}
        self.mouse_pos = None
        self.medicine = False
        self.medicine_time = None
        self.room_item_pickup_counts = {}  # 记录每个房间拾取次数
        self.doorOpenState = {}  # 记录每个房间开门状态

    def set_big_break_time(self):
        # 计算3-4小时后的随机时间点（以秒为单位）
        hours_3 = 3 * 60 * 60  # 10800秒
        hours_4 = 4 * 60 * 60  # 14400秒
        self.big_break_time_s = random.uniform(hours_3, hours_4)
        self.big_break_time_text = self.format_time(self.big_break_time_s)
        self.big_break_time = time.time() + self.big_break_time_s

    def should_take_big_break(self) -> bool:
        """检查是否应该进行大休息"""
        return time.time() >= self.big_break_time

    # 格式化输出
    def format_time(self, seconds: float) -> str:
        """将秒数格式化为时:分:秒的形式"""
        hours, remainder = divmod(int(seconds), HOUR)
        minutes, seconds = divmod(remainder, MINUTE)
        return f"{hours}小时{minutes}分钟{seconds}秒"

    def find_coordinate_variation(self, coordinate_list):
        if not coordinate_list:
            return None
        num_dimensions = len(coordinate_list[0])
        variations = []
        for dim in range(num_dimensions):
            values = [coord[dim] for coord in coordinate_list]
            min_val = min(values)
            max_val = max(values)
            variation = max_val - min_val
            variations.append(variation)
        return variations

    def initialize(self):
        self.operator_module = OperatorModule(self)
        self.operator_module.initialize()

    def Image_count_initialization(self):
        folder_path = 'Images'
        # 检查文件夹是否存在
        if not os.path.exists(folder_path):
            # 文件夹不存在，创建文件夹
            os.makedirs(folder_path)
            logger.info(f"文件夹 {folder_path} 已创建。")
        else:
            # 文件夹已存在
            logger.info(f"文件夹 {folder_path} 已存在。")
        # 路径和编号记录文件
        self.counter_file = os.path.join(folder_path, "last_counter.txt")
        # 读取上一次的编号，如果不存在则设置为1
        if os.path.exists(self.counter_file):
            with open(self.counter_file, 'r') as f:
                self.save_count = int(f.read().strip())
        else:
            self.save_count = 0

    def sock_connect(self):
        """
        连接socket
        :return: 
        """
        server_address = (gv.server_ip, gv.server_port)
        logger.info(server_address)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(server_address)
        self.sock.settimeout(1)
        self.sock_connect_flags = True
        logger.info(self.sock)

    def read_role_config(self):
        """
        读取当前角色组的配置，并设置当前角色的索引。

        首先清空当前的角色索引列表，然后获取当前角色组的所有角色设置。
        如果角色设置为空，则将当前角色索引设置为-1并返回。
        遍历所有角色设置，排除已完成的角色（即完成时间等于当前日期的角色），
        将剩余角色的索引添加到角色索引列表中。
        如果角色索引列表为空，则将当前角色索引设置为-1并返回。
        否则，将当前角色索引设置为角色索引列表中的第一个索引，
        并打印角色索引列表和当前角色索引，最后读取当前角色的配置。
        """
        # 清空当前的角色索引列表
        self.role_index_list.clear()

        # 获取新数据
        list_data = []
        # 获取当前角色组的所有角色设置
        # self.all_role_settings = get_all_role_settings(self.current_role_group)
        ret = test_view_subgroup_config(self.dic.get("cookies"), self.current_role_group)
        # 检查是否有配置数据
        if not ret or 'configs' not in ret or not ret['configs']:
            self.current_role_index = -1
            return

        # 处理数据
        for item in ret['configs']:
            logger.info(item)
            list_data.append(str(item['brush_order']))
            self.all_role_settings[str(item['brush_order'])] = item
        # 按刷图顺序排序角色
        self.all_role_settings = dict(sorted(self.all_role_settings.items(), key=lambda x: int(x[0])))

        # 如果角色设置为空，则设置当前角色索引为-1并返回
        if len(self.all_role_settings) == 0:
            self.current_role_index = -1
            return

            # 遍历所有角色设置
        for role_index in self.all_role_settings:
            logger.info(f"疲劳阈值:{self.all_role_settings[role_index].get('leave_pl')}")
            # 转换为日期对象进行比较
            expire_date = datetime.datetime.strptime(self.all_role_settings[role_index].get("brush_map_expire_time"), '%Y-%m-%d %H:%M:%S')
            if expire_date.hour < 6:
                previous_day = expire_date - datetime.timedelta(days=1)
                expire_date = previous_day.strftime("%Y-%m-%d")
            else:
                expire_date = expire_date.strftime("%Y-%m-%d")
            logger.info(f"302expire_date:{expire_date}")
            # 如果角色的完成时间等于当前日期，则跳过该角色
            if get_date() == expire_date:
                continue  # 否则，将角色索引添加到角色索引列表中
            self.role_index_list.append(role_index)

            # 如果角色索引列表为空，则设置当前角色索引为-1并返回
        if len(self.role_index_list) == 0:
            self.current_role_index = -1
            return
        # 将当前角色索引设置为角色索引列表中的第一个索引
        self.current_role_index = self.role_index_list[0]
        self.role_table_message.emit()

        # 打印角色索引列表和当前角色索引
        logger.info(self.role_index_list)
        logger.info(self.current_role_index)

        # 读取当前角色的配置
        self.read_current_role_config()

    def run(self):
        print(gv.banzhuan)
        if gv.banzhuan == 0:
            self.banzhuan()
        elif gv.banzhuan == 1:
            self.juqing()
        elif gv.banzhuan == 2:
            self.juqing_2()

    def banzhuan(self):
        try:
            self.sock_connect()  # 连接yolo识别服务器
            self.running = True
            for i in range(3, 0, -1):
                self.send_log("程序启动倒计时" + str(i) + "s")
                time.sleep(1)
            self.send_log("程序已启动")
            self.operator_module.move_to(640, 40)
            time.sleep(0.1)
            pyauto.click()
            time.sleep(0.1)
            while self.running:
                self.brush_running = True
                self.read_role_config()
                if self.current_role_index == -1:
                    # 这里防止站街，回到赛丽亚房间，脚本停止
                    self.select_role()
                    self.send_log("暂无可刷角色,脚本停止")
                    self.today_task_completed = True

                    # self.stop()
                    # # 刷完关机
                    # minutes = 1
                    # # 计算总秒数
                    # total_seconds = minutes * 60
                    # os.system(f"shutdown -s -t {total_seconds}")
                    # return
                if self.today_task_completed:
                    # 等待到次日六点
                    self.wait_until_next_start()
                    continue

                screenshot_util.activate_window_by_handle()  # 激活窗口
                # 选择角色
                self.select_role()
                self.send_log(f"当前执行到第{self.current_role_index}个角色")
                # 传递一个ocr方法
                pl_value = self.operator_module.ocr_pl(self.get_text, self.send_log)
                if pl_value is not None and isinstance(pl_value, (int, float)) and pl_value <= self.player.pl_value:
                    # update_role_brush_date(self.current_role_group, self.current_role_index)
                    # 从所有角色设置中根据当前角色索引获取当前角色的设置
                    role_settings = self.all_role_settings[self.current_role_index]
                    dic_data = {'career': role_settings['career'],
                                'convert_career': role_settings['convert_career'],
                                'height': role_settings['height'],
                                'map': role_settings['map'],
                                'difficulty': role_settings['difficulty'],
                                "brush_map_expire_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'leave_pl': self.player.pl_value}

                    test_update_subgroup_config(self.dic.get("cookies"), self.current_role_group, self.current_role_index, dic_data)
                    continue
                self.mm.FindPic_sleep(758, 564, 818, 589, "商城图标.bmp", 0.9, time_s=10, my_sleep=0.5)
                if self.player.map_name == "风暴逆鳞普通":
                    # 打开金绿盒子
                    self.access_0()
                if self.player.map_name == "跌宕群岛":
                    pyauto.keyPressChar('f2')
                    time.sleep(0.1)
                    ret = self.mm.FindPic_sleep(185, 401, 350, 482, "每日_跌宕群岛.bmp", 0.9, time_s=1, my_sleep=0.2)
                    if ret:
                        self.player.map_name = "风暴逆鳞普通"
                        self.player.map_level = 3
                    pyauto.keyPressChar('esc')
                    time.sleep(0.1)
                # 存、取
                self.access()
                # 检查自动捡物
                # self.auto_pick()
                # 进图
                if self.enter_map() == 0:
                    self.send_log("金绿柱石不够")
                    continue
                logger.info('地图名称:', self.player.map_name)
                # 初始化地图
                self.room_info_map = deepcopy(a_mapInfo.get(self.player.map_name))
                logger.info('初始化地图')
                for room_list in self.room_info_map:
                    logger.info(room_list)
                # 刷图
                while self.brush_running:
                    if self.player.map_name != "深渊：终末崇拜者":
                        # 得到玩家所在房间
                        self.get_min_map_yolo_res()

                        if self.player.player_room_id is not None:
                            break
                        else:
                            logger.info("普通图未检测到在图中,等待...")
                            time.sleep(0.5)
                            continue
                    else:
                        game_image = screenshot_util.get_game_screenshot()
                        text = self.get_text(927, 2, 1031, 22, game_image)
                        logger.info(f"识别右上角文字：{text}")
                        cleaned_text = re.sub(r'[^\u4e00-\u9fa5]', '', text)
                        if self.similarity(cleaned_text, "深渊：终末崇拜者") >= 0.7:
                            break
                        else:
                            logger.info("深渊图检测1——未检测到在图中,等待...")
                            time.sleep(0.5)
                            continue

                if self.player.map_name in miniMapUtil.minimap:
                    self.brush(self.brush_map)
                else:
                    self.send_log(f"{self.player.map_name}地图暂不支持，请检查配置文件")
                    return

        except Exception as e:
            logger.exception(f"player模块:{e}")
            # 打印完整的堆栈跟踪信息
            traceback.print_exc()
        finally:
            self.sock.close()
            self.sock = None

    def juqing(self):
        try:
            self.player.pl_value = 0
            self.sock_connect()  # 连接yolo识别服务器
            self.running = True
            for i in range(2, 0, -1):
                self.send_log("程序启动倒计时" + str(i) + "s")
                time.sleep(1)
            self.send_log("程序已启动")
            self.operator_module.move_to(640, 40)
            time.sleep(0.1)
            pyauto.click()
            time.sleep(0.1)
            while self.running:
                self.brush_running = True

                # 构造玩家的职业字符串，格式为“职业类型-具体职业”
                self.player.player_occupation = "通用" + "-" + "通用"
                logger.info(self.player.player_occupation)

                height = 140
                if height != 0:
                    self.player.player_height = height
                else:
                    # 根据玩家的职业从occupationInfoMap中获取身高信息，并更新到玩家对象中
                    self.player.player_height = occupationInfoMap[self.player.player_occupation].get("height")

                # 从角色设置中读取地图名称，并更新到玩家对象中
                self.player.map_name = "通用"

                # 从mapLevelDict中获取地图等级，根据角色设置中的地图等级键来查找，并更新到玩家对象中
                self.player.map_level = 1

                # 初始化玩家是否获得速度提升的标记为False
                self.player.has_get_speed = False

                self.player.is_daily_tasks = "是"

                # 打印当前玩家的地图名称
                logger.info(self.player.map_name)

                # 调用miniMapUtil的set_minimap_name方法，设置小地图的名称为当前玩家的地图名称
                miniMapUtil.set_minimap_name(self.player.map_name)
                screenshot_util.activate_window_by_handle()  # 激活窗口
                self.send_log(f"半自动剧情")
                # 传递一个ocr方法
                pl_value = self.operator_module.ocr_pl(self.get_text, self.send_log)
                if pl_value == 0:
                    self.send_log(f"疲劳为空")
                    return
                # 初始化地图
                self.room_info_map = deepcopy(a_mapInfo.get(self.player.map_name))
                logger.info('初始化地图')
                for room_list in self.room_info_map:
                    logger.info(room_list)
                # 刷图
                while self.brush_running:
                    if self.player.map_name != "深渊：终末崇拜者":
                        # 得到玩家所在房间
                        self.get_min_map_yolo_res()

                        if self.player.player_room_id is not None:
                            break
                        else:
                            logger.info("普通图未检测到在图中,等待...")
                            time.sleep(0.5)
                            continue
                    else:
                        game_image = screenshot_util.get_game_screenshot()
                        text = self.get_text(927, 2, 1031, 22, game_image)
                        logger.info(f"识别右上角文字：{text}")
                        cleaned_text = re.sub(r'[^\u4e00-\u9fa5]', '', text)
                        if self.similarity(cleaned_text, "深渊：终末崇拜者") >= 0.7:
                            break
                        else:
                            logger.info("深渊图检测1——未检测到在图中,等待...")
                            time.sleep(0.5)
                            continue

                if self.player.map_name in miniMapUtil.minimap:
                    self.juqing_brush(self.brush_map)
                else:
                    self.send_log(f"{self.player.map_name}地图暂不支持，请检查配置文件")
                    return

        except Exception as e:
            logger.exception(f"player模块:{e}")
            # 打印完整的堆栈跟踪信息
            traceback.print_exc()
        finally:
            self.sock.close()
            self.sock = None

    def juqing_2(self):
        try:
            self.player.pl_value = 0
            self.sock_connect()  # 连接yolo识别服务器
            self.running = True
            for i in range(2, 0, -1):
                self.send_log("程序启动倒计时" + str(i) + "s")
                time.sleep(1)
            self.send_log("程序已启动")
            self.operator_module.move_to(640, 40)
            time.sleep(0.1)
            pyauto.click()
            time.sleep(0.1)
            while self.running:
                self.brush_running = True

                # 构造玩家的职业字符串，格式为“职业类型-具体职业”
                self.player.player_occupation = "通用" + "-" + "通用"
                logger.info(self.player.player_occupation)

                height = 140
                if height != 0:
                    self.player.player_height = height
                else:
                    # 根据玩家的职业从occupationInfoMap中获取身高信息，并更新到玩家对象中
                    self.player.player_height = occupationInfoMap[self.player.player_occupation].get("height")

                # 从角色设置中读取地图名称，并更新到玩家对象中
                self.player.map_name = "通用"

                # 从mapLevelDict中获取地图等级，根据角色设置中的地图等级键来查找，并更新到玩家对象中
                self.player.map_level = 1

                # 初始化玩家是否获得速度提升的标记为False
                self.player.has_get_speed = False

                self.player.is_daily_tasks = "是"

                # 打印当前玩家的地图名称
                logger.info(self.player.map_name)

                # 调用miniMapUtil的set_minimap_name方法，设置小地图的名称为当前玩家的地图名称
                miniMapUtil.set_minimap_name(self.player.map_name)
                screenshot_util.activate_window_by_handle()  # 激活窗口
                self.send_log(f"半自动剧情2")
                # 传递一个ocr方法
                pl_value = self.operator_module.ocr_pl(self.get_text, self.send_log)
                if pl_value == 0:
                    self.send_log(f"疲劳为空")
                    return
                # 初始化地图
                self.room_info_map = deepcopy(a_mapInfo.get(self.player.map_name))
                logger.info('初始化地图')
                for room_list in self.room_info_map:
                    logger.info(room_list)
                # 刷图
                while self.brush_running:
                    if self.player.map_name != "深渊：终末崇拜者":
                        # 得到玩家所在房间
                        self.get_min_map_yolo_res()

                        if self.player.player_room_id is not None:
                            break
                        else:
                            logger.info("普通图未检测到在图中,等待...")
                            time.sleep(0.5)
                            continue
                    else:
                        game_image = screenshot_util.get_game_screenshot()
                        text = self.get_text(927, 2, 1031, 22, game_image)
                        logger.info(f"识别右上角文字：{text}")
                        cleaned_text = re.sub(r'[^\u4e00-\u9fa5]', '', text)
                        if self.similarity(cleaned_text, "深渊：终末崇拜者") >= 0.7:
                            break
                        else:
                            logger.info("深渊图检测1——未检测到在图中,等待...")
                            time.sleep(0.5)
                            continue

                if self.player.map_name in miniMapUtil.minimap:
                    self.juqing_brush_2(self.brush_map_2)
                else:
                    self.send_log(f"{self.player.map_name}地图暂不支持，请检查配置文件")
                    return

        except Exception as e:
            logger.exception(f"player模块:{e}")
            # 打印完整的堆栈跟踪信息
            traceback.print_exc()
        finally:
            self.sock.close()
            self.sock = None

    def stop(self):
        self.running = False
        self.brush_running = False
        # screenshot_util.cancel_window_topping()
        self.send_log("脚本已停止，可关闭窗口")

    def send_log(self, log):
        self.message.emit(log)

    def brush(self, func: callable):
        """
        刷图
        :return:
        """
        # 重置boss状态
        self.room_item_pickup_counts.clear()
        self.doorOpenState.clear()
        self.direction_dic.clear()
        self.is_boss = False
        self.to_door_count = 0
        self.first_press_to_exit = True
        for room_list in self.room_info_map:
            logger.info(room_list)
        # 用buff
        self.release_buffer()
        time.sleep(0.2)
        # 获取移速
        if not self.player.has_get_speed:
            self.get_move_speed()
        while self.brush_running and not self.ghost_state:
            logger.info("技能初始化")
            init_status = skill_util.init(screenshot_util.get_game_screenshot(), self.player.player_occupation)
            if init_status:
                break
        ret = self.mm.FindPic(727, 474, 885, 557, "魔界人.bmp", 0.9)
        if ret:
            # 关闭铃铛
            self.operator_module.move_to(743, 576)
            time.sleep(0.05)
            pyauto.click()
            time.sleep(0.05)
        logger.info('开始刷图')
        while self.brush_running:
            if self.ghost_state:
                self.direction_dic.clear()
                # 重置boss状态
                self.is_boss = False
                self.to_door_count = 0
                self.first_press_to_exit = True
                logger.info('地图名称:', self.player.map_name)
                # 初始化地图
                self.room_info_map = deepcopy(a_mapInfo.get(self.player.map_name))
                logger.info('初始化地图')
                for room_list in self.room_info_map:
                    logger.info(room_list)
                # 超时或幽灵状态要重置boss房状态，不然一直一出门就是Boss房
                click_status = self.operator_module.click_menu_item("返回城镇")
                if not click_status:
                    continue
                pyauto.releaseallkey()
                ret = self.mm.FindPic(0, 0, 1067, 600, "关闭.bmp", 0.9)
                if ret:
                    x, y = ret[0][1], ret[0][2]
                    self.operator_module.move_to(x, y)
                    time.sleep(0.05)
                    pyauto.click()
                    time.sleep(0.5)
                time.sleep(2)
                if self.operator_module.remove_weakness():  # 移除虚弱
                    _sleep = random.randint(300, 360)
                    self.send_log(f"虚弱，休息{_sleep}秒")
                    time.sleep(_sleep)
                time.sleep(2)
                self.select_role()  # 选择角色
                time.sleep(2)
                pl_value = self.operator_module.ocr_pl(self.get_text, self.send_log)  # 识别疲劳值
                if pl_value is not None and isinstance(pl_value, (int, float)) and pl_value <= self.player.pl_value:
                    self.ghost_state = False
                    # update_role_brush_date(self.current_role_group, self.current_role_index)
                    role_settings = self.all_role_settings[self.current_role_index]
                    dic_data = {'career': role_settings['career'],
                                'convert_career': role_settings['convert_career'],
                                'height': role_settings['height'],
                                'map': role_settings['map'],
                                'difficulty': role_settings['difficulty'],
                                "brush_map_expire_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'leave_pl': self.player.pl_value}
                    test_update_subgroup_config(self.dic.get("cookies"), self.current_role_group, self.current_role_index, dic_data)
                    self.brush_running = False
                    return
                self.mm.FindPic_sleep(758, 564, 818, 589, "商城图标.bmp", 0.9, time_s=10, my_sleep=0.5)
                if self.player.map_name == "风暴逆鳞普通":
                    # 打开金绿盒子
                    self.access_0()
                if self.player.map_name == "跌宕群岛":
                    pyauto.keyPressChar('f2')
                    time.sleep(0.1)
                    ret = self.mm.FindPic_sleep(185, 401, 350, 482, "每日_跌宕群岛.bmp", 0.9, time_s=1, my_sleep=0.2)
                    if ret:
                        self.player.map_name = "风暴逆鳞普通"
                        self.player.map_level = 3
                    pyauto.keyPressChar('esc')
                    time.sleep(0.1)
                # 存、取
                self.access()
                # 检查自动捡物
                # self.auto_pick()
                time.sleep(2)
                if self.enter_map() == 0:
                    self.send_log("金绿柱石不够")
                    return
                time.sleep(2)
                # todo 判断是否在图内
                self.ghost_state = False
                self.release_buffer()
            self.get_yolo_res()
            func()

    def juqing_brush(self, func: callable):
        """
        刷图
        :return:
        """
        # 重置boss状态
        self.direction_dic.clear()
        self.is_boss = False
        self.to_door_count = 0
        self.first_press_to_exit = True
        for room_list in self.room_info_map:
            logger.info(room_list)
        # 用buff
        self.release_buffer()
        time.sleep(0.2)
        # 获取移速
        if not self.player.has_get_speed:
            self.get_move_speed()
        while self.brush_running and not self.ghost_state:
            logger.info("技能初始化")
            init_status = skill_util.init(screenshot_util.get_game_screenshot(), self.player.player_occupation)
            if init_status:
                break
        ret = self.mm.FindPic(727, 474, 885, 557, "魔界人.bmp", 0.9)
        if ret:
            # 关闭铃铛
            self.operator_module.move_to(743, 576)
            time.sleep(0.05)
            pyauto.click()
            time.sleep(0.05)
        logger.info('开始刷图')
        while self.brush_running:
            self.get_yolo_res()
            func()

    def juqing_brush_2(self, func: callable):
        """
        刷图
        :return:
        """
        # 重置boss状态
        self.direction_dic.clear()
        self.is_boss = False
        self.to_door_count = 0
        self.first_press_to_exit = True
        for room_list in self.room_info_map:
            logger.info(room_list)
        # 用buff
        self.release_buffer()
        time.sleep(0.2)
        # 获取移速
        if not self.player.has_get_speed:
            self.get_move_speed()
        while self.brush_running and not self.ghost_state:
            logger.info("技能初始化")
            init_status = skill_util.init(screenshot_util.get_game_screenshot(), self.player.player_occupation)
            if init_status:
                break
        ret = self.mm.FindPic(727, 474, 885, 557, "魔界人.bmp", 0.9)
        if ret:
            # 关闭铃铛
            self.operator_module.move_to(743, 576)
            time.sleep(0.05)
            pyauto.click()
            time.sleep(0.05)
        logger.info('开始刷图')
        while self.brush_running:
            self.get_yolo_res()
            func()

    def brush_map(self):
        # 提取重复使用的变量，减少计算次数
        current_room_id = self.player.player_room_id
        pickup_count = self.room_item_pickup_counts.get(current_room_id, 0)
        has_doors = len(self.doors) > 0
        has_monsters = len(self.monsters) > 0
        has_goods = len(self.goods) > 0
        # 添加拾取次数检查 - 如果已经拾取超过10次，不再拾取
        can_pickup_goods = has_goods and pickup_count < 10

        # 调试日志保持不变，便于问题定位
        logger.info(
            f"\nbrush_map:"
            f"\n\tself.doors:{len(self.doors)}"
            f"\n\tself.has_continue:{self.has_continue}"
            f"\n\tself.player.player_room_id:{current_room_id}"
            f"\n\tself.room_item_pickup_counts:{pickup_count}"
            f"\n\tself.goods:{len(self.goods)}"
            f"\n\tself.monsters:{len(self.monsters)}"
            f"\n\tself.is_boss:{self.is_boss}"
        )

        # 分支1：存在门且无需继续上一操作
        if has_doors and not self.has_continue:
            if can_pickup_goods:  # 只有在拾取次数未超限时才拾取
                self.pickup_goods()
            else:
                self.enter_door()

        # 分支2：无门 或 需要继续上一操作
        else:
            # 优先处理怪物逻辑
            if has_monsters:
                if self.is_boss:
                    self.process_boss_room()
                else:
                    self.attach_monster()
            # 无怪物时，处理物品或进门
            else:
                # 满足物品拾取条件且拾取次数未超限时优先拾取
                if can_pickup_goods and not self.has_continue:
                    self.pickup_goods()
                # 非BOSS房间：无物品/不可拾取时进门
                elif not self.is_boss:
                    self.enter_door()
                # BOSS房间：无物品/不可拾取时处理BOSS逻辑
                else:
                    self.process_boss_room()

    def brush_map_2(self):
        def enter_door():
            """
            进入门并尝试移动到门的位置。

            该方法会在游戏或应用程序运行时持续尝试找到门的位置并移动到那里。如果遇到特定条件（如玩家位置无法确定、执行时间过长等），则会执行不同的逻辑。

            注意：该方法假设已经定义了其他方法和属性，如self.brush_running, self.ghost_state, self.get_yolo_res(), self.player_pos等。
            """

            logger.info("剧情进门")  # 打印开始信息
            player_pos_none_count = 0
            already_move = False  # 标记是否已经尝试过左右移动
            # 只要游戏在运行且不是幽灵状态，就持续尝试
            while self.brush_running and not self.ghost_state:

                self.get_yolo_res()  # enter_door获取YOLO检测结果
                # 如果检测到怪物、物品或满足特定条件，则处理
                logger.info("确定门检查怪物数量：{}\t金币数量：{}\t是否有奖励：{}\t是否有继续：{}"
                            "".format(len(self.monsters), len(self.goods), self.has_rewards, self.has_continue))
                if len(self.monsters) > 0 or len(self.goods) > 0 or self.has_rewards or self.has_continue:

                    if self.has_rewards or self.has_continue:
                        self.process_boss_room()
                    return

                # 如果玩家位置为None，则尝试左右移动
                if self.player_pos.x is None or self.player_pos.y is None:

                    logger.info("player_pos is none")
                    player_pos_none_count += 1
                    if player_pos_none_count > 5:
                        player_pos_none_count = 0
                        # 玩家位置恢复
                        self.movement_recorder.spiral_search(self.get_player_position, duration=2)  # self.movement_recorder.up_down_move("down", 0.2)  # self.player_left_right_move()
                    continue
                self.send_log("请鼠标移动到门的坐标然后鼠标右键")
                while self.brush_running and not self.ghost_state:
                    data = self.mouse_pos
                    self.get_yolo_res()  # enter_door获取YOLO检测结果
                    if isinstance(data, tuple) and self.player_pos.x:
                        # 接收到退出元组，退出循环
                        break
                    # 其他情况，即使数据是None或者其他内容，都不退出，继续处理
                    logger.info(f"[消费者] 收到: {data}")
                    if len(self.monsters) > 0:
                        return
                    elif len(self.goods) > 0:
                        return
                    elif self.has_rewards or self.has_continue:
                        return
                door_pos = Point(data[0], data[1])
                logger.info(f"door_pos:{type(door_pos)}")
                logger.info(door_pos)
                # 如果没有找到门的位置，则根据当前位置和移动方向尝试左右移动
                if isinstance(door_pos, Point):
                    logger.info(f"player_pos：{self.player_pos.x}, {self.player_pos.y}\tdoor_pos:{door_pos.x}, {door_pos.y}")
                    # if abs(self.player_pos.x - door_pos.x) < 40:
                    #     self.player_left_right_move()
                    #     continue
                    # move_info = self.compute_move_info(self.player_pos, door_pos, 0, 0)
                    # if move_info is None:
                    #     continue
                    # # 移动人物
                    # self.movement_recorder.left_right_up_down_move_by(move_info, already_move)

                    if abs(self.player_pos.x - door_pos.x) > 200:
                        move_info = self.compute_move_info(self.player_pos, door_pos, 0, 0)  # 计算到最近货物的移动信息
                        logger.info("向门奔跑：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                        self.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动

                    else:
                        move_info = self.compute_move_info_walk(self.player_pos, door_pos, 0, 0)  # 计算到最近货物的移动信息
                        logger.info("向门步行：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                        self.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动

                    self.to_door_count += 1
                    already_move = False
                    time.sleep(0.1)
                    ret = self.mm.FindPic(0, 0, 1067, 600, "未拾取.bmp", 0.8, delta_color=([23, 0, 0], [30, 93, 222]))
                    if ret:
                        logger.info("有未拾取物品，等待3秒过门")
                        time.sleep(3)
                    # 释放所有按键并重置技能状态
                    pyauto.releaseallkey()
                self.mouse_pos = None
                logger.info("enter_door stop")
                return

        # 情况1: 房间有物品且无怪物
        if len(self.goods) > 0 and len(self.monsters) == 0:
            self.pickup_goods()
            # 拾取物品后如果是普通房间就尝试进入下一个门
            if not self.is_boss:
                enter_door()
            # 如果是boss房间，拾取物品后处理boss战
            else:
                self.process_boss_room()

            # 情况2: 房间有怪物
        elif len(self.monsters) > 0:
            if self.is_boss:
                self.process_boss_room()
            else:
                self.attach_monster()

            # 情况3: 房间无物品且无怪物
        else:
            # 普通房间没有物品和怪物时进入下一个门
            if not self.is_boss:
                enter_door()
            # boss房间没有物品和怪物的特殊情况处理
            else:
                self.process_boss_room()

    def access(self):
        """存金币或取金绿柱石"""
        pyauto.releaseallkey()
        qx, qy = 327, 0
        if self.player.map_name in ("深渊：终末崇拜者", "跌宕群岛", "妖气追踪"):
            return
        if self.player.map_name == "风暴逆鳞普通":
            # 点箱子
            self.operator_module.move_to(368, 370)
            time.sleep(1)
            pyauto.click()
            time.sleep(0.5)
            self.operator_module.move_to(743, 161)
            time.sleep(0.1)
            ret = self.mm.FindPic_sleep(0, 0, 1067, 600, "账号金库.bmp|账号金库a.bmp", 0.9, 1, time_s=5)
            if ret:
                x, y = ret[0][1], ret[0][2]
                # 点账号金库
                self.operator_module.move_to(x, y)
                time.sleep(1)
                pyauto.click()
                time.sleep(0.1)
                pyauto.click()
                time.sleep(0.1)
            ret = self.mm.FindPic(0, 0, 1067, 600, "存入.bmp", 0.9, 1)
            if ret:
                x, y = ret[0][1], ret[0][2]
                qy = ret[0][2]
                # 点存入
                self.operator_module.move_to(x, y)
                time.sleep(1)
                pyauto.click()
                time.sleep(0.1)
                pyauto.click()
                time.sleep(0.1)
            ret = self.mm.FindPic(0, 0, 1067, 600, "一次性转存.bmp", 0.9, 1)
            if ret:
                x, y = ret[0][1], ret[0][2]
                # 点存入
                self.operator_module.move_to(x, y)
                time.sleep(0.1)
                pyauto.click()
                time.sleep(1)
                pyauto.keyPressChar('space')
                time.sleep(0.1)
                pyauto.keyPressChar('space')
                time.sleep(0.1)
                self.operator_module.move_to(743, 161)
                time.sleep(0.1)

                ret = self.mm.FindPic_sleep(qx, qy, 447, 541, "放入.bmp", 0.9, 1, time_s=2)
                if ret:
                    x1, y1, x2, y2 = ret[0][1], ret[0][2] - 10, ret[0][1] + 100, ret[0][2] + 30
                    ret = self.mm.FindPic_sleep(x1, y1, x2, y2, "取出.bmp", 0.9, 1, time_s=2)
                    if ret:
                        x, y = ret[0][1], ret[0][2]
                        # 点取出
                        self.operator_module.move_to(x, y)
                        time.sleep(0.1)
                        pyauto.click()
                        time.sleep(0.1)
                        ret = self.mm.FindPic_sleep(0, 0, 1067, 600, "金库1.bmp", 0.9, 1, time_s=5)
                        if ret:
                            x, y = ret[0][1], ret[0][2]
                            # 点物品
                            self.operator_module.move_to(x, y + 30)
                            time.sleep(0.1)
                            pyauto.click()
                            time.sleep(0.1)
                            ret = self.mm.FindPic_sleep(0, 0, 1067, 600, "数量.bmp", 0.9, 1, time_s=2)
                            if ret:
                                # 生成980到1020之间的随机整数
                                random_number = random.randint(2000, 2100)
                                # 将整数转换为字符串
                                random_number_str = str(random_number)
                                # # 输出结果
                                # logger.info(random_number_str)
                                for st in random_number_str:
                                    pyauto.keyPressChar(st)
                                    time.sleep(random.uniform(0.1, 0.15))
                                # keyboard.write(random_number_str, delay=random.uniform(0.1, 0.15))
                                time.sleep(random.uniform(1, 1.55))
                                # 点物品
                                self.operator_module.move_to(x, y + 30)
                                time.sleep(0.1)
                                pyauto.click()
                                time.sleep(1)
                                # 按下esc
                                pyauto.keyPressChar("esc")
                                time.sleep(0.1)  # # 回车  # pyauto.KeyPressChar("enter")  # time.sleep(0.1)
        else:
            # 点箱子
            self.operator_module.move_to(368, 370)
            time.sleep(0.1)
            pyauto.click()
            time.sleep(0.5)
            ret = self.mm.FindPic_sleep(0, 0, 1067, 600, "账号金库.bmp|账号金库a.bmp", 0.9, 1, time_s=5)
            if ret:
                x, y = ret[0][1], ret[0][2]
                # 点账号金库
                self.operator_module.move_to(x, y)
                time.sleep(0.1)
                pyauto.click()
                time.sleep(0.1)
            ret = self.mm.FindPic(0, 0, 1067, 600, "存入.bmp", 0.9, 1)
            if ret:
                x, y = ret[0][1], ret[0][2]
                # 点存入
                self.operator_module.move_to(x, y)
                time.sleep(0.1)
                pyauto.click()
                time.sleep(0.1)
                pyauto.click()
                time.sleep(0.1)
            ret = self.mm.FindPic(0, 0, 1067, 600, "一次性转存.bmp", 0.9, 1)
            if ret:
                x, y = ret[0][1], ret[0][2]
                # 点存入
                self.operator_module.move_to(x, y)
                time.sleep(0.1)
                pyauto.click()
                time.sleep(1)
                pyauto.keyPressChar('space')
                time.sleep(0.1)
                pyauto.keyPressChar('space')
                time.sleep(0.1)
                self.operator_module.move_to(743, 161)
                time.sleep(0.1)
            self.operator_module.open_window("选择菜单")
            # 按下esc
            pyauto.keyPressChar("esc")
            time.sleep(0.1)

    def enter_door(self):
        """
        进入门并尝试移动到门的位置。

        该方法会在游戏或应用程序运行时持续尝试找到门的位置并移动到那里。如果遇到特定条件（如玩家位置无法确定、执行时间过长等），则会执行不同的逻辑。

        注意：该方法假设已经定义了其他方法和属性，如self.brush_running, self.ghost_state, self.get_yolo_res(), self.player_pos等。
        """

        start_time = time.time()  # 记录方法开始执行的时间
        frame_time = time.time()
        logger.info("开始找门")  # 打印开始信息
        # 定义变量
        next_direction = "right"  # 默认的移动方向为向右
        already_move = False  # 标记是否已经尝试过左右移动
        up_and_down_move = False
        player_pos_none_count = 0  # 玩家位置为None的计数
        door__pos_none_count = 0  # 门位置为None的计数
        attack = False
        down = False
        # 只要游戏在运行且不是幽灵状态，就持续尝试
        while self.brush_running and not self.ghost_state:
            # 如果执行时间过长，则进入幽灵状态并返回
            if time.time() - start_time > 30:
                self.ghost_state = True
                return
            self.get_yolo_res()  # enter_door获取YOLO检测结果
            if time.time() - start_time > 10 and not attack:
                if self.player_pos.x is None:
                    continue

                move_info = self.compute_move_info(self.player_pos, Point(562, 392), 0, 0)
                if move_info is None:
                    continue
                # 移动人物
                self.movement_recorder.left_right_up_down_move_by(move_info, already_move)
                attack = True
                for bj in range(2):
                    if bj == 0:
                        pyauto.keyDownChar("right")
                        time.sleep(0.05)
                        pyauto.keyUpChar("right")
                        time.sleep(0.05)
                    else:
                        pyauto.keyDownChar("left")
                        time.sleep(0.05)
                        pyauto.keyUpChar("left")
                        time.sleep(0.05)
                    game_img = screenshot_util.get_game_screenshot()  # 获取当前游戏屏幕的截图
                    logger.info("找门超时，随便放个技能把怪清理掉")
                    skill = skill_util.get_release_skill(game_img)  # 获取释放普通怪物的技能
                    if skill == "x":  # 如果技能是"x"（平a）
                        pyauto.keyDownChar("x")
                        time.sleep(random.uniform(0.9, 1.2))
                        pyauto.keyUpChar("x")
                        time.sleep(0.05)
                        # pyauto.KeyPressChar(skill)
                        # game_img = screenshot_util.get_game_screenshot()  # 重新截图
                        continue  # 跳过后续代码，继续下一次循环
                    if skill is not None:  # 如果技能不是None
                        if self.player.player_occupation == "弓箭手-缪斯" and skill == "q":
                            pyauto.releaseallkey()
                            time.sleep(0.05)
                            if random.random() < 0.5:
                                if random.random() < 0.5:
                                    pyauto.keyPressChar("q")
                                    time.sleep(0.1)
                                    pyauto.keyPressChar("a")
                                    time.sleep(0.1)
                                else:
                                    pyauto.keyPressChar("w")
                                    time.sleep(0.1)
                                    pyauto.keyPressChar("a")
                                    time.sleep(0.1)
                            else:
                                if random.random() < 0.5:
                                    pyauto.keyPressChar("e")
                                    time.sleep(0.1)
                                else:
                                    pyauto.keyPressChar("a")
                                    time.sleep(0.1)
                        else:
                            logger.info(f"使用技能：{skill}")
                            pyauto.keyPressChar(skill)
                            time.sleep(0.1)

                        start_time_k = time.time()  # 记录当前时间作为开始时间
                        while self.brush_running and not self.ghost_state:  # 进入内层循环等待技能释放完成
                            end_time = time.time()  # 记录当前时间作为结束时间
                            execution_time = end_time - start_time_k  # 计算从开始到当前的执行时间
                            if execution_time > 5 and skill != "ctrl":  # 如果执行时间超过5秒
                                logger.info(f"等待技能释放结束超时")
                                while self.brush_running and not self.ghost_state:
                                    logger.info("技能初始化")
                                    init_status = skill_util.init(screenshot_util.get_game_screenshot(), self.player.player_occupation)
                                    if init_status:
                                        break
                                break  # 退出循环
                            elif execution_time > 10 and skill == "ctrl":
                                logger.info(f"等待技能释放大招结束超时")
                                break  # 退出循环
                            # logger.info('进入内层循环等待技能释放完成')
                            game_img = screenshot_util.get_game_screenshot()  # 更新截图
                            # self.get_yolo_res(game_img)  # 使用技能的时候也推理
                            if self.has_rewards:
                                break  # 退出内层循环
                            release_completed = skill_util.skill_status(game_img)
                            # logger.info("进入内层循环等待技能释放完成,是否已经释放完毕：{}".format(release_completed))
                            if release_completed:  # 检查技能是否已释放完成
                                time.sleep(0.2)  # 稍微等待一下以确保技能确实释放完成
                                break  # 退出内层循环
                            time.sleep(0.2)  # 注意：这里没有else语句来处理技能为None的情况，因为前面的if skill is not None已经涵盖了这种情况——

            # 如果检测到怪物、物品或满足特定条件，则处理
            logger.info("确定门检查怪物数量：{}\t是否有奖励：{}\t是否有继续：{}"
                        "".format(len(self.monsters), self.has_rewards, self.has_continue))

            if len(self.monsters) > 0 or self.has_rewards or self.has_continue:

                if self.has_rewards or self.has_continue:
                    self.process_boss_room()
                return

            # 如果玩家位置为None，则尝试左右移动
            if self.player_pos.x is None or self.player_pos.y is None:

                logger.info("player_pos is none")
                player_pos_none_count += 1
                if player_pos_none_count > 5:
                    player_pos_none_count = 0
                    # 玩家位置恢复
                    self.movement_recorder.spiral_search(self.get_player_position, duration=2)  # self.movement_recorder.up_down_move("down", 0.2)  # self.player_left_right_move()
                continue
            # 清除障碍
            self.clearingobstacles()
            # 获取小地图数据
            self.get_min_map_yolo_res()
            door_pos = None
            logger.info(f"self.player.map_name:{self.player.map_name}")
            # # 获取玩家所在的房间ID
            if self.player.map_name != "深渊：终末崇拜者":
                # 如果房间ID为None，则跳过本次循环
                if self.player.player_room_id is None:
                    logger.info("enter_door player_room_id is None")
                    continue
                # 打印房间ID
                logger.info(f"ROOM_Id:{self.player.player_room_id}")

                # 查找门的位置
                door_pos = self.find_door_pos(down)
            else:
                if len(self.doors) > 0:
                    door_pos = self.doors[0]
            logger.info(f"door_pos:{type(door_pos)}")
            logger.info(door_pos)
            # 如果没有找到门的位置，则根据当前位置和移动方向尝试左右移动
            if isinstance(door_pos, Point):
                logger.info(f"door_pos:{door_pos.x}, {door_pos.y}")
                # if abs(self.player_pos.x - door_pos.x) < 40:
                #     self.player_left_right_move()
                #     continue
                if 0 < door_pos.x < 150:
                    door_pos.x = 1
                elif 1067 > door_pos.x > 1067 - 150:
                    door_pos.x = 1100
                frame1_detections = (self.player_pos.x, self.player_pos.y)

                st = time.time()
                if abs(self.player_pos.x - door_pos.x) > 200:
                    move_info = self.compute_move_info(self.player_pos, door_pos, 0, 0)  # 计算到最近货物的移动信息
                    logger.info("向门奔跑：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                    self.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动

                else:
                    move_info = self.compute_move_info_walk(self.player_pos, door_pos, 0, 0)  # 计算到最近货物的移动信息
                    logger.info("向门步行：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                    self.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动
                move_info = self.compute_move_info(self.player_pos, door_pos, 0, 0)
                if move_info is None:
                    continue

                # # 移动人物
                # self.movement_recorder.left_right_up_down_move_by(move_info, already_move)
                self.to_door_count += 1
                logger.info(f"朝门移动耗时：{time.time() - st}秒")
                already_move = False
                time.sleep(0.1)
                ret = self.mm.FindPic(0, 0, 1067, 600, "未拾取.bmp", 0.8, delta_color=([23, 0, 0], [30, 93, 222]))
                if ret:
                    logger.info("有未拾取物品，等待3秒过门")
                    time.sleep(3)
                # 释放所有按键并重置技能状态
                pyauto.releaseallkey()
                # 设置首次攻击怪物的标志
                self.is_first_attack_monster = True
                if time.time() - frame_time > 5:
                    frame_time = time.time()
                    self.get_yolo_res()  # 重新获取YOLO结果，可能是为了更新玩家位置或货物位置
                    if self.player_pos.x is None:
                        continue
                    frame2_detections = (self.player_pos.x, self.player_pos.y)

                    frames = [frame1_detections, frame2_detections]
                    logger.info("检测人物frames:{}".format(frames))
                    # 设置一个位置变化的阈值（这里以像素为单位）
                    movement_threshold = 10  # 如果x或y方向上的变化超过10像素，则认为物体在移动
                    # 跟踪人物并检测运动
                    last_position = None
                    for frame_idx, (x, y) in enumerate(frames):
                        # 检查当前位置是否为None
                        if (x is None) or (y is None):
                            logger.info(f"在帧 {frame_idx + 1} 中，人物位置数据缺失。")
                            break
                        # 如果是第一帧，则没有上一个位置可以比较，直接跳过
                        if last_position is None:
                            last_position = (x, y)
                            continue
                        # 计算当前位置与上一个位置的变化
                        current_position = (x, y)
                        dx, dy = abs(current_position[0] - last_position[0]), abs(current_position[1] - last_position[1])

                        # 判断是否移动
                        if dx > movement_threshold or dy > movement_threshold:
                            logger.info(f"在帧 {frame_idx + 1} 中，人物移动了。")
                        else:
                            logger.info(f"在帧 {frame_idx + 1} 中，人物是静止的。")
                            already_move = False
                            if not up_and_down_move:
                                logger.info("尝试向上移动")
                                self.movement_recorder.up_down_move("up", 1)
                                up_and_down_move = True
                            else:
                                logger.info("尝试向下移动")
                                self.movement_recorder.up_down_move("down", 1)
                                up_and_down_move = False
                            self.test_move()
                            # if self.player_pos.y < 458:
                            #     logger.info("人物位置在上面卡住了")
                            #     self.movement_recorder.up_down_move("down", 1)
                            # else:
                            #     logger.info("人物位置在下面卡住了")
                            #     self.movement_recorder.up_down_move("up", 1)

            if isinstance(door_pos, str) and door_pos == "down":
                down = True
                logger.info("门在下面，往下移动1秒")
                self.movement_recorder.up_down_move("down", 1)

            else:
                frame1_detections = (self.player_pos.x, self.player_pos.y)
                if next_direction == "right" and self.player_pos.x > 750:
                    logger.info("现在方向向右，且玩家X轴坐标{}大于750，弹起前进的方向，现在向左走".format(int(self.player_pos.x)))
                    self.movement_recorder.already_left_right_move("left")
                    # pyauto.KeyDownChar(next_direction)
                    # time.sleep(0.05)
                    next_direction = "left"
                    already_move = True
                if next_direction == "left" and self.player_pos.x < 375:
                    logger.info("现在方向向左，且玩家X轴坐标{}小于450，弹起前进的方向，现在向右走".format(int(self.player_pos.x)))
                    self.movement_recorder.already_left_right_move("right")
                    # pyauto.KeyDownChar(next_direction)
                    # time.sleep(0.05)
                    next_direction = "right"
                    already_move = True
                if not already_move:
                    logger.info("没有移动过，现在移动方向为：{}".format(next_direction))
                    self.movement_recorder.already_left_right_move(next_direction)
                    already_move = True
                if time.time() - frame_time > 5:
                    frame_time = time.time()
                    self.get_yolo_res()  # 重新获取YOLO结果，可能是为了更新玩家位置或货物位置
                    if self.player_pos.x is None:
                        logger.info("第二帧没有识别到玩家")
                        continue
                    frame2_detections = (self.player_pos.x, self.player_pos.y)

                    frames = [frame1_detections, frame2_detections]
                    logger.info("检测人物frames:{}".format(frames))
                    # 设置一个位置变化的阈值（这里以像素为单位）
                    movement_threshold = 5  # 如果x或y方向上的变化超过10像素，则认为物体在移动
                    # 跟踪人物并检测运动
                    last_position = None
                    for frame_idx, (x, y) in enumerate(frames):
                        # 检查当前位置是否为None
                        if (x is None) or (y is None):
                            logger.info(f"在帧 {frame_idx + 1} 中，人物位置数据缺失。")
                            break
                        # 如果是第一帧，则没有上一个位置可以比较，直接跳过
                        if last_position is None:
                            last_position = (x, y)
                            continue
                        # 计算当前位置与上一个位置的变化
                        current_position = (x, y)
                        dx, dy = abs(current_position[0] - last_position[0]), abs(current_position[1] - last_position[1])

                        # 判断是否移动
                        if dx > movement_threshold or dy > movement_threshold:
                            logger.info(f"在帧 {frame_idx + 1} 中，人物移动了。")
                        else:
                            logger.info(f"在帧 {frame_idx + 1} 中，人物是静止的。")
                            already_move = False
                            if not up_and_down_move:
                                logger.info("尝试向上移动")
                                self.movement_recorder.up_down_move("up", 1)
                                up_and_down_move = True
                            else:
                                logger.info("尝试向下移动")
                                self.movement_recorder.up_down_move("down", 1)
                                up_and_down_move = False
                            self.test_move()
                            # if self.player_pos.y < 458:
                            #     logger.info("人物位置在上面卡住了")
                            #     self.movement_recorder.up_down_move("down", 1)
                            # else:
                            #     logger.info("人物位置在下面卡住了")
                            #     self.movement_recorder.up_down_move("up", 1)
                continue
            logger.info("结束找门")

    def player_left_right_move(self):
        """
        玩家左右移动，如果当前方向是右则向左移动，向左则向右移动
        :return:
        """
        self.movement_recorder.left_right_move(self.find_player_direction, 0.5)
        if self.find_player_direction == "right":
            self.find_player_direction = "left"
        else:
            self.find_player_direction = "right"

    def pickup_goods(self):
        """ 优化后的货物捡取方法 """
        logger.info("开始拾取物品")
        pyauto.releaseallkey()
        start_time = time.time()
        # self.get_yolo_res()
        frame_time = time.time()
        up_and_down_move = False
        while self.brush_running and not self.ghost_state:
            # 前置检查：超时/怪物/空货物
            if time.time() - start_time > self.MAX_PICKUP_TIME:
                self.ghost_state = True
                break
            if len(self.monsters) > 0 or len(self.goods) == 0:
                break

            # 状态更新
            self.get_yolo_res()
            if len(self.goods) == 0:
                break

            # 货物移动检测
            if self._check_goods_movement():
                logger.info("货物移动中，暂缓捡取")
                time.sleep(0.1)
                continue

            # 玩家位置恢复
            if self.player_pos.x is None:
                # self._recover_player_position()
                self.movement_recorder.spiral_search(self.get_player_position, duration=2)
                continue
            frame1_detections = (self.player_pos.x, self.player_pos.y)
            # 障碍物清除
            self.clearingobstacles()

            # 路径计算与移动
            goods_pos = sort_points_by_x(self.goods)  # 对货物位置按x坐标排序
            if not goods_pos:  # 无论什么原因导致排序后为空，都直接退出
                break
            the_first_item = Point(goods_pos[0][0], goods_pos[0][1])
            # 先获取当前房间ID和对应的拾取次数（不存在则为None）
            current_room_id = self.player.player_room_id
            pickup_count = self.room_item_pickup_counts.get(current_room_id, 0)

            if abs(self.player_pos.x - the_first_item.x) > 200 and pickup_count < 3:
                move_info = self.compute_move_info(self.player_pos, the_first_item, 0, 0)  # 计算到最近货物的移动信息
                logger.info("向物品奔跑：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                self.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动

            else:
                move_info = self.compute_move_info_walk(self.player_pos, the_first_item, 0, 0)  # 计算到最近货物的移动信息
                logger.info("向物品步行：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                self.movement_recorder.left_right_up_down_move_walk_by(move_info, False)  # 根据移动信息移动
            if self.player.player_room_id is not None:
                # 操作前检查键是否存在
                room_id = self.player.player_room_id
                if room_id not in self.room_item_pickup_counts:
                    self.room_item_pickup_counts[room_id] = 0  # 手动初始化
                self.room_item_pickup_counts[room_id] += 1  # 现在可以安全执行
                logger.info(f"房间 {room_id}拾取次数+1")
                logger.info(f"房间{current_room_id}拾取次数: {pickup_count}")
            pickup_count = self.room_item_pickup_counts.get(current_room_id)
            if isinstance(pickup_count, int) and pickup_count > 5:
                logger.info(f"房间{current_room_id}拾取次数大于或等于5次，重新识别移速")
                if self.player_pos.x:
                    # 重新识别移速
                    self.get_move_speed()
                    # 实时移动
                    # # 处理X方向移动：添加按键状态标记
                    # x_reached = False
                    # x_pressed_key = None  # 记录当前按下的X方向键（None表示未按下）
                    # while not x_reached and self.brush_running and not self.ghost_state:
                    #     # 实时更新状态和目标
                    #     self.get_yolo_res()
                    #     if len(self.goods) == 0 or self.player_pos.x is None:
                    #         break
                    #     goods_pos = sort_points_by_x(self.goods)
                    #     if not goods_pos:
                    #         break
                    #     the_first_item = Point(goods_pos[0][0], goods_pos[0][1])
                    #
                    #     x_diff = abs(self.player_pos.x - the_first_item.x)
                    #     if x_diff <= 15:
                    #         x_reached = True
                    #         break
                    #
                    #     # 确定需要按下的方向键
                    #     target_key = "left" if self.player_pos.x > the_first_item.x else "right"
                    #
                    #     # 只有当未按下目标键时，才执行按下操作（避免重复按下）
                    #     if x_pressed_key != target_key:
                    #         # 先释放可能按下的另一个方向键（比如从左移切换到右移时）
                    #         if x_pressed_key is not None:
                    #             pyauto.KeyUpChar(x_pressed_key)
                    #         # 按下目标键并更新标记
                    #         pyauto.KeyDownChar(target_key)
                    #         x_pressed_key = target_key
                    #
                    #     time.sleep(0.01)
                    #
                    # # 释放X方向按键（无论是否按下，确保最终释放）
                    # if x_pressed_key is not None:
                    #     pyauto.KeyUpChar(x_pressed_key)
                    #     x_pressed_key = None  # 清空标记
                    # # 额外保险：释放左右键（防止标记异常时按键未释放）
                    # pyauto.KeyUpChar("left")
                    # pyauto.KeyUpChar("right")
                    #
                    # # 处理Y方向移动：同理添加按键状态标记
                    # y_reached = False
                    # y_pressed_key = None  # 记录当前按下的Y方向键（None表示未按下）
                    # while not y_reached and self.brush_running and not self.ghost_state:
                    #     # 实时更新状态和目标
                    #     self.get_yolo_res()
                    #     if len(self.goods) == 0 or self.player_pos.x is None:
                    #         break
                    #     goods_pos = sort_points_by_x(self.goods)
                    #     if not goods_pos:
                    #         break
                    #     the_first_item = Point(goods_pos[0][0], goods_pos[0][1])
                    #
                    #     y_diff = abs(self.player_pos.y - the_first_item.y)
                    #     if y_diff <= 15:
                    #         y_reached = True
                    #         break
                    #
                    #     # 确定需要按下的方向键
                    #     target_key = "up" if self.player_pos.y > the_first_item.y else "down"
                    #
                    #     # 只有当未按下目标键时，才执行按下操作
                    #     if y_pressed_key != target_key:
                    #         # 先释放可能按下的另一个方向键（比如从上移切换到下移时）
                    #         if y_pressed_key is not None:
                    #             pyauto.KeyUpChar(y_pressed_key)
                    #         # 按下目标键并更新标记
                    #         pyauto.KeyDownChar(target_key)
                    #         y_pressed_key = target_key
                    #
                    #     time.sleep(0.01)
                    #
                    # # 释放Y方向按键
                    # if y_pressed_key is not None:
                    #     pyauto.KeyUpChar(y_pressed_key)
                    #     y_pressed_key = None  # 清空标记
                    # # 额外保险：释放上下键
                    # pyauto.KeyUpChar("up")
                    # pyauto.KeyUpChar("down")  # 修正之前的笔误（原代码是KeyDownChar）

            if '金币' in goods_pos[0][2]:
                pass
            else:
                time.sleep(0.1)
                pyauto.keyPressChar("x")
                time.sleep(0.05)
            # move_info = self.compute_move_info(self.player_pos, the_first_item, 0, 0)
            # self.movement_recorder.left_right_up_down_move_by(move_info, False)
            if time.time() - frame_time > 5:
                frame_time = time.time()
                self.get_yolo_res()  # 重新获取YOLO结果，可能是为了更新玩家位置或货物位置
                if self.player_pos.x is None:
                    continue
                frame2_detections = (self.player_pos.x, self.player_pos.y)

                frames = [frame1_detections, frame2_detections]
                logger.info("检测人物frames:{}".format(frames))
                # 设置一个位置变化的阈值（这里以像素为单位）
                movement_threshold = 10  # 如果x或y方向上的变化超过10像素，则认为物体在移动
                # 跟踪人物并检测运动
                last_position = None
                for frame_idx, (x, y) in enumerate(frames):
                    # 检查当前位置是否为None
                    if (x is None) or (y is None):
                        logger.info(f"在帧 {frame_idx + 1} 中，人物位置数据缺失。")
                        break
                    # 如果是第一帧，则没有上一个位置可以比较，直接跳过
                    if last_position is None:
                        last_position = (x, y)
                        continue
                    # 计算当前位置与上一个位置的变化
                    current_position = (x, y)
                    dx, dy = abs(current_position[0] - last_position[0]), abs(current_position[1] - last_position[1])

                    # 判断是否移动
                    if dx > movement_threshold or dy > movement_threshold:
                        logger.info(f"在帧 {frame_idx + 1} 中，人物移动了。")
                    else:
                        logger.info(f"在帧 {frame_idx + 1} 中，人物是静止的。")
                        if not up_and_down_move:
                            logger.info("尝试向上移动")
                            self.movement_recorder.up_down_move("up", 1)
                            up_and_down_move = True
                        else:
                            logger.info("尝试向下移动")
                            self.movement_recorder.up_down_move("down", 1)
                            up_and_down_move = False
                        self.test_move()
                        # if self.player_pos.y < 458:
                        #     logger.info("人物位置在上面卡住了")
                        #     self.movement_recorder.up_down_move("down", 1)
                        # else:
                        #     logger.info("人物位置在下面卡住了")
                        #     self.movement_recorder.up_down_move("up", 1)
            # 执行捡取与结果验证
            # self._execute_pickup_action()
        logger.info("拾取物品结束")
        pyauto.releaseallkey()

    def _check_goods_movement(self):
        positions = []
        for _ in range(3):  # 连续取三帧数据
            self.get_yolo_res()
            if len(self.goods) < 1: return None
            positions.append(sort_points_by_x(self.goods)[0])
            time.sleep(0.03)  # 适当增加采样间隔
        # 计算三帧间平均移动量
        dx = abs(positions[-1][0] - positions[0][0])
        dy = abs(positions[-1][1] - positions[0][1])
        return dx > 5 or dy > 5  # 动态阈值

    def _recover_player_position(self):
        """ 玩家位置丢失恢复策略 """
        logger.info("尝试螺旋搜索恢复位置")
        # pyauto.KeyPressChar('=')
        # time.sleep(0.05)
        # pyauto.KeyPressChar('space')
        # time.sleep(0.05)
        self.movement_recorder.spiral_search(self.get_player_position, duration=2)
        self.get_yolo_res()

    def get_player_position(self):
        self.get_yolo_res()
        logger.info(f"回调函数！获取玩家坐标：{self.player_pos.x, self.player_pos.y}")
        pos = self.player_pos.x
        return pos

    def _execute_pickup_action(self):
        """ 执行捡取操作并验证结果 """
        pre_count = len(self.goods)
        time.sleep(0.1)  # 暂停0.02秒
        self.get_yolo_res()
        if len(self.goods) > 0:
            for i in range(random.randint(2, 3)):
                pyauto.keyPressChar("x")
                time.sleep(0.05)
        if len(self.goods) < pre_count:
            logger.info(f"成功捡取{pre_count - len(self.goods)}件货物")

    def read_current_role_config(self):
        """
        读取当前角色的配置信息，并更新玩家对象的相应属性。

        此方法从当前角色的设置中获取职业、身高、地图名称和地图等级等信息，
        并将这些信息更新到玩家对象中。同时，还会设置小地图的名称。
        """
        # 从所有角色设置中根据当前角色索引获取当前角色的设置
        role_settings = self.all_role_settings[self.current_role_index]

        # 构造玩家的职业字符串，格式为“职业类型-具体职业”
        self.player.player_occupation = role_settings['career'] + "-" + role_settings['convert_career']
        logger.info(self.player.player_occupation)

        height = int(role_settings["height"])
        if height != 0:
            self.player.player_height = height
        else:
            # 根据玩家的职业从occupationInfoMap中获取身高信息，并更新到玩家对象中
            self.player.player_height = occupationInfoMap[self.player.player_occupation].get("height")

        # 从角色设置中读取地图名称，并更新到玩家对象中
        self.player.map_name = role_settings["map"]
        if self.player.map_name == "深渊：终末崇拜者":
            gv.sy = True
        else:
            gv.sy = False
        # 从mapLevelDict中获取地图等级，根据角色设置中的地图等级键来查找，并更新到玩家对象中
        self.player.map_level = int(role_settings["difficulty"])

        # 预留疲劳
        self.player.pl_value = int(role_settings["leave_pl"])

        self.send_log(f"预留疲劳为：{self.player.pl_value}")

        # 初始化玩家是否获得速度提升的标记为False
        self.player.has_get_speed = False

        self.player.is_daily_tasks = role_settings["today_task_completed"]

        # 打印当前玩家的地图名称
        logger.info(self.player.map_name)

        # 调用miniMapUtil的set_minimap_name方法，设置小地图的名称为当前玩家的地图名称
        miniMapUtil.set_minimap_name(self.player.map_name)

    def process_boss_room(self):
        """
        处理Boss房间的逻辑。

        如果当前处于Boss房间（self.is_boss为True），则执行以下逻辑：
        1. 记录开始时间。
        2. 在刷子（brush_running）运行且非幽灵状态（ghost_state）时循环执行：
           a. 计算已执行时间。
           b. 如果执行时间超过60秒，则设置幽灵状态（ghost_state）为True并退出循环。
           c. 如果怪物列表（monsters）不为空，则附加一个怪物。
           d. 如果怪物列表为空，则尝试处理通过（process_pass）的逻辑，如果成功，则退出循环。
           e. 无论是否附加怪物或处理通过，都执行获取YOLO结果的逻辑（get_yolo_res）。
        """
        if self.is_boss:  # 判断是否处于Boss房间
            logger.info("BOSS房处理")
            start_time = time.time()  # 记录当前时间作为开始时间
            while self.brush_running and not self.ghost_state:  # 循环条件：刷子正在运行且非幽灵状态
                end_time = time.time()  # 记录当前时间作为结束时间
                execution_time = end_time - start_time  # 计算从开始到当前的执行时间
                if execution_time > 120:  # 如果执行时间超过60秒
                    self.ghost_state = True  # 设置幽灵状态为True
                    logger.info("BOSS房处理超时")
                    break  # 退出循环
                if len(self.monsters) > 0 or self.player.map_name == "深渊：终末崇拜者" and self.is_boss and not self.has_continue:  # 如果怪物列表不为空
                    self.attach_monster()  # 攻击怪物的方法
                else:  # 如果怪物列表为空
                    if self.player.map_name == "深渊：终末崇拜者" or not self.doors:
                        process_status = self.process_pass()  # boss打败后处理逻辑
                        if process_status:  # 如果处理通过成功
                            logger.info("BOSS房处理结束")
                            break  # 退出循环
                    else:
                        logger.info("BOSS房处理结束")
                        return
                self.get_yolo_res()  # 无论是否附加怪物或处理通过，都执行获取YOLO结果的逻辑

    def attach_monster(self):
        """
        攻击怪物的方法。

        此方法首先打印“attach_monster start”表明开始攻击怪物。
        然后，它获取当前游戏屏幕的截图，并进入一个循环，在刷子运行中且角色未成为幽灵时持续尝试攻击怪物。
        如果检测到门存在或怪物列表为空，则退出循环。
        对于每个怪物，它会移动到怪物位置，并根据怪物类型（是否为Boss）选择合适的技能进行释放。
        如果技能是"x"（这里假设"x"是某种特殊技能或取消技能），则执行后立即重新截图并继续循环。
        对于其他技能，释放技能后进入一个内层循环，等待技能释放完成（通过检查技能状态）。
        一旦技能释放完成或退出条件满足，方法将重新截图并继续检查或退出循环。
        最后，打印“attach_monster stop”表明停止攻击怪物。
        """

        def contains_digit(s):
            pattern = r'\d'
            return bool(re.search(pattern, s))

        logger.info("开始攻击怪物")
        attack_boss_count = 0
        while self.brush_running and not self.ghost_state:  # 在刷子运行中且角色未成为幽灵时循环
            game_img = screenshot_util.get_game_screenshot()  # 获取当前游戏屏幕的截图
            logger.info("打怪中···")
            self.get_yolo_res(game_img)  # 假设此方法用于处理YOLO结果，可能是更新怪物或门的位置
            if len(self.doors) > 0 or len(self.monsters) == 0:  # 如果检测到门或没有怪物可以攻击
                break  # 退出循环
            if self.player.map_name == "深渊：终末崇拜者":
                # 检查是否有药
                k1_img = game_img[571:595, 139:163]
                if skill_util.is_colored(k1_img):
                    results = self.get_text(373, 558, 404, 574, game_img, amplify=True)
                    if contains_digit(results):
                        try:
                            if match := re.search(r'(\d+\.?\d*)%', results):
                                hb = float(match.group(1))
                                logger.info(f"当前血量为：{hb}")
                                if hb < 50:
                                    if not self.medicine or time.time() - self.medicine_time > 10:
                                        self.medicine_time = time.time()
                                        self.medicine = True
                                        logger.info(f"当前血量低于50%使用技能1的药品")
                                        self.send_log(f"当前血量低于50%使用技能1的药品")
                                        pyauto.keyPressChar("1")
                                        time.sleep(0.05)
                                    else:
                                        logger.info(f"在药品冷却时间，等待药品冷却")
                        except ValueError:
                            logger.error(f"血量转换失败: {results}")
                if self.attack_boss_sy:
                    attack_boss_sy_pos = sort_points_by_x(self.attack_boss_sy)  # 对货物位置按x坐标排序x
                    the_first_item = Point(attack_boss_sy_pos[0][0], attack_boss_sy_pos[0][1])
                    if self.player_pos.x is None:
                        self.movement_recorder.spiral_search(self.get_player_position, duration=2)
                        continue
                    if abs(self.player_pos.x - the_first_item.x) > 200:
                        move_info = self.compute_move_info(self.player_pos, the_first_item, 0, 0)  # 计算到最近货物的移动信息
                        logger.info("向深渊机制物品奔跑：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                        self.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动
                    else:
                        move_info = self.compute_move_info_walk(self.player_pos, the_first_item, 0, 0)  # 计算到最近货物的移动信息
                        logger.info("向深渊机制物品步行：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                        self.movement_recorder.left_right_up_down_move_walk_by(move_info, False)  # 根据移动信息移动
                    return
            self.move_to_monster()  # 移动到最近的怪物
            if self.is_boss and attack_boss_count <= 2:  # 如果当前怪物是Boss
                logger.info("当前怪物是Boss,释放打Boss的技能")
                skill = skill_util.get_release_boss_skill(game_img)  # 获取释放Boss的技能
                attack_boss_count += 1
            else:
                logger.info("当前怪物是普通怪物,释放打普通怪物的技能")
                skill = skill_util.get_release_skill(game_img)  # 获取释放普通怪物的技能
            if skill == "x":  # 如果技能是"x"（平a）
                pyauto.keyDownChar("x")
                time.sleep(random.uniform(0.9, 1.2))
                pyauto.keyUpChar("x")
                time.sleep(0.05)
                # pyauto.KeyPressChar(skill)
                # game_img = screenshot_util.get_game_screenshot()  # 重新截图
                continue  # 跳过后续代码，继续下一次循环
            if skill is not None:  # 如果技能不是None
                if self.player.player_occupation == "弓箭手-缪斯" and skill == "q":
                    pyauto.releaseallkey()
                    time.sleep(0.05)
                    if random.random() < 0.7:
                        if random.random() < 0.7:
                            pyauto.keyPressChar("q")
                            time.sleep(0.1)
                            pyauto.keyPressChar("a")
                            time.sleep(0.1)
                        else:
                            pyauto.keyPressChar("w")
                            time.sleep(0.1)
                            pyauto.keyPressChar("s")
                            time.sleep(0.1)
                    else:
                        pyauto.keyPressChar("x")

                else:
                    logger.info(f"使用技能：{skill}")
                    pyauto.keyPressChar(skill)
                    time.sleep(0.1)

                start_time = time.time()  # 记录当前时间作为开始时间
                while self.brush_running and not self.ghost_state:  # 进入内层循环等待技能释放完成
                    end_time = time.time()  # 记录当前时间作为结束时间
                    execution_time = end_time - start_time  # 计算从开始到当前的执行时间
                    if execution_time > 5 and skill != "ctrl":  # 如果执行时间超过5秒
                        logger.info(f"等待技能释放结束超时")
                        while self.brush_running and not self.ghost_state:
                            logger.info("技能初始化")
                            init_status = skill_util.init(screenshot_util.get_game_screenshot(), self.player.player_occupation)
                            if init_status:
                                break
                        break  # 退出循环
                    elif execution_time > 10 and skill == "ctrl":
                        logger.info(f"等待技能释放大招结束超时")
                        break  # 退出循环
                    # logger.info('进入内层循环等待技能释放完成')
                    game_img = screenshot_util.get_game_screenshot()  # 更新截图
                    if self.has_rewards:
                        break  # 退出内层循环
                    release_completed = skill_util.skill_status(game_img)
                    # logger.info("进入内层循环等待技能释放完成,是否已经释放完毕：{}".format(release_completed))
                    if release_completed:  # 检查技能是否已释放完成
                        time.sleep(0.2)  # 稍微等待一下以确保技能确实释放完成
                        break  # 退出内层循环
                    time.sleep(0.2)  # 注意：这里没有else语句来处理技能为None的情况，因为前面的if skill is not None已经涵盖了这种情况

        logger.info("结束攻击怪物")  # 打印停止信息

    def release_buffer(self):
        """
        用buff
        :return:
        """
        if occupationInfoMap.get(self.player.player_occupation) is not None:
            player_occupation = ["男光职者-光明骑士", "女光职者-光明骑士", "女魔法师-小魔女", "弓箭手-缪斯", "女神枪手-协战师"]
            logger.info(f"职业：{self.player.player_occupation}")
            if self.player.player_occupation in player_occupation:
                buffer = occupationInfoMap.get(self.player.player_occupation).get("buffer")
                buffs = buffer.split("|")
                for buff in buffs:
                    key = buff.split(",")
                    for k in key:
                        pyauto.keyPressChar(k)
                        # yjs.KeyPressChar(k)
                        time.sleep(0.05)
            if self.player.player_occupation == "女魔法师-召唤师":
                pyauto.keyPressChar("left")
                time.sleep(0.05)
                pyauto.keyPressChar("up")
                time.sleep(0.05)
                pyauto.keyPressChar("right")
                time.sleep(0.05)
                pyauto.keyPressChar("space")
                time.sleep(0.05)
        self.buffer_is_release = True

    def find_nearest_zero_to_target(self, room_info_map, target):
        """
        找不到问号房间和精英房间的情况下找到最靠近boss房的房间坐标
        :param room_info_map:
        :param target:boss房坐标
        :return:最靠近boss房的房间坐标
        """
        # 初始化一个空列表来存储为0的坐标
        zero_coords = []

        # 遍历矩阵
        for x in range(len(room_info_map)):  # x 是行索引
            for y in range(len(room_info_map[x])):  # y 是列索引
                if room_info_map[x][y] == 0 and (x, y) != target:
                    zero_coords.append((x, y))  # 将坐标 (x, y) 加入到列表中

        # 打印结果
        logger.info(f"已探索房间：{zero_coords}")
        # 如果没有为0的坐标，则直接返回None（虽然在这个示例中不会发生）
        if not zero_coords:
            return None

        # 初始化最小距离为无穷大，以及最近的坐标
        min_distance = float('inf')
        nearest_coord = None

        # 遍历坐标列表
        for coord in zero_coords:
            # 计算当前坐标与target的距离的平方（避免使用sqrt以提高效率）
            distance_squared = (coord[0] - target[0]) ** 2 + (coord[1] - target[1]) ** 2
            # 如果当前距离的平方小于已知的最小距离的平方，则更新最小距离和最近的坐标
            if distance_squared < min_distance:
                min_distance = distance_squared
                nearest_coord = coord

            # 如果找到了最近的坐标，则打印它
        if nearest_coord is not None:
            logger.info(f"与({target[0]}, {target[1]})最近的房间坐标是: {nearest_coord}")
        else:
            logger.info(f"没有找到与({target[0]}, {target[1]})接近的坐标。")
        return nearest_coord

    def find_door_pos(self, down):
        """
        寻找玩家当前房间内的门的位置。

        首先检查玩家是否在有效的地图中，并且该地图有对应的房间信息。
        然后，根据玩家当前所在的房间ID，查找该房间内的门的位置。
        如果找到符合条件的门，则返回该门的位置；否则返回None。

        Returns:
            DoorPosition: 符合条件的门的位置对象，如果未找到则返回None。
        """
        logger.info("开始找门")
        if not self.is_valid_map():
            logger.info("结束找门（无效地图）")
            return None
        # self.get_boss_room_id()
        logger.info(f"boss房位置:{self.boss_room_id}")
        # if self.player.map_name == "德洛斯矿山外围":
        #     priority_direction = 'down'
        # else:
        #     priority_direction = 'right'
        priority_direction = 'right'
        # 查找问号房间的路径
        map_direction = None
        # 遍历输出A星地图数据
        for room_list in self.room_info_map:
            logger.info(room_list)
        if self.boss_room_id:
            map_direction = self.find_door_direction()

        if map_direction is None:
            logger.info("map_direction 为空")
            return None  # 如果没有找到当前房间的信息，则返回None
        # 得到房间门筛选信息
        room_info = a_DictInfo.get(self.player.map_name).get(map_direction)
        logger.info(room_info)
        logger.info(f"开始遍历所有门")
        # 遍历所有门的位置，寻找在当前房间内的门
        for door_pos in self.doors:
            logger.info(f"当前遍历的door_pos:{(door_pos.x, door_pos.y)}")
            if (room_info['min_x'] < door_pos.x < room_info['max_x'] and  # 门的x坐标在房间x坐标范围内
                    room_info['min_y'] < door_pos.y <= room_info['max_y']):  # 门的y坐标在房间y坐标范围内
                # logger.info(f'door_x:{door_pos.x},door_y:{door_pos.y}')  # 打印找到的门的位置，用于调试
                logger.info("已找到门，结束找门")
                if map_direction == "up":
                    logger.info("向上的门")
                    door_pos.y = door_pos.y - 50
                return door_pos  # 返回找到的门的位置
        if map_direction == "down":
            # 记录人物当前坐标
            logger.info(f"人物坐标: ({self.player_pos.x}, {self.player_pos.y})")

            # 处理门位置数据
            sorted_doors = sorted(self.doors, key=lambda door: door.y)

            # 遍历并记录所有门位置
            for door in self.doors:
                logger.info(f"门位置: ({door.x}, {door.y})")

            # 检查是否有可用门位置
            if not sorted_doors:
                logger.warning("未找到任何门位置数据（self.doors为空）")
                return map_direction

            # 根据方向返回对应门位置
            if down:
                bottom_door = sorted_doors[-1]
                logger.info(f"返回最下方的门位置: ({bottom_door.x}, {bottom_door.y})")
                return bottom_door
            else:
                return map_direction

        logger.info("结束找门,没有找到门")
        return map_direction  # 如果没有找到符合条件的门，则返回None

    # def get_next_door_direction(self):
    #     if len(self.doors) <= 0 or self.player.map_name not in mapDictInfo:
    #         return None
    #     room_info_map = mapDictInfo.get(self.player.map_name)
    #     room_info = room_info_map.get(self.player.player_room_id)
    #     return room_info['direction']

    def get_move_speed(self):
        def open_window():
            for _ in range(5):
                pyauto.keyPressChar('m')
                time.sleep(0.1)
                ret_t = self.waiting_for_the_text_to_appear([353, 58, 424, 79], "个人信息", r'[\u4e00-\u9fa5]+', 0.5)
                logger.info("OCR: " + ret_t)
                if ret_t:
                    logger.info("已打开个人信息")
                    return True
            return False

        status = False
        for i in range(5):
            try:
                open_status = open_window()
                if not open_status:
                    continue
                time.sleep(0.1)
                ret = self.mm.FindPic(0, 0, 1067, 600, "移动速度.bmp", 0.9, 1, None, delta_color=([19, 0, 0], [21, 255, 255]))
                if ret:
                    x1, y1 = ret[0][3] + 60, ret[0][4] - 5
                    x2, y2 = x1 + 55, y1 + 20
                else:
                    self.send_log("没有找到移动坐标")
                    continue
                # results = self.waiting_for_the_text_to_appear([x1, y1, x2, y2], "0123456789", r'[0-9]+', 0.5, amplify=False)
                img_dict = {
                    '0': ['0.bmp'], '1': ['1.bmp', '1-1.bmp'], '2': ['2.bmp', '2-1.bmp'],
                    '3': ['3.bmp', '3-1.bmp'], '4': ['4.bmp', '4_1.bmp'],
                    '5': ['5.bmp', '5-1.bmp'], '6': ['6.bmp', '6-1.bmp'], '7': ['7.bmp', '7-1.bmp'],
                    '8': ['8.bmp', '8-1.bmp'], '9': ['9.bmp', '9-1.bmp']

                }
                results = self.mm.screenshot_OCR_str(x1, y1, x2, y2, img_dict, 0.8, get_colour=([62, 130, 159], [65, 141, 163]), drag=None)
                self.send_log(f"移速识别结果：{results}")
                if len(results) > 0:
                    if len(results) > 2:
                        # 取前面最后一个前面的个字符
                        plain_move_speed = int(results[:-1])
                    else:
                        plain_move_speed = int(results)
                    self.send_log(f"处理后移速为：{plain_move_speed}")
                else:
                    self.send_log("没有识别到移速")
                    continue
                if self.player.player_occupation == "弓箭手-缪斯":
                    plain_move_speed += 20
                # game_image = screenshot_util.get_game_screenshot()
                # move_speed_image = game_image[512:530, 427:500]
                # ocr_text = ocr_util.ocr(move_speed_image)
                # if ocr_text == "":
                #     continue
                # plain_move_speed = ocr_text.replace("+", "").replace("%", "")
                plain_move_speed = float(plain_move_speed) / 100
                base_speed_x, base_speed_y = self.operator_module.get_base_speed(self.player.player_occupation, plain_move_speed)
                self.send_log(f"人物x轴基本速度为：{base_speed_x}\t人物y轴基本速度为：{base_speed_y}")
                self.player.x_speed = base_speed_x * (1 + plain_move_speed)
                self.player.y_speed = base_speed_y * (1 + plain_move_speed)
                # 步行速度一样的
                self.player.x_speed_walk = base_speed_y * (1 + plain_move_speed)
                self.player.y_speed_walk = base_speed_y * (1 + plain_move_speed)
                self.send_log(f"人物x轴速度为：{self.player.x_speed}\t人物y轴速度为：{self.player.y_speed}")
                self.operator_module.close_all_window()
                self.player.has_get_speed = True
                status = True
                return
            except Exception as e:
                self.send_log(f"player模块:{e}")
                # 打印完整的堆栈跟踪信息
                traceback.print_exc()
                logger.exception(f"player模块:{e}")
                continue
        if not status:
            self.send_log("获取面板速度失败")
            self.stop()

    def compute_move_info(self, player_pos, target_pos, diff_x, diff_y):
        # 检查无效输入
        if (player_pos.x is None or player_pos.y is None or any(v <= 0 for v in [player_pos.x, player_pos.y, target_pos.x, target_pos.y])):
            return None

        move_info = MoveInfo("left", "up", 0, 0, False)
        # 处理X轴方向
        dx = abs(player_pos.x - target_pos.x)
        if dx > diff_x:
            delta = self.player.x_speed * 0.05
            if player_pos.x > target_pos.x and player_pos.x - target_pos.x > delta:
                target_pos.x += delta
            elif player_pos.x < target_pos.x and target_pos.x - player_pos.x > delta:
                target_pos.x -= delta
            if player_pos.x < target_pos.x:
                move_info.leftRightDirection = "right"
            if dx > 200:
                move_info.run = True
            move_info.xTime = (abs(player_pos.x - target_pos.x - diff_x) / self.player.x_speed)
        # 处理Y轴方向
        dy = abs(player_pos.y - target_pos.y)
        if dy > diff_y:
            if player_pos.y < target_pos.y:
                move_info.upDownDirection = "down"
            move_info.yTime = (abs(player_pos.y - target_pos.y - diff_y) / self.player.y_speed)
        return move_info

    def compute_move_info_walk(self, player_pos, target_pos, diff_x, diff_y):
        # 检查无效输入
        if (player_pos.x is None or player_pos.y is None or any(v <= 0 for v in [player_pos.x, player_pos.y, target_pos.x, target_pos.y])):
            return None

        move_info = MoveInfo("left", "up", 0, 0, False)
        # 处理X轴方向
        dx = abs(player_pos.x - target_pos.x)
        if dx > diff_x:
            delta = self.player.x_speed_walk * 0.1
            if player_pos.x > target_pos.x and player_pos.x - target_pos.x > delta:
                target_pos.x += delta
            elif player_pos.x < target_pos.x and target_pos.x - player_pos.x > delta:
                target_pos.x -= delta
            if player_pos.x < target_pos.x:
                move_info.leftRightDirection = "right"
            if dx > 200:
                move_info.run = True
            move_info.xTime = (abs(player_pos.x - target_pos.x - diff_x) / self.player.x_speed_walk)
        # 处理Y轴方向
        dy = abs(player_pos.y - target_pos.y)
        if dy > diff_y:
            if player_pos.y < target_pos.y:
                move_info.upDownDirection = "down"
            move_info.yTime = (abs(player_pos.y - target_pos.y - diff_y) / self.player.y_speed_walk)
        return move_info

    def move_to_monster(self):
        """
        使玩家角色向最近的怪物移动，并控制怪物面向玩家。

        该函数首先检查玩家位置是否已设定。然后，它找到最近的怪物，并根据一系列条件调整怪物的位置
        和面向方向，以便玩家可以接近它。最后，计算玩家向怪物移动的信息，并发送键盘指令来控制
        玩家移动和怪物面向。

        返回:
            bool: 如果玩家位置已设定且执行了移动操作，则返回True；否则返回False。
        """
        logger.info("开始向怪物移动")
        monster_direction = "right"
        if self.player_pos.x is None or not self.monsters:
            # 如果玩家位置未设定（即x坐标为None），则返回False
            return False
        # 清除障碍
        self.clearingobstacles()
        # 计算每个怪物与玩家的距离，找到最近的怪物
        min_distance = float('inf')
        nearest_monster = None
        for monster in self.monsters:
            # 计算欧氏距离的平方（避免开方运算，不影响距离比较结果）
            distance = (monster[0] - self.player_pos.x) ** 2 + (monster[1] - self.player_pos.y) ** 2
            if distance < min_distance:
                min_distance = distance
                nearest_monster = monster

        if not nearest_monster:
            # 如果没有怪物，返回False
            return False

        # 按y坐标排序的怪物列表（保留用于可能的y坐标参考）
        sorted_monsters_by_y = sorted(self.monsters, key=lambda x: x[1])
        n = len(sorted_monsters_by_y)
        if n % 2 == 1:
            median_y = sorted_monsters_by_y[n // 2][1]
        else:
            median_y = (sorted_monsters_by_y[n // 2 - 1][1] + sorted_monsters_by_y[n // 2][1]) / 2

        # 使用最近的怪物作为目标点
        monster_point = Point(nearest_monster[0], median_y)

        if self.is_first_attack_monster:
            # 第一次攻击的位置调整逻辑，基于最近的怪物
            if monster_point.x >= self.player_pos.x and monster_point.x - 160 > 0:
                monster_point.x = monster_point.x - 160
                monster_direction = "right"  # 朝向玩家（右侧怪物面向左？这里根据实际需求调整）
            elif monster_point.x <= self.player_pos.x and monster_point.x + 160 < 1067:
                monster_point.x = monster_point.x + 160
                monster_direction = "left"  # 朝向玩家（左侧怪物面向右？这里根据实际需求调整）
            elif monster_point.x < self.player_pos.x < (monster_point.x + 160):
                if self.player_pos.x - monster_point.x < (monster_point.x + 160) - self.player_pos.x:
                    monster_point.x = monster_point.x - 160
                    monster_direction = "right"
                else:
                    monster_point.x = monster_point.x + 160
                    monster_direction = "left"

            self.is_first_attack_monster = False

        else:
            # 非第一次攻击，直接根据最近怪物位置判断方向
            if monster_point.x > self.player_pos.x:
                # 怪物在玩家右侧，玩家需要向右移动并朝向右侧
                if monster_point.x - 160 > 0:
                    monster_point.x = monster_point.x - 160
                monster_direction = "right"  # 玩家朝向右侧（怪物方向）
            elif monster_point.x < self.player_pos.x:
                # 怪物在玩家左侧，玩家需要向左移动并朝向左侧
                if monster_point.x + 160 < 1067:
                    monster_point.x = monster_point.x + 160
                monster_direction = "left"  # 玩家朝向左侧（怪物方向）
            else:
                # 怪物与玩家x坐标相同，保持当前方向或默认向右
                monster_direction = "right"

        # 计算到最近怪物的移动信息
        move_info = self.compute_move_info(self.player_pos, monster_point, 0, 0)

        # 执行移动
        self.movement_recorder.left_right_up_down_move_by(move_info, False)
        # 发送方向指令，确保玩家朝向怪物
        pyauto.keyPressChar(monster_direction)

        logger.info("结束向最近怪物移动，朝向: {}".format(monster_direction))
        return True

    def process_detect_message(self, cls, game_image):
        """
        处理检测到的消息，根据消息内容更新游戏状态。

        Args:
            cls (list): 包含多个元组的列表，每个元组代表一个检测到的游戏元素（如玩家、物品、怪物等）。

        每个元组的结构通常为 [元素类型, x坐标, y坐标, 宽度, 高度]。
        """
        # 清除之前存储的游戏元素信息
        self.attack_boss_sy.clear()  # 清除深渊机制物品坐标
        self.goods.clear()  # 清除物品列表
        self.doors.clear()  # 清除门列表
        self.monsters.clear()  # 清除怪物列表
        self.box.clear()  # 清除障碍列表
        self.forward = False  # 重置前进方向
        # 重置奖励和继续标志
        self.has_rewards = False  # 是否有奖励
        self.has_continue = False  # 是否有继续游戏的选项
        # 重置玩家位置
        self.player_pos = Point(None, None)  # 初始化玩家位置为None
        # logger.info(f"物品列表已清空:{self.goods}")
        # logger.info(f"门列表已清空:{self.doors}")
        # logger.info(f"怪物列表已清空:{self.monsters}")
        # logger.info(f"障碍列表已清空:{self.box}")
        # count = 0
        # 遍历检测到的每个元素
        goods = []
        for data in cls:
            logger.info(f"data:{data}")
            # 处理玩家位置
            if data[0] == "player":
                # if (item[1] + item[3]) / 2 < 1180:
                if data[4] + self.player.player_height < 620:
                    self.player_pos.x = (data[1] + data[3]) / 2  # 玩家x坐标取边界中点
                    self.player_pos.y = data[4] + self.player.player_height  # 玩家y坐标考虑玩家高度
                else:
                    logger.info(f"玩家位置识别错误！！！")
            # 处理物品
            elif data[0].startswith("attack_boss_sy"):
                # 如果物品位置在特定区域外，也跳过
                if 5 < data[1] < 22 and 408 < data[2] < 425:
                    continue
                x = (data[1] + data[3]) / 2  # 门x坐标取边界中点
                y = data[4]
                self.attack_boss_sy.append((x, y))  # 将attack_boss_sy添加到列表中

            # 处理继续游戏的选项
            elif data[0] == "continue":
                x = (data[1] + data[3]) / 2  # 门x坐标取边界中点
                y = (data[2] + data[4]) / 2  # 门x坐标取边界中点
                box = (871, 29, 1013, 79)  # 矩形框的坐标：(左, 上, 右, 下)
                if box[0] < x < box[2] and box[1] < y < box[3]:
                    self.has_continue = True  # 标记有继续游戏的选项
                    self.is_boss = True  # 假设遇到继续即视为Boss关
                logger.info(f"{data}")
                continue
            elif data[0].startswith("goods") and data[5] > 0.5:
                if not self.is_boss and self.player.map_name == "深渊：终末崇拜者":
                    logger.info(f"刷深渊中，当前不是boss房不捡物品")
                    continue
                # 如果物品位置在特定区域外，也跳过
                if 5 < data[1] < 22 and 340 < data[2] < 354:
                    continue
                goods.append((int(data[1]), int(data[2]), int(data[3]), int(data[4])))  # 将物品添加到列表中  # x = (data[1] + data[3]) / 2  # 物品x坐标取边界中点  # y = data[4] + 25  # 物品y坐标调整  # self.goods.append((x, y))  # 将物品添加到列表中  # logger.info(f"物品x = {x}\ty = {y}")

            # 处理怪物和Boss
            elif data[0].startswith(("monster", "boss")):
                logger.info(data)

                # 计算怪物x坐标（所有怪物类型通用）
                x = (data[1] + data[3]) / 2

                # 计算怪物y坐标（根据不同怪物类型进行调整）
                y = data[4]  # 默认值

                if data[0].startswith("boss") and data[5] > 0.5:
                    # 从地图BOSS信息中获取高度数据
                    boss_info = map_boss_info.get(self.player.map_name, "").get(data[0])
                    if boss_info:
                        y += boss_info.get('height', 0)  # 使用height值，如果没有则默认为0
                        min_rooms = MAP_MIN_ROOMS.get(self.player.map_name, 2)
                        logger.info(f"yolo处理 最少房间要求为：{min_rooms}")
                        if self.getOpenedRoomsCount() >= min_rooms:
                            logger.info(f"yolo处理 当前房间是boss房")
                            self.is_boss = True  # 假设遇到继续即视为Boss关
                    else:
                        logger.info(f"当前地图：{self.player.map_name},识别的数据：{data}，不是本地图的怪物，应该是识别错误已跳过本条信息处理")
                        continue
                elif data[0] == "monster_frost":
                    # 冰霜怪物不需要额外调整
                    pass
                elif data[0].startswith("monster_115"):
                    # 从地图BOSS信息中获取高度数据
                    monster_info = map_boss_info.get(self.player.map_name, "").get(data[0])
                    if monster_info:
                        y += monster_info.get('height', 0)  # 使用height值，如果没有则默认为0
                else:
                    # 其他怪物类型的默认调整
                    y += 120

                # 将怪物添加到列表中
                self.monsters.append((x, y))
                if data[0].startswith("boss_sy") and self.player.map_name == "深渊：终末崇拜者" and self.to_door_count >= 3:
                    logger.info(f"当前过门次数self.to_door_count：{self.to_door_count}")
                    self.is_boss = True  # 假设遇到继续即视为Boss关
                    continue

            # 处理门
            elif data[0].startswith("door"):
                x = (data[1] + data[3]) / 2  # 门x坐标取边界中点
                y = data[4] - 17.5  # 门y坐标调整
                if self.player.map_name == "风暴逆鳞普通":
                    if 291 < x < 824 and 474 < y < 600:
                        y = 600
                else:
                    room_info = a_DictInfo.get(self.player.map_name).get("down")
                    if room_info['min_x'] < x < room_info['max_x'] and y > 480:
                        if self.player.map_name == "德洛斯矿山外围":
                            y = 600
                        else:
                            y = 560
                # elif self.player.map_name == "德洛斯矿山外围" and y > 480 and self.door_direction == "down":
                #
                #
                # elif y > 480 and 250 < x < 933:
                #     y = 560
                self.doors.append(Point(x, y))  # 将门添加到列表中
            elif data[0].startswith("forward") and self.player.map_name == "深渊：终末崇拜者":
                self.forward = True
                if data[1] > 1067 / 2:
                    self.doors.append(Point(random.randint(1350, 1467), random.randint(400, 450)))  # 将门添加到列表中
                else:
                    continue
                    # self.doors.append(Point(random.randint(20, 30), random.randint(400, 450)))  # 将门添加到列表中



            # 处理奖励
            elif data[0] == "reward":
                # 判断是否在这个区域，不然可能误判
                x = (data[1] + data[3]) / 2  # 门x坐标取边界中点
                y = (data[2] + data[4]) / 2  # 门x坐标取边界中点
                box = (398, 0, 566, 72)  # 矩形框的坐标：(左, 上, 右, 下)
                if box[0] < x < box[2] and box[1] < y < box[3]:
                    self.has_rewards = True  # 标记有奖励
                    self.is_boss = True  # 假设遇到奖励即视为Boss关

            # 处理障碍
            elif data[0] == "box_lypb":
                x = (data[1] + data[3]) / 2  # 障碍x坐标取边界中点
                y = (data[4] + 90)  # 障碍y坐标取边界中点
                self.box.append(Point(x, y))  # 将障碍添加到列表中
        # recording_time = time.time()
        # if len(self.goods) > 0 and self.image_save_interval_time is None or len(self.goods) > 0 and recording_time - self.image_save_interval_time > 5:
        #     self.2  = recording_time
        #     self.save_count += 1
        #     filename = os.path.join("Images", f"{self.save_count}.png")
        #     game_image = screenshot_util.get_game_screenshot()
        #     cv2.imwrite(filename, game_image)  # 假设 pic 已经是有效的图像数据
        #     # 更新编号文件
        #     with open(self.counter_file, 'w') as f:
        #         f.write(str(self.save_count))
        #     logger.info(f"图片：{self.save_count}.png\t已保存")
        # 如果存在门、继续选项或奖励，则清除怪物列表（可能为了优化或逻辑需要）
        # if len(self.goods) > 0 or self.has_continue or self.has_rewards:
        #     self.doors.clear()
        room_id = self.player.player_room_id
        if gv.banzhuan == 0:
            should_process = (len(self.doors) > 0 or self.has_continue or self.has_rewards)
            if should_process:
                self.monsters.clear()
                if room_id not in self.doorOpenState:
                    self.doorOpenState[room_id] = True  # 记录已开门
        else:
            should_process = (not self.monsters or self.has_continue or self.has_rewards)
        current_room_id = self.player.player_room_id
        pickup_count = self.room_item_pickup_counts.get(current_room_id, 0)
        # 调试输出：打印两个条件的值
        logger.info(f"\n拾取物品的条件：\n\tshould_process : {should_process}"
                    f"\n\tself.doorOpenState.get(room_id) : {self.doorOpenState.get(room_id)}"
                    f"\n\tpickup_count : {pickup_count}")

        if (should_process or self.doorOpenState.get(room_id)) and pickup_count < 10:
            # 公共的商品处理逻辑
            filtered_goods = []
            for dx, dy, dx1, dy1 in goods:
                text = self.get_text(dx, dy, dx1, dy1, game_image)
                logger.info(f"识别物品：{text}")
                cleaned_text = re.sub(r'[^\u4e00-\u9fa5]', '', text)

                # 检查是否需要过滤此物品
                should_filter = any(
                    self.similarity(cleaned_text, item) >= SIMILARITY_THRESHOLD
                    for item in target_items
                )

                if should_filter:
                    logger.info(f"已筛选掉：{text}")
                else:
                    filtered_goods.append((dx, dy, dx1, dy1, cleaned_text))

            # 计算商品中心点坐标
            self.goods = [(int((dx + dx1) / 2), dy1 + 20, text) for dx, dy, dx1, dy1, text in filtered_goods]
            logger.info(f"self.goods:{self.goods}")

    def similarity(self, s1, s2):
        """计算字符串相似度（0-1）"""
        # 计算编辑距离
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            for j in range(n + 1):
                if i == 0:
                    dp[i][j] = j
                elif j == 0:
                    dp[i][j] = i
                else:
                    cost = 0 if s1[i - 1] == s2[j - 1] else 1
                    dp[i][j] = min(dp[i - 1][j] + 1,  # 删除
                                   dp[i][j - 1] + 1,  # 插入
                                   dp[i - 1][j - 1] + cost)  # 替换

        distance = dp[m][n]
        max_len = max(m, n)
        return 1 - distance / max_len if max_len > 0 else 1.0

    def min_map_process_detect_message(self, cls):
        self.player.player_room_id = None
        self.query_room_id = None
        self.elite_room_id = None
        self.boss_room_id = None
        self.special_room_id = None
        query_room_id_list = []
        elite_room_id_list = []
        for data in cls:
            # if data[5] > 0.6:
            # logger.info(f"item:{item[0]}")
            # 处理玩家位置
            if data[0] == "map_hero":
                x = int((data[1] + data[3]) / 2)
                y = int((data[2] + data[4]) / 2)
                self.player.player_room_id = miniMapUtil.compute_room_id(x, y)
                logger.info(f"{data[0]}_room_id:{self.player.player_room_id}")
                x, y = self.player.player_room_id
                self.room_info_map[x][y] = 0
            if data[0] == "map_boss":
                x = int((data[1] + data[3]) / 2)
                y = int((data[2] + data[4]) / 2)
                self.boss_room_id = miniMapUtil.compute_room_id(x, y)
                logger.info(f"{data[0]}_room_id:{self.boss_room_id}")
                x, y = self.boss_room_id
                self.room_info_map[x][y] = 0
            if data[0].startswith("map_query"):
                x = int((data[1] + data[3]) / 2)
                y = int((data[2] + data[4]) / 2)
                xy = miniMapUtil.compute_room_id(x, y)
                logger.info(f"{data[0]}_room_id:{xy}")
                query_room_id_list.append(xy)
            if data[0] == "map_elite":
                x = int((data[1] + data[3]) / 2)
                y = int((data[2] + data[4]) / 2)
                # 计算房间位置
                xy = miniMapUtil.compute_room_id(x, y)
                logger.info(f"{data[0]}_room_id:{xy}")
                elite_room_id_list.append(xy)
            if data[0] == "map_special":
                x = int((data[1] + data[3]) / 2)
                y = int((data[2] + data[4]) / 2)
                # 计算房间位置
                self.special_room_id = miniMapUtil.compute_room_id(x, y)
                logger.info(f"{data[0]}_room_id:{self.special_room_id}")
                elite_room_id_list.append(self.special_room_id)

        screen_out = []
        if self.player.map_name == "德洛斯矿山外围" and self.player.player_room_id == (1, 4):
            logger.info("矿山这里向上")
            query_room_id_list.append((0, 4))
        if self.player.map_name == "德洛斯矿山外围" and self.player.player_room_id == (1, 5):
            logger.info("矿山这里向左")
            query_room_id_list.append((1, 4))
        # 如果问号房间和boss房间不为空，找到最接近boss房间的问号房间
        if query_room_id_list and self.boss_room_id:
            if self.player.map_name == "德洛斯矿山外围" and len(query_room_id_list) > 1:
                self.query_room_id = max(query_room_id_list, key=lambda x: x[0])
            else:
                # 初始化最小距离为无穷大，以及最近的坐标
                min_distance = float('inf')
                # 遍历坐标列表
                for coord in query_room_id_list:
                    # 计算当前坐标与target的距离的平方（避免使用sqrt以提高效率）
                    distance_squared = (coord[0] - self.player.player_room_id[0]) ** 2 + (coord[1] - self.player.player_room_id[1]) ** 2
                    # 如果当前距离的平方小于已知的最小距离的平方，则更新最小距离和最近的坐标
                    if distance_squared < min_distance:
                        min_distance = distance_squared
                        self.query_room_id = coord
                        screen_out.append(coord)
        # 如果精英房间和人物房间不为空，找到最接近人物房间的精英房间
        if elite_room_id_list and self.player.player_room_id:
            logger.info(f"精英房间和人物房间不为空,elite_room_id_list:{elite_room_id_list}")
            # 初始化最小距离为无穷大，以及最近的坐标
            min_distance = float('inf')
            # 遍历坐标列表
            for coord in elite_room_id_list:
                # 计算当前坐标与target的距离的平方（避免使用sqrt以提高效率）
                distance_squared = (coord[0] - self.player.player_room_id[0]) ** 2 + (coord[1] - self.player.player_room_id[1]) ** 2
                # 如果当前距离的平方小于已知的最小距离的平方，则更新最小距离和最近的坐标
                if distance_squared < min_distance:
                    min_distance = distance_squared
                    if min_distance == 1:
                        self.elite_room_id = coord
                        screen_out.append(coord)
                        logger.info(f"筛选出精英房间：{coord}")
        if self.player.map_name == "流雨瀑布":
            # 如果精英房间和人物房间不为空，找到最接近人物房间的精英房间
            if screen_out and self.boss_room_id:
                logger.info(f"精英房间或问号房间不为空:{screen_out},取最接近boss房的房间设置为问号房间，因为问号房间优先")
                # 初始化最小距离为无穷大，以及最近的坐标
                min_distance = float('inf')
                # 遍历坐标列表
                for coord in screen_out:
                    # 计算当前坐标与target的距离的平方（避免使用sqrt以提高效率）
                    distance_squared = (coord[0] - self.boss_room_id[0]) ** 2 + (coord[1] - self.boss_room_id[1]) ** 2
                    # 如果当前距离的平方小于已知的最小距离的平方，则更新最小距离和最近的坐标
                    if distance_squared < min_distance:
                        min_distance = distance_squared
                        self.query_room_id = coord
                        logger.info(f"取最接近boss房的房间设置为问号房间：{coord}")
        if self.player.player_room_id is None and self.boss_room_id and self.special_room_id:
            priority_direction = 'right'
            # 查找终点房间的路径
            end_direction = a_star(self.room_info_map, self.special_room_id, self.boss_room_id, priority_direction)
            if end_direction is not None:
                logger.info(f"special_room_id到boss_room_id路径:{end_direction}")
                logger.info(f"获取不到玩家所在房间时，特殊房间到boss房间路径能走通，玩家应该在boss房，不做特殊处理")
            else:
                self.player.player_room_id = self.special_room_id
                logger.info(f"获取不到玩家所在房间时，特殊房间到boss房间路径走不通，则玩家当前在特殊房间{self.player.player_room_id}")
                if elite_room_id_list and self.player.player_room_id:
                    logger.info(f"精英房间和人物房间不为空,elite_room_id_list:{elite_room_id_list}")
                    # 初始化最小距离为无穷大，以及最近的坐标
                    min_distance = float('inf')
                    # 遍历坐标列表
                    for coord in elite_room_id_list:
                        # 计算当前坐标与target的距离的平方（避免使用sqrt以提高效率）
                        distance_squared = (coord[0] - self.player.player_room_id[0]) ** 2 + (coord[1] - self.player.player_room_id[1]) ** 2
                        # 如果当前距离的平方小于已知的最小距离的平方，则更新最小距离和最近的坐标
                        if distance_squared < min_distance:
                            min_distance = distance_squared
                            if min_distance == 1:
                                self.elite_room_id = coord
                                screen_out.append(coord)
                                logger.info(f"筛选出精英房间：{coord}")

    def send_with_retry(self, data, message):
        """封装发送逻辑，带自动重连"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.sock.sendall(data)
                logger.info(f"成功发送 {message}")
                return True
            except socket.error as e:
                logger.info(f"发送失败（尝试 {attempt + 1}/{max_retries}）: {e}")
                traceback.print_exc()
                self._reconnect()
                time.sleep(3)
        return False

    def _reconnect(self):
        """关闭旧连接并建立新连接"""
        server_address = (gv.server_ip, gv.server_port)
        logger.info(server_address)
        self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(server_address)
        self.sock.settimeout(5.0)

    def get_yolo_res(self, game_image=None):
        try:
            logger.info(f"进入 get_yolo_res")
            if game_image is None:
                # st = time.time()
                logger.info(f"开始截图")
                game_image = screenshot_util.get_game_screenshot()  # logger.info(f"截图用时：{time.time() - st}")  # game_image = Capture(hwnd, 0, 0, 1067, 600)
                logger.info(f"截图完毕")
            # 1. 转换图片为二进制
            img_bytes = cv2.imencode('.jpg', game_image)[1].tobytes()
            image_size = len(img_bytes)

            # 2. 创建消息头
            header_data = json.dumps({"type": "game_windows", "width": 1067, "height": 600, "image_size": image_size  # 添加图片大小到header
                                      }).encode('utf-8')

            # 3. 打包消息头长度（4字节）
            header_length = struct.pack('!I', len(header_data))

            # 4. 发送数据（带自动重试）
            if not self.send_with_retry(header_length, "消息头长度"):
                return False

            if not self.send_with_retry(header_data, "消息头内容"):
                return False

            if not self.send_with_retry(img_bytes, f"图片数据({image_size}字节)"):
                return False

            # 接收服务端的返回信息
            # 假设这里已经连接到服务端，并且sock是socket对象
            header, cls = self.receive_message_from_server()
            if header["type"] == "game_windows":
                # if game_image is None:
                #     cls = self.yolo.detect()
                # else:
                #     cls = self.yolo.detect_by_img(game_image)
                self.process_detect_message(cls, game_image)
            logger.info(f"退出 get_yolo_res")

        except Exception as e:
            logger.info(f"发送过程中发生未处理异常: {e}")
            traceback.print_exc()
            self._reconnect()
            return False

        return True

    def _recv_exact(self, n):
        """确保接收指定长度的数据"""
        buf = bytearray(n)
        received = 0
        while received < n:
            chunk = self.sock.recv(min(n - received, 4096))
            if not chunk:
                raise ConnectionError("连接意外关闭")
            buf[received:received + len(chunk)] = chunk
            received += len(chunk)
        return bytes(buf)

    def receive_message_from_server(self):
        """
        从服务器接收完整消息（含协议头+数据）

        返回:
            tuple: (header_dict, data_bytes)
                   header_dict: 解析后的消息头字典
                   data_bytes: 原始数据字节流
        异常:
            ConnectionError: 接收过程中连接中断
            ValueError: 协议格式错误
        """

        try:
            # 接收消息头长度
            header_len_buf = self._recv_exact(4)
            header_len = struct.unpack('!I', header_len_buf)[0]

            # 接收并解析消息头
            header_data = self._recv_exact(header_len)
            header = json.loads(header_data.decode('utf-8'))

            # 验证必要字段
            if 'type' not in header or 'data_size' not in header:
                raise ValueError("无效的协议头格式")

            # 接收实际数据
            data_size = header['data_size']
            data_buf = self._recv_exact(data_size)
            data = json.loads(data_buf.decode('utf-8'))

            return header, data

        except (OSError, json.JSONDecodeError) as e:
            logger.exception(f"接收消息失败:{e}")
            traceback.print_exc()
            raise ConnectionError("连接异常")

    def get_text(self, x1, y1, x2, y2, img_numpy=None, amplify=False):
        try:
            logger.info(f"进入 ocr")
            if img_numpy is not None:
                game_image = img_numpy[y1:y2, x1:x2]

            else:
                img_numpy = screenshot_util.get_game_screenshot()
                game_image = img_numpy[y1:y2, x1:x2]
            if amplify:
                # 定义缩放比例（例如放大2倍）
                scale_factor = 1.5

                # 计算新尺寸
                new_width = int(game_image.shape[1] * scale_factor)
                new_height = int(game_image.shape[0] * scale_factor)
                new_size = (new_width, new_height)

                # 按比例放大图像
                game_image = cv2.resize(game_image, new_size, interpolation=cv2.INTER_LINEAR)
            _image_rgb = cv2.cvtColor(game_image, cv2.COLOR_BGR2GRAY)
            # 1. 转换图片为二进制
            img_bytes = cv2.imencode('.jpg', _image_rgb)[1].tobytes()
            image_size = len(img_bytes)

            # 2. 创建消息头
            header_data = json.dumps({"type": "ocr", "width": 1, "height": 1, "image_size": image_size  # 添加图片大小到header
                                      }).encode('utf-8')

            # 3. 打包消息头长度（4字节）
            header_length = struct.pack('!I', len(header_data))

            # 4. 发送数据（带自动重试）
            if not self.send_with_retry(header_length, "消息头长度"):
                return False

            if not self.send_with_retry(header_data, "消息头内容"):
                return False

            if not self.send_with_retry(img_bytes, f"图片数据({image_size}字节)"):
                return False

            # 接收服务端的返回信息
            # 假设这里已经连接到服务端，并且sock是socket对象
            header, response = self.receive_message_from_server()
            if header["type"] == "ocr":
                logger.info(f"ocr 已获取识别数据: {response}")

            logger.info(f"退出 ocr")

        except Exception as e:
            logger.exception(f"发送过程中发生未处理异常:{e}")
            traceback.print_exc()
            self._reconnect()
            return ''

        return response

    def get_min_map_yolo_res(self):
        # global min_map_name
        try:
            logger.info(f"进入 get_min_map_yolo_res")
            min_map = miniMapUtil.min_map_capture(self.player.map_name)
            logger.info(f"get_min_map_yolo_res")
            # cv2.imwrite(f"D:/automatic-painting/min_map/{min_map_name}.png", min_map)
            # min_map_name += 1
            # 1. 转换图片为二进制
            img_bytes = cv2.imencode('.jpg', min_map)[1].tobytes()
            image_size = len(img_bytes)

            # 2. 创建消息头
            header_data = json.dumps({"type": "min_map", "width": 1, "height": 1, "image_size": image_size  # 添加图片大小到header
                                      }).encode('utf-8')

            # 3. 打包消息头长度（4字节）
            header_length = struct.pack('!I', len(header_data))

            # 4. 发送数据（带自动重试）
            if not self.send_with_retry(header_length, "消息头长度"):
                return False

            if not self.send_with_retry(header_data, "消息头内容"):
                return False

            if not self.send_with_retry(img_bytes, f"图片数据({image_size}字节)"):
                return False

            # 接收服务端的返回信息
            # 假设这里已经连接到服务端，并且sock是socket对象
            header, cls = self.receive_message_from_server()
            if header["type"] == "min_map":
                logger.info(f"get_min_map_yolo_res 已获取识别数据: {cls}")
                self.min_map_process_detect_message(cls)

            logger.info(f"退出 get_min_map_yolo_res")

        except Exception as e:
            logger.exception(f"发送过程中发生未处理异常:{e}")
            traceback.print_exc()
            self._reconnect()
            return False

        return True

    def deposit_goods(self):
        if self.player.map_name in ("跌宕群岛", "妖气追踪"):
            return
        logger.info("回赛丽亚旅馆存金币")
        self.send_log("回赛丽亚旅馆存金币")
        pyauto.keyPressChar(back_to_selia_value)
        time.sleep(0.2)
        pyauto.keyPressChar("space")
        time.sleep(1)
        start_time = time.time()
        r = 1
        while self.running and r == 1:
            text = self.get_text(862, 296, 905, 317)
            pattern = r'[\u4e00-\u9fa5]+'
            # 使用 re.findall() 找出所有匹配的内容
            matches = re.findall(pattern, text)
            t = "".join(matches)
            for char in "邮件箱":
                if char in t:
                    r = 0
                    break
            else:
                logger.info(f"回赛丽亚旅馆存金币识别邮箱：{t}")
                time.sleep(0.2)
                if time.time() - start_time > 10:
                    logger.info("回赛丽亚旅馆存金币超时")
                    self.send_log("回赛丽亚旅馆存金币超时")
                    return
        # 点箱子
        self.operator_module.move_to(368, 370)
        time.sleep(1)
        pyauto.click()
        time.sleep(0.5)
        self.operator_module.move_to(743, 161)
        time.sleep(0.1)
        ret = self.mm.FindPic_sleep(0, 0, 1067, 600, "账号金库.bmp|账号金库a.bmp", 0.9, 1, time_s=5)
        if ret:
            x, y = ret[0][1], ret[0][2]
            # 点账号金库
            self.operator_module.move_to(x, y)
            time.sleep(1)
            pyauto.click()
            time.sleep(0.1)
            pyauto.click()
            time.sleep(0.1)
        ret = self.mm.FindPic(0, 0, 1067, 600, "存入.bmp", 0.9, 1)
        if ret:
            x, y = ret[0][1], ret[0][2]
            qy = ret[0][2]
            # 点存入
            self.operator_module.move_to(x, y)
            time.sleep(1)
            pyauto.click()
            time.sleep(0.1)
            pyauto.click()
            time.sleep(0.1)
        ret = self.mm.FindPic(0, 0, 1067, 600, "一次性转存.bmp", 0.9, 1)
        if ret:
            x, y = ret[0][1], ret[0][2]
            # 点存入
            self.operator_module.move_to(x, y)
            time.sleep(0.1)
            pyauto.click()
            time.sleep(1)
            pyauto.keyPressChar('space')
            time.sleep(0.1)
            pyauto.keyPressChar('space')
            time.sleep(0.1)
            self.operator_module.move_to(743, 161)
            time.sleep(0.1)
            pyauto.keyPressChar("esc")
            time.sleep(0.1)

    def process_pass(self):
        """
        打完boss
        :return:
        """
        skill_util.is_release_boss_skill = False
        if self.has_rewards and self.first_press_to_exit:
            logger.info("boss房有奖励")
            time.sleep(0.5)
            # 使用random.choice()从字符串中随机选择一个字符
            random_char = random.choice("1234")
            pyauto.keyPressChar(random_char)
            time.sleep(0.1)
            pyauto.keyPressChar("esc")
            time.sleep(0.1)
            self.first_press_to_exit = False
            return False
        # if self.has_continue:
        # 买门票、玛瑙
        if self.player.map_name in ("深渊：终末崇拜者", "跌宕群岛", "妖气追踪"):
            ret = self.mm.FindPic(152, 505, 248, 549, "一键出售.bmp", 0.85)
            if ret:
                ret = self.mm.FindPic(62, 433, 304, 510, "歼灭门票.bmp|玛瑙.bmp|闪闪明的闪亮谢礼.bmp", 0.85, 1)
                if ret:
                    for r in ret:
                        x, y = r[1], r[2]
                        self.operator_module.move_to(x, y)
                        pyauto.click()
                        time.sleep(0.2)
                        pyauto.click()
                        time.sleep(0.2)
        if self.player.map_name != "深渊：终末崇拜者":
            ret = self.mm.FindPic(152, 505, 248, 549, "一键出售.bmp", 0.85)
            if ret:
                if self.player.map_name == "风暴逆鳞普通":
                    time.sleep(2.5)
                # 聚物捡东西
                self.agg_pick_up_goods()
                self.send_log(f"当前刷图次数{self.brush_cnt + 1}")

                if self.brush_cnt % 16 == 0 and self.player.map_name not in ("深渊：终末崇拜者", "跌宕群岛", "妖气追踪"):
                    self.operator_module.sale_goods(self.sell)
                pl_value = self.operator_module.ocr_pl(self.get_text, self.send_log)
                # 识别到疲劳且小于预留
                if pl_value is not None and isinstance(pl_value, (int, float)) and pl_value <= self.player.pl_value:

                    if self.brush_cnt % 16 != 0 and self.player.map_name not in ("深渊：终末崇拜者", "跌宕群岛", "妖气追踪"):  # 这几个图不出售
                        # 出售装备、材料
                        self.operator_module.sale_goods(self.sell)
                    # update_role_brush_date(self.current_role_group, self.current_role_index)
                    role_settings = self.all_role_settings[self.current_role_index]
                    # 更新状态到数据库
                    dic_data = {'career': role_settings['career'],
                                'convert_career': role_settings['convert_career'],
                                'height': role_settings['height'],
                                'map': role_settings['map'],
                                'difficulty': role_settings['difficulty'],
                                "brush_map_expire_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'leave_pl': self.player.pl_value}
                    test_update_subgroup_config(self.dic.get("cookies"), self.current_role_group, self.current_role_index, dic_data)
                    self.operator_module.click_menu_item("返回城镇")
                    time.sleep(0.5)
                    ret = self.mm.FindPic(0, 0, 1067, 600, "关闭.bmp", 0.9)
                    if ret:
                        x, y = ret[0][1], ret[0][2]
                        self.operator_module.move_to(x, y)
                        pyauto.click()
                        time.sleep(0.5)
                    # 存金币
                    self.deposit_goods()
                    # if self.player.map_name == "风暴逆鳞普通" or self.player.map_name == "流雨瀑布" or self.player.map_name == "海伯伦的预言所":
                    #     # 存金币
                    #     self.deposit_goods()
                    #     pass  # 分解史诗  # self.sell()
                    # 每日任务
                    if self.player.is_daily_tasks == "是":
                        self.daily_tasks()
                    self.brush_running = False
                    self.first_press_to_exit = True
                    self.direction_dic.clear()
                    self.is_boss = False
                    self.to_door_count = 0
                    self.room_item_pickup_counts.clear()
                    self.doorOpenState.clear()
                    return True
                start_time = time.time()  # 记录当前时间作为开始时间
                direction = 'left'
                player_pos_none_count = 0
                while self.brush_running and not self.ghost_state:
                    end_time = time.time()  # 记录当前时间作为结束时间
                    execution_time = end_time - start_time  # 计算从开始到当前的执行时间
                    if execution_time > 30:  # 如果执行时间超过15秒
                        self.ghost_state = True  # 设置幽灵状态为True
                        self.send_log("物品没拾取完，再次挑战超时")
                        break  # 退出循环
                    # 收起结算评分否则如果还有物品可能识别不到
                    ret = self.mm.FindPic(901, 159, 969, 195, "减号.bmp", 0.97)
                    if ret:
                        x, y = ret[0][1], ret[0][2]
                        self.operator_module.move_to(x, y)
                        pyauto.click()
                        time.sleep(0.1)
                    ret = self.mm.FindPic(152, 505, 248, 549, "一键出售.bmp", 0.85)
                    if ret:
                        if self.player.map_name in ("深渊：终末崇拜者", "跌宕群岛", "妖气追踪"):
                            ret = self.mm.FindPic(62, 433, 304, 510, "歼灭门票.bmp|玛瑙.bmp|闪闪明的闪亮谢礼.bmp", 0.85, 1)
                            if ret:
                                for r in ret:
                                    x, y = r[1], r[2]
                                    self.operator_module.move_to(x, y)
                                    pyauto.click()
                                    time.sleep(0.2)
                                    pyauto.click()
                                    time.sleep(0.2)
                        pyauto.keyPressChar("esc")
                        time.sleep(0.2)
                        ret = self.mm.FindPic(357, 200, 456, 239, "我的信息.bmp", 0.85, delta_color=([0, 0, 0], [22, 255, 255]))
                        if ret:
                            # 点击关闭
                            self.operator_module.move_to(852, 59)
                            time.sleep(0.05)
                            pyauto.click()
                            time.sleep(0.1)
                    game_image = screenshot_util.get_game_screenshot()
                    if gv.banzhuan == 0:
                        pyauto.keyPressChar(challenge_again_value)
                    else:
                        pyauto.keyPressChar("space")
                    self.get_yolo_res(game_image)
                    # 再次检查是否还有物品
                    if len(self.goods) > 0:
                        self.send_log("boss房物品没拾取完，尝试拾取")
                        goods_pos = sort_points_by_x(self.goods)  # 对货物位置按x坐标排序
                        the_first_item = Point(goods_pos[0][0], goods_pos[0][1])
                        # if self.player_pos.x is not None and self.is_boss is False:
                        #     # 记录玩家的动态
                        #     self.player_dynamics_tuple.emit((self.player_pos.x, self.player_pos.y))
                        if self.player_pos.x is not None:
                            logger.info("人物坐标:{}\t{}\t物品坐标：{}\t{}".format(self.player_pos.x, self.player_pos.y, the_first_item.x, the_first_item.y))
                            if abs(self.player_pos.x - the_first_item.x) > 200:
                                move_info = self.compute_move_info(self.player_pos, the_first_item, 0, 0)  # 计算到最近货物的移动信息
                                logger.info("向物品奔跑：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                                self.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动
                            else:
                                move_info = self.compute_move_info_walk(self.player_pos, the_first_item, 0, 0)  # 计算到最近货物的移动信息
                                logger.info("向物品步行：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                                self.movement_recorder.left_right_up_down_move_walk_by(move_info, False)  # 根据移动信息移动
                            time.sleep(0.05)  # 暂停0.02秒
                            pyauto.releaseallkey()
                            time.sleep(0.05)
                            pyauto.keyDownChar('x')
                            time.sleep(random.uniform(1.5, 2.0))
                            pyauto.keyUpChar('x')
                            time.sleep(0.05)
                        else:
                            self.send_log("boss房物品没拾取完，未识别到人物位置")
                            if self.player_pos.x is None or self.player_pos.y is None:
                                logger.info("player_pos is none")
                                player_pos_none_count += 1
                                if player_pos_none_count > 30:
                                    self.movement_recorder.up_down_move("down", 0.2)
                                    self.player_left_right_move()

                    if not self.has_continue:
                        self.get_min_map_yolo_res()

                        if self.player.player_room_id is None:
                            time.sleep(0.1)
                            continue

                        if self.player.player_room_id:
                            logger.info('初始化地图:', self.room_info_map)
                            for room_list in self.room_info_map:
                                logger.info(room_list)
                            logger.info('地图名称:', self.player.map_name)
                            # 初始化地图
                            self.room_info_map = deepcopy(a_mapInfo.get(self.player.map_name))
                            logger.info('初始化地图')
                            for room_list in self.room_info_map:
                                logger.info(room_list)
                            self.brush_cnt += 1
                            self.first_press_to_exit = True
                            self.direction_dic.clear()
                            self.is_boss = False
                            self.to_door_count = 0
                            self.release_buffer()
                            self.pass_room_id.clear()
                            self.room_item_pickup_counts.clear()
                            self.doorOpenState.clear()
                            if self.player.player_occupation == "女魔法师-召唤师":
                                pyauto.keyPressChar("left")
                                time.sleep(0.05)
                                pyauto.keyPressChar("up")
                                time.sleep(0.05)
                                pyauto.keyPressChar("right")
                                time.sleep(0.05)
                                pyauto.keyPressChar("space")
                                time.sleep(0.05)
                            return True
                return True
        else:
            if self.has_continue:
                time.sleep(random.uniform(0.8, 1.2))
                self.agg_pick_up_goods()
                self.send_log(f"当前刷图次数{self.brush_cnt + 1}")
                pl_value = self.operator_module.ocr_pl(self.get_text, self.send_log)
                x1, y1, x2, y2 = (899, 77, 964, 96)
                min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                ret = self.mm.is_colored(min_img, 30)
                # 如果体力不为0、小于预留体力、ret是False代表按f10不能再刷
                if pl_value is not None and isinstance(pl_value, (int, float)) and pl_value <= self.player.pl_value or not ret:
                    role_settings = self.all_role_settings[self.current_role_index]
                    dic_data = {'career': role_settings['career'],
                                'convert_career': role_settings['convert_career'],
                                'height': role_settings['height'],
                                'map': role_settings['map'],
                                'difficulty': role_settings['difficulty'],
                                "brush_map_expire_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'leave_pl': self.player.pl_value}
                    test_update_subgroup_config(self.dic.get("cookies"), self.current_role_group, self.current_role_index, dic_data)
                    self.operator_module.click_menu_item("返回城镇")
                    time.sleep(0.5)
                    # 0点弹广告
                    ret = self.mm.FindPic(0, 0, 1067, 600, "关闭.bmp", 0.9)
                    if ret:
                        x, y = ret[0][1], ret[0][2]
                        self.operator_module.move_to(x, y)
                        pyauto.click()
                        time.sleep(0.5)

                    # if self.player.map_name == "风暴逆鳞普通" or self.player.map_name == "流雨瀑布" or self.player.map_name == "海伯伦的预言所":
                    #     # 存金币
                    #     self.deposit_goods()
                    #     pass  # 分解史诗  # self.sell()
                    # 每日任务
                    if self.player.is_daily_tasks == "是":
                        self.daily_tasks()
                    self.brush_running = False
                    self.first_press_to_exit = True
                    self.direction_dic.clear()
                    self.is_boss = False
                    self.to_door_count = 0
                    self.room_item_pickup_counts.clear()
                    self.doorOpenState.clear()
                start_time = time.time()  # 记录当前时间作为开始时间
                direction = 'left'
                player_pos_none_count = 0
                while self.brush_running and not self.ghost_state:
                    end_time = time.time()  # 记录当前时间作为结束时间
                    execution_time = end_time - start_time  # 计算从开始到当前的执行时间
                    if execution_time > 30:  # 如果执行时间超过15秒
                        self.ghost_state = True  # 设置幽灵状态为True
                        self.send_log("物品没拾取完，再次挑战超时")
                        break  # 退出循环
                    # 收起结算评分否则如果还有物品可能识别不到
                    ret = self.mm.FindPic(901, 159, 969, 195, "减号.bmp", 0.97)
                    if ret:
                        x, y = ret[0][1], ret[0][2]
                        self.operator_module.move_to(x, y)
                        pyauto.click()
                        time.sleep(0.1)

                    if self.mm.FindPic(152, 505, 248, 549, "一键出售.bmp", 0.85) or self.mm.FindPic(145, 22, 255, 54, "模糊的奥拉蔻.bmp", 0.85):
                        ret = self.mm.FindPic(62, 433, 304, 510, "歼灭门票.bmp|玛瑙.bmp|闪闪明的闪亮谢礼.bmp", 0.85, 1)
                        if ret:
                            for r in ret:
                                x, y = r[1], r[2]
                                self.operator_module.move_to(x, y)
                                pyauto.click()
                                time.sleep(0.2)
                                pyauto.click()
                                time.sleep(0.2)
                        pyauto.keyPressChar("esc")
                        time.sleep(0.2)
                        ret = self.mm.FindPic(357, 200, 456, 239, "我的信息.bmp", 0.85, delta_color=([0, 0, 0], [22, 255, 255]))
                        if ret:
                            # 点击关闭
                            self.operator_module.move_to(852, 59)
                            time.sleep(0.05)
                            pyauto.click()
                            time.sleep(0.1)
                    game_image = screenshot_util.get_game_screenshot()
                    pyauto.keyPressChar("f10")
                    self.get_yolo_res(game_image)
                    # 再次检查是否还有物品
                    if len(self.goods) > 0:
                        self.send_log("boss房物品没拾取完，尝试拾取")
                        goods_pos = sort_points_by_x(self.goods)  # 对货物位置按x坐标排序
                        the_first_item = Point(goods_pos[0][0], goods_pos[0][1])
                        # if self.player_pos.x is not None and self.is_boss is False:
                        #     # 记录玩家的动态
                        #     self.player_dynamics_tuple.emit((self.player_pos.x, self.player_pos.y))
                        if self.player_pos.x is not None:
                            logger.info("人物坐标:{}\t{}\t物品坐标：{}\t{}".format(self.player_pos.x, self.player_pos.y, the_first_item.x, the_first_item.y))
                            if abs(self.player_pos.x - the_first_item.x) > 200:
                                move_info = self.compute_move_info(self.player_pos, the_first_item, 0, 0)  # 计算到最近货物的移动信息
                                logger.info("向物品奔跑：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                                self.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动
                            else:
                                move_info = self.compute_move_info_walk(self.player_pos, the_first_item, 0, 0)  # 计算到最近货物的移动信息
                                logger.info("向物品步行：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                                self.movement_recorder.left_right_up_down_move_walk_by(move_info, False)  # 根据移动信息移动
                            time.sleep(0.05)  # 暂停0.02秒
                            pyauto.releaseallkey()
                            time.sleep(0.05)
                            pyauto.keyDownChar('x')
                            time.sleep(random.uniform(1.5, 2.0))
                            pyauto.keyUpChar('x')
                            time.sleep(0.05)
                        else:
                            self.send_log("boss房物品没拾取完，未识别到人物位置")
                            if self.player_pos.x is None or self.player_pos.y is None:
                                logger.info("player_pos is none")
                                player_pos_none_count += 1
                                if player_pos_none_count > 30:
                                    self.movement_recorder.up_down_move("down", 0.2)
                                    self.player_left_right_move()
                    if not self.has_continue:
                        self.get_yolo_res()
                        if not self.has_continue:
                            logger.info('初始化地图:', self.room_info_map)
                            for room_list in self.room_info_map:
                                logger.info(room_list)
                            logger.info('地图名称:', self.player.map_name)
                            # 初始化地图
                            self.room_info_map = deepcopy(a_mapInfo.get(self.player.map_name))
                            logger.info('初始化地图')
                            for room_list in self.room_info_map:
                                logger.info(room_list)
                            self.brush_cnt += 1
                            self.first_press_to_exit = True
                            self.direction_dic.clear()
                            self.is_boss = False
                            self.to_door_count = 0
                            self.release_buffer()
                            self.pass_room_id.clear()
                            self.room_item_pickup_counts.clear()
                            self.doorOpenState.clear()
                            if self.player.player_occupation == "女魔法师-召唤师":
                                pyauto.keyPressChar("left")
                                time.sleep(0.05)
                                pyauto.keyPressChar("up")
                                time.sleep(0.05)
                                pyauto.keyPressChar("right")
                                time.sleep(0.05)
                                pyauto.keyPressChar("space")
                                time.sleep(0.05)
                            return True
                return True
        return False

    def agg_pick_up_goods(self):
        """
        移动所有物品到脚下并拾取
        :return:
        """
        logger.info("boss房聚物拾取")
        pyauto.releaseallkey()
        time.sleep(0.05)
        pyauto.keyDownChar('up')
        time.sleep(0.4)
        pyauto.keyUpChar('up')
        time.sleep(0.05)
        for i in range(random.randint(3, 5)):
            pyauto.keyPressChar(one_key_gather_value)
            time.sleep(0.05)
        time.sleep(random.uniform(1, 1.5))
        start_time = time.time()
        while time.time() - start_time < 2.5:
            pyauto.keyDownChar('x')
            time.sleep(random.uniform(0.05, 0.07))
            pyauto.keyUpChar('x')
            time.sleep(random.uniform(0.05, 0.07))
            self.get_yolo_res()
            if not self.goods:
                break
        self.get_yolo_res()
        if len(self.goods) > 0:
            pyauto.keyDownChar('x')
            time.sleep(random.uniform(2, 2.5))
            pyauto.keyUpChar('x')
        time.sleep(0.05)

    def sell(self):
        """出售装备"""

        def calculate_brightness(img):
            # # 读取图像
            # img = cv2.imread(image_path)

            # 检查图像是否成功加载
            if img is None:
                logger.info("Error: 图像未成功加载。")
                return None

                # 如果图像是彩色的，转换为灰度图像
            if len(img.shape) == 3:
                gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                gray_img = img

                # 计算平均亮度
            # 注意：OpenCV中灰度图像的像素值范围是0-255
            brightness = np.mean(gray_img)

            return brightness

        y = 0
        ret = self.mm.FindPic_sleep(0, 0, 1067, 600, "装备1.bmp", 0.9, time_s=1, delta_color=([0, 0, 0], [0, 232, 255]))
        if ret:
            x, y = ret[0][1], ret[0][2]
        if y == 0:
            y = 292
        while self.brush_running:
            game_image = screenshot_util.get_game_screenshot()
            for row in range(3):
                for col in range(8):
                    x1 = 617 + col * 30
                    x2 = x1 + 30
                    y1 = y + 10 + row * 30
                    y2 = y1 + 30
                    min_img = game_image[y1:y2, x1:x2]
                    brightness = calculate_brightness(min_img)
                    logger.info(f"图像的平均亮度为: {brightness}")
                    # if 40 > brightness > 30:
                    #     self.operator_module.move_to(x1 + 15, y1 + 15)
                    #     time.sleep(0.1)
                    #     pyauto.click()
                    #     time.sleep(0.1)
                    if brightness > 30:
                        self.operator_module.move_to(x1 + 15, y1 + 15)
                        time.sleep(0.1)
                        pyauto.click()
                        time.sleep(0.1)
            self.operator_module.move_to(329, 464)
            time.sleep(0.05)
            pyauto.click()
            time.sleep(0.5)
            ret = self.mm.FindPic_sleep(0, 0, 1067, 600, "立即执行.bmp", 0.9, time_s=1, delta_color=([0, 0, 0], [0, 232, 255]))
            if ret:
                x, y = ret[0][1], ret[0][2]
                self.operator_module.move_to(x, y)
                time.sleep(0.05)
                pyauto.click()
                time.sleep(0.5)
                keyboard.write('立即执行', delay=random.uniform(0.05, 0.08))
                # self.operator_module.move_to(498, 463)
                # time.sleep(0.05)
                # pyauto.click()
                time.sleep(0.1)
            ret = self.mm.FindPic_sleep(0, 0, 1067, 600, "确认进行.bmp", 0.9, time_s=1, delta_color=([0, 0, 0], [0, 232, 255]))
            if ret:
                x, y = ret[0][1], ret[0][2]
                self.operator_module.move_to(x, y)
                time.sleep(0.05)
                pyauto.click()
                time.sleep(0.5)
                keyboard.write('确认进行', delay=random.uniform(0.05, 0.08))
                # self.operator_module.move_to(498, 463)
                # time.sleep(0.05)
                # pyauto.click()
                time.sleep(0.1)
            pyauto.keyPressChar("enter")
            time.sleep(0.1)
            pyauto.keyPressChar("space")
            time.sleep(0.1)
            pyauto.keyPressChar("esc")
            time.sleep(0.1)
            return

    # def sell(self):
    #     """次元风暴分解史诗"""
    #
    #     def calculate_brightness(img):
    #         # # 读取图像
    #         # img = cv2.imread(image_path)
    #
    #         # 检查图像是否成功加载
    #         if img is None:
    #             logger.info("Error: 图像未成功加载。")
    #             return None
    #
    #             # 如果图像是彩色的，转换为灰度图像
    #         if len(img.shape) == 3:
    #             gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #         else:
    #             gray_img = img
    #
    #             # 计算平均亮度
    #         # 注意：OpenCV中灰度图像的像素值范围是0-255
    #         brightness = np.mean(gray_img)
    #
    #         return brightness
    #
    #     while self.brush_running:
    #         click_status = self.operator_module.click_menu_item("传送阵")
    #         if not click_status:
    #             logger.info("点击传送阵失败")
    #             continue
    #         # 点击风暴次元
    #         self.operator_module.move_to(347, 282)
    #         pyauto.click()
    #
    #         time.sleep(1)
    #         # 点击分解机
    #         self.operator_module.move_to(41, 272)
    #         time.sleep(0.05)
    #         pyauto.click()
    #         time.sleep(0.1)
    #         for _ in range(3):
    #             ret = self.mm.FindPic_sleep(0, 170, 210, 720, "分解装备.bmp", 0.9, delta_color=([0, 0, 0], [19, 255, 255]), time_s=5)
    #             if ret:
    #                 x, y = ret[0][1], ret[0][2]
    #                 self.operator_module.move_to(x, y)
    #                 time.sleep(0.1)
    #                 pyauto.click()
    #
    #                 time.sleep(0.1)
    #                 break
    #         game_image = screenshot_util.get_game_screenshot()
    #         for row in range(3):
    #             for col in range(8):
    #                 x1 = 714 + col * 30
    #                 x2 = x1 + 30
    #                 y1 = 358 + row * 30
    #                 y2 = y1 + 30
    #                 min_img = game_image[y1:y2, x1:x2]
    #                 brightness = calculate_brightness(min_img)
    #                 logger.info(f"图像的平均亮度为: {brightness}")
    #                 if brightness > 40:
    #                     self.operator_module.move_to(x1 + 15, y1 + 15)
    #                     time.sleep(0.1)
    #                     pyauto.click()
    #
    #                     time.sleep(0.1)
    #         self.operator_module.move_to(560, 468)
    #         time.sleep(0.05)
    #         pyauto.click()
    #
    #         time.sleep(0.5)
    #         ret = self.mm.FindPic(419, 360, 527, 392, "高价值装备.bmp", 0.9, delta_color=([0, 0, 0], [0, 255, 255]))
    #         if ret:
    #             self.operator_module.move_to(444, 397)
    #             time.sleep(0.05)
    #             pyauto.click()
    #
    #             time.sleep(0.1)
    #             self.operator_module.move_to(498, 463)
    #             time.sleep(0.05)
    #             pyauto.click()
    #             time.sleep(0.1)
    #         pyauto.KeyPressChar("space")
    #         time.sleep(0.1)
    #         pyauto.KeyPressChar("space")
    #         time.sleep(0.1)
    #         time.sleep(6)
    #         pyauto.KeyPressChar("esc")
    #         time.sleep(0.1)
    #         return

    def daily_tasks(self):
        """
        每日任务
        :return:
        """

        def shuffle_list(lst):
            # 创建一个列表的副本
            shuffled_lst = lst[:]
            random.shuffle(shuffled_lst)
            return shuffled_lst

        for _ in range(2):
            pyauto.keyPressChar("f2")
            # yjs.KeyPressChar("f2")
            time.sleep(0.2)
            xy_list = [(492, 361), (497, 293), (492, 227)]
            game_image = screenshot_util.get_game_screenshot()
            text = self.get_text(159, 89, 242, 118, game_image)
            logger.info(f"识别文字：{text}")
            cleaned_text = re.sub(r'[^\u4e00-\u9fa5]', '', text)
            if self.similarity(cleaned_text, "每日任务") >= 0.7:
                shuffled_xy_list = shuffle_list(xy_list)
                for xy in shuffled_xy_list:
                    x, y = xy
                    self.operator_module.move_to(x, y)
                    time.sleep(0.1)
                    pyauto.click()

                    time.sleep(0.1)
                    pyauto.click()

                    pyauto.keyPressChar("space")
                    time.sleep(0.1)

                time.sleep(0.1)
                self.operator_module.move_to(498, 165)
                time.sleep(0.1)
                pyauto.click()

                time.sleep(0.1)
                pyauto.click()

                time.sleep(0.1)
                pyauto.click()

                time.sleep(1)
                break
            else:
                pyauto.keyPressChar("esc")
                time.sleep(0.2)

    def access_0(self):
        pyauto.keyPressChar("i")
        time.sleep(0.2)
        ret = self.mm.FindPic(609, 218, 861, 342, "消耗品.bmp", 0.9, 1)
        if ret:
            x, y = ret[0][1], ret[0][2]
            self.operator_module.move_to(x, y)
            time.sleep(0.1)
            pyauto.click()
            time.sleep(0.1)
            self.operator_module.move_to(870, 593)
            time.sleep(0.2)
            ret = self.mm.FindPic(607, 306, 862, 521, "金绿.bmp", 0.9, 1)
            if ret:
                for lis in ret:
                    self.operator_module.move_to(lis[1], lis[2])
                    time.sleep(1)
                    for _ in range(3):
                        pyauto.click(input_char='right')
                        time.sleep(0.2)
                        pyauto.keyPressChar("space")
                        time.sleep(0.2)

    def auto_pick(self):
        self.operator_module.move_to(33, 397)
        time.sleep(0.1)
        pyauto.click()
        time.sleep(0.1)
        ret = self.waiting_for_the_text_to_appear([387, 296, 474, 322], "开启自动捡物", r'[\u4e00-\u9fa5]+', 8)
        if ret:
            ret = self.mm.FindPic(358, 292, 396, 324, "未勾选.bmp", 0.9, 1)
            if ret:
                self.operator_module.move_to(376, 304)
                time.sleep(0.1)
                pyauto.click()
                time.sleep(0.1)
        self.operator_module.move_to(934, 105)
        time.sleep(0.1)
        pyauto.click()
        time.sleep(0.1)

    def waiting_for_the_text_to_appear(self, region: list, char: str, regular: str, timeout: float or int, amplify=False):
        start_time = time.time()
        while self.brush_running:
            text = self.get_text(*region, amplify=amplify)
            pattern = regular
            # 使用 re.findall() 找出所有匹配的内容
            matches = re.findall(pattern, text)
            t = "".join(matches)
            for char_ in char:
                if char_ in t:
                    return t
            if time.time() - start_time >= timeout:
                return ''
            time.sleep(0.1)

    def enter_map(self):
        while self.brush_running:
            ret = self.mm.FindPic(0, 0, 1067, 600, "关闭.bmp", 0.9)
            if ret:
                x, y = ret[0][1], ret[0][2]
                self.operator_module.move_to(x, y)
                pyauto.click()
                time.sleep(0.5)

            # if self.player.map_name != "德洛斯矿山外围":
            click_status = self.operator_module.click_menu_item("传送阵")
            if not click_status:
                logger.info("点击传送阵失败")
                continue
            if self.player.map_name == "风暴幽城":
                self.operator_module.move_to(347, 282)
                pyauto.click()

                time.sleep(0.5)

                pyauto.keyDownChar("right")
                while self.brush_running:
                    time.sleep(0.1)
                    ret = self.mm.FindPic(963, 536, 1066, 570, "返回城镇.bmp", 0.9)
                    if ret:
                        pyauto.keyUpChar("right")

                    else:
                        continue
                    ret = self.mm.FindPic(78, 277, 233, 329, "风暴幽城.bmp", 0.9)
                    if ret:
                        time.sleep(0.05)
                        pyauto.keyDownChar("shift")
                        time.sleep(0.05)
                        pyauto.keyDownChar("left")
                        time.sleep(0.05)
                        pyauto.keyUpChar("left")
                        time.sleep(0.05)
                        pyauto.keyUpChar("shift")
                        time.sleep(0.05)
                        for i in range(1, self.player.map_level, 1):
                            pyauto.keyPressChar("right")
                            time.sleep(0.2)
                        pyauto.keyPressChar("space")
                        time.sleep(0.1)
                        pyauto.keyPressChar("space")
                        time.sleep(0.5)
                        break
                    else:
                        pyauto.keyPressChar("down")
                        continue

            elif self.player.map_name == "风暴逆鳞普通":
                stat_time = time.time()
                while self.brush_running:
                    x1, y1, x2, y2 = (57, 97, 126, 105)
                    min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                    ret = self.mm.is_colored(min_img, 50)
                    if ret:
                        pyauto.keyPressChar("space")
                        time.sleep(0.2)
                        break
                    else:
                        pyauto.keyPressChar("up")
                        time.sleep(0.2)
                    if time.time() - stat_time > 10:
                        break
                # self.operator_module.move_to(239, 179)
                # time.sleep(0.2)
                # pyauto.click()
                # time.sleep(0.1)
                # pyauto.KeyPressChar("space")

                while self.brush_running:
                    """
                    如果没到拉比谢尔则再次打开传送阵，进行传送
                    """
                    ret = self.waiting_for_the_text_to_appear([883, 25, 970, 50], "比拉谢尔", r'[\u4e00-\u9fa5]+', 15)
                    if not ret:
                        click_status = self.operator_module.click_menu_item("传送阵")
                        if not click_status:
                            logger.info("点击传送阵失败")
                            continue
                        stat_time = time.time()
                        while self.brush_running:
                            x1, y1, x2, y2 = (57, 97, 126, 105)
                            min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                            ret = self.mm.is_colored(min_img, 50)
                            if ret:
                                pyauto.keyPressChar("space")
                                time.sleep(0.2)
                                break
                            else:
                                pyauto.keyPressChar("up")
                                time.sleep(0.2)
                            if time.time() - stat_time > 10:
                                break
                        # self.operator_module.move_to(239, 179)
                        # time.sleep(0.2)
                        # pyauto.click()
                        # time.sleep(0.2)
                    self.operator_module.open_window("世界地图")
                    time.sleep(0.2)
                    self.operator_module.move_to(725, 199)
                    time.sleep(0.2)
                    pyauto.click()
                    time.sleep(1)
                    pyauto.keyPressChar("n")
                    time.sleep(0.1)
                    ret = self.mm.FindPic_sleep(883, 25, 970, 50, "艾尔罗斯.bmp", 0.9, time_s=1, my_sleep=0.1)
                    if ret:
                        break
                pyauto.keyDownChar("right")
                ret = self.mm.FindPic_sleep(963, 536, 1066, 570, "返回城镇.bmp", 0.9, time_s=20)
                if ret:
                    pyauto.keyUpChar("right")
                    time.sleep(0.1)
                while self.brush_running:
                    ret = self.mm.FindPic(78, 277, 233, 329, "风暴逆鳞普通.bmp", 0.9)
                    if ret:
                        # text = self.get_text(162, 383, 256, 401)
                        # pattern = r'[0-9]+'
                        # # 使用 re.findall() 找出所有匹配的内容
                        # matches = re.findall(pattern, text)
                        # t = ''.join(matches)
                        # if t and int(''.join(t)) < 900:
                        x1, y1, x2, y2 = (162, 383, 256, 401)
                        min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                        ret = self.mm.is_colored(min_img, 15)
                        if not ret:
                            pyauto.keyPressChar("f12")
                            time.sleep(0.05)
                            pyauto.keyPressChar("f12")
                            time.sleep(0.05)
                            pyauto.keyPressChar("f12")
                            time.sleep(0.05)
                            return 0
                        time.sleep(0.05)
                        pyauto.keyDownChar("shift")

                        time.sleep(0.05)
                        pyauto.keyDownChar("left")

                        time.sleep(0.05)
                        pyauto.keyUpChar("left")

                        time.sleep(0.05)
                        pyauto.keyUpChar("shift")
                        # yjs.KeyUpChar("shift")
                        time.sleep(0.05)
                        for i in range(1, self.player.map_level, 1):
                            pyauto.keyPressChar("right")

                            time.sleep(0.2)
                        # 初始化地图
                        self.room_info_map = deepcopy(a_mapInfo.get(self.player.map_name))
                        logger.info('初始化地图')
                        for room_list in self.room_info_map:
                            logger.info(room_list)
                        while self.brush_running:
                            text = self.get_text(860, 0, 997, 23)
                            pattern = r'[0-9]+'
                            # 使用 re.findall() 找出所有匹配的内容
                            matches = re.findall(pattern, text)
                            t = ''.join(matches)
                            logger.info("标记1")
                            logger.info(t)
                            if t and int(t) > 0:
                                self.send_log("识别到频道，说明未进入地图入口")
                                return 0
                            # 得到玩家所在房间
                            self.get_min_map_yolo_res()
                            if self.player.player_room_id:
                                self.send_log("地图确认已进入地图")
                                break
                            else:
                                self.send_log("未检测到在图中,等待...")
                                pyauto.keyPressChar("space")
                                time.sleep(0.5)
                                continue
                        break
                    else:
                        pyauto.keyPressChar("down")
                        time.sleep(0.1)
                        continue

            elif self.player.map_name == "流雨瀑布":
                self.operator_module.move_to(869, 187)
                pyauto.click()

                time.sleep(0.5)
                self.operator_module.move_to(550, 289)
                pyauto.click()

                time.sleep(0.5)

                pyauto.keyDownChar("right")
                # yjs.KeyDownChar("right")
                while self.brush_running:
                    time.sleep(0.1)
                    ret = self.mm.FindPic(963, 536, 1066, 570, "返回城镇.bmp", 0.9)
                    if ret:
                        pyauto.keyUpChar("right")

                    else:
                        continue
                    ret = self.mm.FindPic(78, 277, 233, 329, "流雨瀑布.bmp", 0.9)
                    if ret:
                        time.sleep(0.05)
                        pyauto.keyDownChar("shift")

                        time.sleep(0.05)
                        pyauto.keyDownChar("left")

                        time.sleep(0.05)
                        pyauto.keyUpChar("left")

                        time.sleep(0.05)
                        pyauto.keyUpChar("shift")
                        time.sleep(0.05)
                        for i in range(1, self.player.map_level, 1):
                            pyauto.keyPressChar("right")

                            time.sleep(0.2)
                        pyauto.keyPressChar("space")

                        time.sleep(0.5)
                        break
                    else:
                        pyauto.keyPressChar("down")
                        time.sleep(0.1)
                        continue

            elif self.player.map_name == "海伯伦的预言所":
                self.operator_module.move_to(869, 187)
                pyauto.click()

                time.sleep(0.5)
                self.operator_module.move_to(900, 289)
                pyauto.click()

                time.sleep(0.5)

                pyauto.keyDownChar("right")
                while self.brush_running:
                    time.sleep(0.1)
                    ret = self.mm.FindPic(963, 536, 1066, 570, "返回城镇.bmp", 0.9)
                    if ret:
                        pyauto.keyUpChar("right")

                    else:
                        continue
                    ret = self.mm.FindPic(78, 277, 233, 329, "海伯伦的预言所.bmp", 0.9)
                    if ret:
                        time.sleep(0.05)
                        pyauto.keyDownChar("shift")

                        time.sleep(0.05)
                        pyauto.keyDownChar("left")

                        time.sleep(0.05)
                        pyauto.keyUpChar("left")

                        time.sleep(0.05)
                        pyauto.keyUpChar("shift")
                        time.sleep(0.05)
                        for i in range(1, self.player.map_level, 1):
                            pyauto.keyPressChar("right")

                            time.sleep(0.2)
                        pyauto.keyPressChar("space")

                        time.sleep(0.5)
                        break
                    else:
                        pyauto.keyPressChar("down")
                        time.sleep(0.1)
                        continue

            elif self.player.map_name == "深渊：终末崇拜者":
                stat_time = time.time()
                while self.brush_running:
                    x1, y1, x2, y2 = (59, 194, 133, 198)
                    min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]

                    ret = self.mm.is_colored(min_img, 50)
                    if ret:
                        pyauto.keyPressChar("space")
                        time.sleep(0.2)
                        break
                    else:
                        pyauto.keyPressChar("up")
                        time.sleep(0.2)
                    if time.time() - stat_time > 10:
                        break
                # self.operator_module.move_to(239, 179)
                # time.sleep(0.2)
                # pyauto.click()
                # time.sleep(0.1)
                # pyauto.KeyPressChar("space")

                while self.brush_running:
                    """
                    如果没到拉比谢尔则再次打开传送阵，进行传送
                    """
                    ret = self.waiting_for_the_text_to_appear([883, 25, 970, 50], "红矿村", r'[\u4e00-\u9fa5]+', 15)
                    if not ret:
                        click_status = self.operator_module.click_menu_item("传送阵")
                        if not click_status:
                            logger.info("点击传送阵失败")
                            continue
                        stat_time = time.time()
                        while self.brush_running:
                            x1, y1, x2, y2 = (59, 194, 133, 198)
                            min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                            ret = self.mm.is_colored(min_img, 50)
                            if ret:
                                pyauto.keyPressChar("space")
                                time.sleep(0.2)
                                break
                            else:
                                pyauto.keyPressChar("up")
                                time.sleep(0.2)
                            if time.time() - stat_time > 10:
                                break
                        # self.operator_module.move_to(239, 179)
                        # time.sleep(0.2)
                        # pyauto.click()
                        # time.sleep(0.2)
                    # self.operator_module.open_window("世界地图")
                    # time.sleep(0.2)
                    # self.operator_module.move_to(725, 199)
                    # time.sleep(0.2)
                    # pyauto.click()
                    # time.sleep(1)
                    # pyauto.KeyPressChar("n")
                    time.sleep(5)
                    ret = self.mm.FindPic_sleep(883, 25, 970, 50, "红矿村.bmp", 0.9, time_s=1, my_sleep=0.1)
                    if ret:
                        break
                pyauto.keyDownChar("right")
                time.sleep(random.uniform(0.8, 1.1))
                pyauto.keyUpChar("right")
                time.sleep(0.1)
                pyauto.keyDownChar("left")
                ret = self.mm.FindPic_sleep(963, 536, 1066, 570, "返回城镇.bmp", 0.9, time_s=20)
                if ret:
                    pyauto.keyUpChar("left")
                    time.sleep(0.1)
                while self.brush_running:
                    ret = self.mm.FindPic(78, 277, 233, 329, "深渊.bmp", 0.9)
                    if ret:
                        # text = self.get_text(232, 383, 295, 399)
                        # pattern = r'[0-9]+'
                        # # 使用 re.findall() 找出所有匹配的内容
                        # matches = re.findall(pattern, text)
                        # t = ''.join(matches)
                        # if t and int(''.join(t)) < 30:
                        x1, y1, x2, y2 = (232, 383, 295, 399)
                        min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                        ret = self.mm.is_colored(min_img, 15)
                        if not ret:
                            self.send_log("深渊票不足，跳过当前角色")
                            self.ghost_state = False
                            # update_role_brush_date(self.current_role_group, self.current_role_index)
                            role_settings = self.all_role_settings[self.current_role_index]
                            dic_data = {'career': role_settings['career'],
                                        'convert_career': role_settings['convert_career'],
                                        'height': role_settings['height'],
                                        'map': role_settings['map'],
                                        'difficulty': role_settings['difficulty'],
                                        "brush_map_expire_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        'leave_pl': self.player.pl_value}
                            test_update_subgroup_config(self.dic.get("cookies"), self.current_role_group, self.current_role_index, dic_data)
                            self.brush_running = False
                            return 0
                        # time.sleep(0.05)
                        # pyauto.KeyDownChar("shift")
                        #
                        # time.sleep(0.05)
                        # pyauto.KeyDownChar("left")
                        #
                        # time.sleep(0.05)
                        # pyauto.KeyUpChar("left")
                        #
                        # time.sleep(0.05)
                        # pyauto.KeyUpChar("shift")
                        # # yjs.KeyUpChar("shift")
                        # time.sleep(0.05)
                        # for i in range(1, self.player.map_level, 1):
                        #     pyauto.KeyPressChar("right")
                        #
                        #     time.sleep(0.2)
                        # 初始化地图
                        self.room_info_map = deepcopy(a_mapInfo.get(self.player.map_name))
                        logger.info('初始化地图')
                        for room_list in self.room_info_map:
                            logger.info(room_list)
                        while self.brush_running:
                            text = self.get_text(860, 0, 997, 23)
                            pattern = r'[0-9]+'
                            # 使用 re.findall() 找出所有匹配的内容
                            matches = re.findall(pattern, text)
                            t = ''.join(matches)
                            logger.info("标记1")
                            logger.info(t)
                            if t and int(t) > 0:
                                self.send_log("识别到频道，说明未进入地图入口")
                                return 0
                            game_image = screenshot_util.get_game_screenshot()
                            text = self.get_text(927, 2, 1031, 22, game_image)
                            logger.info(f"识别右上角文字：{text}")
                            cleaned_text = re.sub(r'[^\u4e00-\u9fa5]', '', text)
                            if self.similarity(cleaned_text, "深渊：终末崇拜者") >= 0.7:
                                break
                            else:
                                self.send_log("深渊图检测2——未检测到在图中,等待...")
                                pyauto.keyPressChar("space")
                                time.sleep(0.5)
                                continue
                        break
                    else:
                        pyauto.keyPressChar("down")
                        time.sleep(0.2)
                        continue
            elif self.player.map_name == "跌宕群岛":
                stat_time = time.time()
                while self.brush_running:
                    x1, y1, x2, y2 = (59, 194, 133, 198)
                    min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                    ret = self.mm.is_colored(min_img, 50)
                    if ret:
                        pyauto.keyPressChar("space")
                        time.sleep(0.2)
                        break
                    else:
                        pyauto.keyPressChar("up")
                        time.sleep(0.2)
                    if time.time() - stat_time > 10:
                        break
                # self.operator_module.move_to(239, 179)
                # time.sleep(0.2)
                # pyauto.click()
                # time.sleep(0.1)
                # pyauto.KeyPressChar("space")

                while self.brush_running:
                    """
                    如果没到拉比谢尔则再次打开传送阵，进行传送
                    """
                    ret = self.waiting_for_the_text_to_appear([883, 25, 970, 50], "红矿村", r'[\u4e00-\u9fa5]+', 15)
                    if not ret:
                        click_status = self.operator_module.click_menu_item("传送阵")
                        if not click_status:
                            logger.info("点击传送阵失败")
                            continue
                        stat_time = time.time()
                        while self.brush_running:
                            x1, y1, x2, y2 = (59, 194, 133, 198)
                            min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                            ret = self.mm.is_colored(min_img, 50)
                            if ret:
                                pyauto.keyPressChar("space")
                                time.sleep(0.2)
                                break
                            else:
                                pyauto.keyPressChar("up")
                                time.sleep(0.2)
                            if time.time() - stat_time > 10:
                                break
                        # self.operator_module.move_to(239, 179)
                        # time.sleep(0.2)
                        # pyauto.click()
                        # time.sleep(0.2)
                    # self.operator_module.open_window("世界地图")
                    # time.sleep(0.2)
                    # self.operator_module.move_to(725, 199)
                    # time.sleep(0.2)
                    # pyauto.click()
                    # time.sleep(1)
                    # pyauto.KeyPressChar("n")
                    time.sleep(5)
                    ret = self.mm.FindPic_sleep(883, 25, 970, 50, "红矿村.bmp", 0.9, time_s=1, my_sleep=0.1)
                    if ret:
                        break
                pyauto.keyDownChar("right")
                time.sleep(random.uniform(0.8, 1.1))
                pyauto.keyUpChar("right")
                time.sleep(0.1)
                pyauto.keyDownChar("left")
                ret = self.mm.FindPic_sleep(963, 536, 1066, 570, "返回城镇.bmp", 0.9, time_s=20)
                if ret:
                    pyauto.keyUpChar("left")
                    time.sleep(0.1)
                while self.brush_running:
                    ret = self.mm.FindPic(78, 277, 233, 329, "跌宕群岛.bmp", 0.9)
                    if ret:

                        time.sleep(0.05)
                        pyauto.keyDownChar("shift")

                        time.sleep(0.05)
                        pyauto.keyDownChar("left")

                        time.sleep(0.05)
                        pyauto.keyUpChar("left")

                        time.sleep(0.05)
                        pyauto.keyUpChar("shift")
                        # yjs.KeyUpChar("shift")
                        time.sleep(0.05)
                        for i in range(1, self.player.map_level, 1):
                            pyauto.keyPressChar("right")

                            time.sleep(0.2)
                        # 初始化地图
                        self.room_info_map = deepcopy(a_mapInfo.get(self.player.map_name))
                        logger.info('初始化地图')
                        for room_list in self.room_info_map:
                            logger.info(room_list)
                        while self.brush_running:
                            text = self.get_text(860, 0, 997, 23)
                            pattern = r'[0-9]+'
                            # 使用 re.findall() 找出所有匹配的内容
                            matches = re.findall(pattern, text)
                            t = ''.join(matches)
                            logger.info("标记1")
                            logger.info(t)
                            if t and int(t) > 0:
                                self.send_log("识别到频道，说明未进入地图入口")
                                return 0
                            # 得到玩家所在房间
                            self.get_min_map_yolo_res()
                            if self.player.player_room_id:
                                self.send_log("地图确认已进入地图")
                                break
                            else:
                                self.send_log("未检测到在图中,等待...")
                                pyauto.keyPressChar("space")
                                time.sleep(0.5)
                                continue
                        break
                    else:
                        pyauto.keyPressChar("down")
                        time.sleep(0.2)
                        continue
            elif self.player.map_name == "妖气追踪":
                stat_time = time.time()
                while self.brush_running:
                    x1, y1, x2, y2 = (59, 194, 133, 198)
                    min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                    ret = self.mm.is_colored(min_img, 50)
                    if ret:
                        pyauto.keyPressChar("space")
                        time.sleep(0.2)
                        break
                    else:
                        pyauto.keyPressChar("up")
                        time.sleep(0.2)
                    if time.time() - stat_time > 10:
                        break
                # self.operator_module.move_to(239, 179)
                # time.sleep(0.2)
                # pyauto.click()
                # time.sleep(0.1)
                # pyauto.KeyPressChar("space")

                while self.brush_running:
                    """
                    如果没到拉比谢尔则再次打开传送阵，进行传送
                    """
                    ret = self.waiting_for_the_text_to_appear([883, 25, 970, 50], "红矿村", r'[\u4e00-\u9fa5]+', 15)
                    if not ret:
                        click_status = self.operator_module.click_menu_item("传送阵")
                        if not click_status:
                            logger.info("点击传送阵失败")
                            continue
                        stat_time = time.time()
                        while self.brush_running:
                            x1, y1, x2, y2 = (59, 194, 133, 198)
                            min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                            ret = self.mm.is_colored(min_img, 50)
                            if ret:
                                pyauto.keyPressChar("space")
                                time.sleep(0.2)
                                break
                            else:
                                pyauto.keyPressChar("up")
                                time.sleep(0.2)
                            if time.time() - stat_time > 10:
                                break
                        # self.operator_module.move_to(239, 179)
                        # time.sleep(0.2)
                        # pyauto.click()
                        # time.sleep(0.2)
                    # self.operator_module.open_window("世界地图")
                    # time.sleep(0.2)
                    # self.operator_module.move_to(725, 199)
                    # time.sleep(0.2)
                    # pyauto.click()
                    # time.sleep(1)
                    # pyauto.KeyPressChar("n")
                    time.sleep(5)
                    ret = self.mm.FindPic_sleep(883, 25, 970, 50, "红矿村.bmp", 0.9, time_s=1, my_sleep=0.1)
                    if ret:
                        break
                pyauto.keyDownChar("right")
                time.sleep(random.uniform(0.8, 1.1))
                pyauto.keyUpChar("right")
                time.sleep(0.1)
                pyauto.keyDownChar("left")
                ret = self.mm.FindPic_sleep(963, 536, 1066, 570, "返回城镇.bmp", 0.9, time_s=20)
                if ret:
                    pyauto.keyUpChar("left")
                    time.sleep(0.1)
                while self.brush_running:
                    ret = self.mm.FindPic(78, 277, 233, 329, "妖气追踪.bmp", 0.9)
                    if ret:

                        time.sleep(0.05)
                        pyauto.keyDownChar("shift")

                        time.sleep(0.05)
                        pyauto.keyDownChar("left")

                        time.sleep(0.05)
                        pyauto.keyUpChar("left")

                        time.sleep(0.05)
                        pyauto.keyUpChar("shift")
                        # yjs.KeyUpChar("shift")
                        time.sleep(0.05)
                        for i in range(1, self.player.map_level, 1):
                            pyauto.keyPressChar("right")

                            time.sleep(0.2)
                        # 初始化地图
                        self.room_info_map = deepcopy(a_mapInfo.get(self.player.map_name))
                        logger.info('初始化地图')
                        for room_list in self.room_info_map:
                            logger.info(room_list)
                        while self.brush_running:
                            text = self.get_text(860, 0, 997, 23)
                            pattern = r'[0-9]+'
                            # 使用 re.findall() 找出所有匹配的内容
                            matches = re.findall(pattern, text)
                            t = ''.join(matches)
                            logger.info("标记1")
                            logger.info(t)
                            if t and int(t) > 0:
                                self.send_log("识别到频道，说明未进入地图入口")
                                return 0
                            # 得到玩家所在房间
                            self.get_min_map_yolo_res()
                            if self.player.player_room_id:
                                self.send_log("地图确认已进入地图")
                                break
                            else:
                                self.send_log("未检测到在图中,等待...")
                                pyauto.keyPressChar("space")
                                time.sleep(0.5)
                                continue
                        break
                    else:
                        pyauto.keyPressChar("down")
                        time.sleep(0.2)
                        continue
            if self.player.map_name == "德洛斯矿山外围":
                stat_time = time.time()
                while self.brush_running:
                    x1, y1, x2, y2 = (57, 146, 129, 152)
                    min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                    ret = self.mm.is_colored(min_img, 50)
                    if ret:
                        pyauto.keyPressChar("space")
                        time.sleep(0.2)
                        break
                    else:
                        pyauto.keyPressChar("up")
                        time.sleep(0.2)
                    if time.time() - stat_time > 10:
                        break
                # self.operator_module.move_to(240, 225)
                # time.sleep(0.2)
                # pyauto.click()
                # time.sleep(0.1)
                # pyauto.KeyPressChar("space")
                while self.brush_running:
                    # self.mm.FindPic_sleep(883, 25, 970, 50, "min_切斯特小镇.bmp", 0.9, time_s=10, my_sleep=0.1)
                    ret = self.waiting_for_the_text_to_appear([883, 25, 970, 50], '切斯特小镇', r'[\u4e00-\u9fa5]+', 15)
                    if not ret:
                        click_status = self.operator_module.click_menu_item("传送阵")
                        if not click_status:
                            logger.info("点击传送阵失败")
                            continue
                        stat_time = time.time()
                        while self.brush_running:
                            x1, y1, x2, y2 = (57, 146, 129, 152)
                            min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                            ret = self.mm.is_colored(min_img, 50)
                            if ret:
                                pyauto.keyPressChar("space")
                                time.sleep(0.2)
                                break
                            else:
                                pyauto.keyPressChar("up")
                                time.sleep(0.2)
                            if time.time() - stat_time > 10:
                                break
                        # self.operator_module.move_to(240, 225)
                        # time.sleep(0.2)
                        # pyauto.click()
                        # time.sleep(0.2)
                    self.operator_module.open_window("世界地图")
                    self.operator_module.move_to(428, 294)
                    time.sleep(0.2)
                    pyauto.click()
                    time.sleep(5)
                    self.operator_module.move_to(427, 496)
                    time.sleep(0.2)
                    pyauto.click()
                    time.sleep(0.1)
                    pyauto.click()
                    time.sleep(3)
                    pyauto.keyPressChar("n")
                    # ret = self.waiting_for_the_text_to_appear([337, 124, 488, 179], '分解修理机', r'[\u4e00-\u9fa5]+', 20)
                    ret = self.mm.FindPic_sleep(264, 85, 540, 218, "分解修理机.bmp", 0.9, time_s=20, delta_color=([15, 0, 0], [27, 255, 255]))
                    if ret:
                        logger.info(ret)
                        break
                pyauto.keyDownChar("right")
                ret = self.mm.FindPic_sleep(963, 536, 1066, 570, "返回城镇.bmp", 0.9, time_s=20)
                if ret:
                    pyauto.keyUpChar("right")
                    time.sleep(0.1)
                while self.brush_running:
                    time.sleep(0.1)
                    ret = self.mm.FindPic(60, 270, 270, 317, "德洛斯矿山外围.bmp", 0.9)
                    # ret = self.waiting_for_the_text_to_appear([76, 276, 222, 312], '德洛斯矿山外围', r'[\u4e00-\u9fa5]+', 0.3)
                    if ret:
                        time.sleep(0.05)
                        pyauto.keyDownChar("shift")
                        time.sleep(0.05)
                        pyauto.keyDownChar("left")
                        time.sleep(0.05)
                        pyauto.keyUpChar("left")
                        time.sleep(0.05)
                        pyauto.keyUpChar("shift")
                        time.sleep(1)
                        for i in range(1, self.player.map_level, 1):
                            pyauto.keyPressChar("right")
                            time.sleep(0.2)
                        pyauto.keyPressChar("space")
                        time.sleep(0.1)
                        pyauto.keyPressChar("space")
                        time.sleep(0.5)
                        break
                    else:
                        pyauto.keyPressChar("down")
                        time.sleep(0.1)
                        continue

            return 1

    def select_role(self):
        while self.brush_running:
            # 选择角色状态
            select_role_status = self.operator_module.select_role(self.waiting_for_the_text_to_appear, self.current_role_index)
            if select_role_status:
                break

    def receive_ghost_state_message(self, message):
        logger.info("ghost_state_message：" + message)
        if message == "true":
            self.ghost_state = True
        elif message == "false":
            self.ghost_state = False

    def clearingobstacles(self):
        """
        清除障碍
        :return:
        """
        if len(self.box) > 0 and self.player_pos.x is not None:
            for p in self.box:
                logger.info(f"p position x: {p.x}, y: {p.y}")
                logger.info(f"Player position x: {self.player_pos.x}, y: {self.player_pos.y}")
                if abs(p.x - self.player_pos.x) < 120 and abs(p.y - self.player_pos.y) < 30:
                    logger.info("清除障碍", (p.x, p.y))

    def is_valid_map(self):
        """检查玩家是否在有效的地图中，且该地图有对应的房间信息。"""
        # 实现检查逻辑
        # 检查玩家是否在有效的地图中，且该地图有对应的房间信息
        # if len(self.doors) == 0:
        #     logger.info("门的数量为0")
        #     return False
        # 检查玩家所在的地图是否在 a_mapInfo 中
        if not a_mapInfo.get(self.player.map_name):
            logger.info(f"a_mapInfo.get(self.player.map_name):{a_mapInfo.get(self.player.map_name)}")
            logger.info("无效地图")
            return False  # 检查地图是否包含房间信息
        # 如果所有检查都通过，返回 True
        return True

    def find_path_to_boss_room(self):
        """
        使用A*算法查找从玩家当前房间到BOSS房间的路径。
        返回一个方向或者空
        """
        priority_direction = 'right'
        map_direction = None
        if self.player.player_room_id and self.boss_room_id:
            # 实现A*算法查找路径
            # 查找终点房间的路径
            end_direction = a_star(self.room_info_map, self.player.player_room_id, self.boss_room_id, priority_direction)
            if end_direction is not None:
                logger.info(f"终点路径:{end_direction}")
                map_direction = judge_direction(end_direction[0], end_direction[1])
                logger.info(f"终点路径前进方向：{map_direction}")
                self.direction_dic[self.player.player_room_id] = map_direction
        return map_direction

    def find_path_to_query_room(self):
        """查找从玩家当前房间到问号房间的路径。"""
        # 实现查找逻辑
        priority_direction = 'right'
        map_direction = None
        max_iterations = 100  # 最大迭代次数，防止无限循环
        iterations = 0  # 初始化计数器
        st = time.time()  # 记录当前时间作为开始时间
        while self.brush_running and not self.ghost_state and iterations < max_iterations:  # 循环条件：刷子正在运行且非幽灵状态
            self.get_min_map_yolo_res()
            if time.time() - st > 0.2:  # 如果执行时间超过0.5秒
                logger.info("在0.1秒内没有找到问号房间")
                break
            if self.query_room_id:
                break
            iterations += 1  # 增加计数器
        if self.query_room_id:
            x, y = self.query_room_id
            self.room_info_map[x][y] = 0
            logger.info(f"问号房位置:{self.query_room_id}")
        if self.player.player_room_id and self.query_room_id:
            Temporary_direction = a_star(self.room_info_map, self.player.player_room_id, self.query_room_id, priority_direction)
            logger.info(f"临时路径:{Temporary_direction}")
            if Temporary_direction is not None and len(Temporary_direction) >= 2:
                map_direction = judge_direction(Temporary_direction[0], Temporary_direction[1])
                self.direction_dic[self.player.player_room_id] = map_direction
                logger.info(f"临时路径前进方向：{map_direction}")
        return map_direction

    def find_path_to_elite_room(self):
        """查找从玩家当前房间到精英怪房间的路径。"""
        # 实现查找逻辑
        priority_direction = 'right'
        map_direction = None
        if self.player.player_room_id and self.elite_room_id:
            x, y = self.elite_room_id
            self.room_info_map[x][y] = 0
            logger.info(f"精英怪房位置:{self.elite_room_id}")
            # 查找终点房间的路径
            elite_direction = a_star(self.room_info_map, self.player.player_room_id, self.elite_room_id, priority_direction)
            logger.info(f"精英怪路径:{elite_direction}")
            if elite_direction is not None and len(elite_direction) >= 2:
                map_direction = judge_direction(elite_direction[0], elite_direction[1])
                self.direction_dic[self.player.player_room_id] = map_direction
                logger.info(f"精英怪路径前进方向：{map_direction}")
        return map_direction

    def find_path_to_nearest_room_to_boss(self):
        """查找从玩家当前房间到离BOSS房间最近的已探索房间的路径。"""
        # 实现查找逻辑
        priority_direction = 'right'
        map_direction = None
        if self.player.player_room_id and self.boss_room_id:
            # 得到离boss房最近的已探索的房间
            the_room_closest_to_the_boss = self.find_nearest_zero_to_target(self.room_info_map, self.boss_room_id)
            # 查找终点房间的路径
            to_the_boss = a_star(self.room_info_map, self.player.player_room_id, the_room_closest_to_the_boss, priority_direction)
            logger.info(f"to_the_boss路径:{to_the_boss}")
            if to_the_boss is not None and len(to_the_boss) >= 2:
                map_direction = judge_direction(to_the_boss[0], to_the_boss[1])
                self.direction_dic[self.player.player_room_id] = map_direction
                logger.info(f"to_the_boss路径前进方向：{map_direction}")
        return map_direction

    def find_door_direction(self):
        """
        寻找玩家当前房间内的门的方向，优先寻找问号房和精英房，其次寻找Boss房

        Returns:
            str: 门的方向描述
            None: 未找到符合条件的门
        """
        # 1. 检查缓存
        if self.player.player_room_id in self.direction_dic:
            cached_direction = self.direction_dic[self.player.player_room_id]
            self.door_direction = cached_direction
            logger.info(f"从缓存获取门方向: {cached_direction}")
            return cached_direction

        logger.info("开始寻找门方向...")

        # 2. 搜索问号房和精英房
        query_elite_timeout = 0.5  # 搜索问号/精英房的最大时间
        start_time = time.time()

        while (self.brush_running and
               not self.ghost_state and
               time.time() - start_time < query_elite_timeout):

            time.sleep(0.05)  # 减少CPU使用

            try:
                self.get_min_map_yolo_res()
            except Exception as e:
                logger.info(f"更新小地图信息异常: {str(e)}")

            # 优先处理问号房
            if self.query_room_id:
                direction = self.find_path_to_query_room()
                if direction:
                    logger.info(f"找到问号房方向: {direction}")
                    self.door_direction = direction
                    return direction

            # 其次处理精英房
            if self.elite_room_id:
                direction = self.find_path_to_elite_room()
                if direction:
                    logger.info(f"找到精英房方向: {direction}")
                    self.door_direction = direction
                    return direction

        # 3. 搜索Boss房（如果满足条件）

        if not self.query_room_id and not self.elite_room_id:
            min_rooms = MAP_MIN_ROOMS.get(self.player.map_name, 2)
            logger.info(f"最少房间要求为：{min_rooms}")
            if self.boss_room_id and self.player.player_room_id:
                # 初始化最小距离为无穷大，以及最近的坐标
                min_distance = float('inf')
                # 计算当前坐标与target的距离的平方（避免使用sqrt以提高效率）
                distance_squared = (self.boss_room_id[0] - self.player.player_room_id[0]) ** 2 + (self.boss_room_id[1] - self.player.player_room_id[1]) ** 2
                # 如果当前距离的平方小于已知的最小距离的平方，则更新最小距离和最近的坐标
                if distance_squared < min_distance:
                    min_distance = distance_squared
                    if min_distance == 1:
                        logger.info(f"玩家与boss房距离为1")
                if self.getOpenedRoomsCount() >= min_rooms and min_distance == 1:
                    boss_direction = self.find_path_to_boss_room()
                    if boss_direction:
                        logger.info(f"找到{self.player.map_name} Boss方向: {boss_direction}")
                        self.door_direction = boss_direction
                        return boss_direction

        # # 4. 最后尝试找最近房间
        # nearest_direction = self.find_path_to_nearest_room_to_boss()
        # if nearest_direction:
        #     logger.info(f"找到最近房间方向: {nearest_direction}")
        #     return nearest_direction

        logger.info("未找到任何门方向")
        self.door_direction = ''
        return None

    def getOpenedRoomsCount(self):
        count = 0  # 初始化计数器
        for row in self.room_info_map:  # 遍历每个子列表（行）
            for element in row:  # 遍历子列表中的每个元素
                if element == 0:  # 如果元素等于0
                    count += 1  # 计数器加1

        logger.info("0的数量:", count)  # 输出: 0的数量（方法1）: 0
        return count

    def handle_mouse_press(self, x, y):
        if gv.banzhuan == 2:
            # if button == "middle":
            self.mouse_pos = (x, y)
            # self.send_log(f"鼠标事件: 移动 - 位置({x}, {y})")

    def test_move(self):
        if self.player_pos.x > 1067 / 2:
            if abs(self.player_pos.x - 244) < 200:
                move_info = self.compute_move_info_walk(self.player_pos, Point(244, 468), 0, 0)  # 计算到最近货物的移动信息
                logger.info("卡点了，尝试移动：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                self.movement_recorder.left_right_up_down_move_walk_by(move_info, False)  # 根据移动信息移动
            else:
                move_info = self.compute_move_info(self.player_pos, Point(244, 468), 0, 0)  # 计算到最近货物的移动信息
                logger.info("卡点了，尝试跑步：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                self.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动
        else:
            if abs(self.player_pos.x - 244) < 200:
                move_info = self.compute_move_info_walk(self.player_pos, Point(848, 468), 0, 0)  # 计算到最近货物的移动信息
                logger.info("卡点了，尝试移动：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                self.movement_recorder.left_right_up_down_move_walk_by(move_info, False)  # 根据移动信息移动
            else:
                move_info = self.compute_move_info(self.player_pos, Point(848, 468), 0, 0)  # 计算到最近货物的移动信息
                logger.info("卡点了，尝试跑步：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                self.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动

    def wait_until_next_start(self):
        """等待到下一个开始时间（早上六点）"""
        wait_seconds = self.calculate_wait_time()

        # 转换等待时间为小时、分钟、秒，便于阅读
        hours, remainder = divmod(int(wait_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)

        self.send_log(f"本日任务已完成，将在 {hours}小时{minutes}分钟{seconds}秒后（即次日{self.start_hour}点）继续运行")

        # 进入等待状态
        time.sleep(wait_seconds)

        # 等待结束后重置任务状态
        self.today_task_completed = False
        self.send_log("等待结束，准备开始新的任务周期")

    def calculate_wait_time(self):
        """计算距离次日早上六点需要等待的秒数"""
        now = datetime.datetime.now()

        # 计算今天早上六点的时间
        today_6am = now.replace(hour=self.start_hour, minute=0, second=0, microsecond=0)

        # 如果当前时间已经过了今天六点，则目标时间是明天六点
        if now >= today_6am:
            tomorrow_6am = today_6am + datetime.timedelta(days=1)
            wait_seconds = (tomorrow_6am - now).total_seconds()
        else:
            # 如果还没到今天六点，则等待到今天六点
            wait_seconds = (today_6am - now).total_seconds()

        return wait_seconds
