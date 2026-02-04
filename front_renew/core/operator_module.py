# -*- coding: utf-8 -*-
import re
import time

from core.Config import get_gui_config
from utils.cross_control import pyauto
from root_dir import root_path
from core.common import occupationInfoMap
from utils.cv_recognizer import vnc_mm, my_imread
import random
from core import global_variable as gv
from utils.logging_setup import logger

class OperatorModule:

    def __init__(self, player_instance):
        self.player_instance = player_instance
        self.weakness_template = None  # 弱点模板
        self.back_down_template = None  # 返回城镇模板
        # self.filter = []
        self.mm = vnc_mm

    def initialize(self):
        self.weakness_template = my_imread(root_path + "/res/xuruo.png")
        self.back_down_template = my_imread(
            root_path + "/res/back_down.png")

    def select_role(self, fun, cur_index):
        """
        选择角色
        :param fun:
        :param cur_index:
        :return:
        """
        logger.info(f"当前第{cur_index}个角色")
        # 如果当前对象（self）不是处于开始游戏的界面（即is_start_game_interface()
        # 方法返回False），则执行接下来的代码块
        if not self.is_start_game_interface():
            self.click_menu_item("选择角色")
            time.sleep(0.3)
            if self.is_start_game_interface():
                logger.info("选择角色，已回到开始游戏界面")
                self.move_to(100, 355)
                time.sleep(0.3)
                pyauto.click()
                time.sleep(0.3)
                for i in range(7):
                    pyauto.keyPressChar('up')
                    time.sleep(0.1)
                time.sleep(0.2)
                self.move_to(245, 235)
                time.sleep(0.3)
                pyauto.click()
                time.sleep(2)
            else:
                logger.info("选择角色，没有回到开始游戏界面")
                return False
        cur_index = int(cur_index)
        # 计算行号和列号
        # 行号从1开始，列号也从1开始（但编程时我们通常从0开始计数）
        row = (cur_index - 1) // 7 + 1  # 使用整除来找到行号，并加1以匹配人类的计数方式
        col = (cur_index - 1) % 7  # 使用取余来找到列号

        # 计算需要按下的“下”键次数（注意：从第1行开始不需要按）
        down_count = row - 1

        # 计算需要按下的“右”键次数（从第1列开始不需要按）
        right_count = col
        if cur_index != -1:
            # 模拟按键操作
            for _ in range(down_count):
                pyauto.keyPressChar('down')
                time.sleep(0.1)  # 假设yjs是一个可以模拟按键的库，time用于添加延迟
            for _ in range(right_count):
                pyauto.keyPressChar('right')
                time.sleep(0.1)
        pyauto.keyPressChar('space')
        time.sleep(2)
        for i in range(5):
            if self.is_celia_room(fun):
                return True
            else:
                pyauto.keyPressChar('space')
                time.sleep(2)
        return False

    def is_start_game_interface(self):
        text = self.player_instance.get_text(490, 552, 588, 575)
        chinese_only = re.sub(r'[^一-鿿]', '', text)
        if self.player_instance.yolo_handler.similarity(chinese_only, "游戏开始") >= 0.7:
            return True
        return False

    def is_celia_room(self, fun):
        ret = fun([758, 566, 815, 588], '商城', r'[\u4e00-\u9fa5]+', 2)
        if ret:
            return True
        else:
            return False

    def remove_weakness(self):
        """
        消除弱点
        :return:
        """
        for i in range(5):
            ret = self.mm.FindPic(725, 462, 972, 558, "虚弱.bmp", 0.9)
            if ret:
                x, y = ret[0][1], ret[0][2]
                self.move_to(x, y)
                pyauto.click()

                time.sleep(0.5)

                weak_config = get_gui_config()  #
                setting = weak_config.get('weak_setting', 'gold')  #
                print('虚弱666',setting)
                if setting == 'gold':
                    ret = self.mm.FindPic(398, 154, 670, 435, "金币恢复.bmp", 0.9)
                elif setting == 'contract':
                    ret = self.mm.FindPic(398, 154, 670, 435, "契约恢复.bmp", 0.9)

                if ret:
                    x, y = ret[0][1], ret[0][2]
                    self.move_to(x, y)
                    pyauto.click()

                    time.sleep(0.1)
                else:
                    continue
                ret = self.mm.FindPic(406, 150, 651, 424, "是.bmp", 0.9)
                if ret:
                    pyauto.keyPressChar('esc')

                    time.sleep(0.1)
                    return True
        return False


    def open_window(self, window_name):
        """
        打开个人信息、菜单
        :param window_name:
        :return:
        """
        try:
            for _ in range(5):
                if window_name == "个人信息":
                    pyauto.keyPressChar('m')
                    time.sleep(0.1)
                    ret = self.mm.FindPic_sleep(239, 39, 548, 135, "个人信息.bmp", 0.9, delta_color=([0, 0, 0], [179, 255, 255]), time_s=0.5, my_sleep=0.1)
                    if ret:
                        logger.info("已打开个人信息")
                        return True
                if window_name == "选择菜单":

                    pyauto.keyPressChar('esc')
                    time.sleep(0.2)
                    if self.is_esc_menu_open():
                        return True
                if window_name == "世界地图":
                    ret = self.mm.FindPic_sleep(463, 0, 607, 43, "世界地图.bmp", 0.9, time_s=0.5, my_sleep=0.1)
                    if ret:
                        logger.info("已打开世界地图")
                        return True
                    else:
                        pyauto.keyPressChar('n')
                        time.sleep(0.1)

            return False
        except Exception as e:
            logger.info(f'open_window方法报错：{e}')

    def close_all_window(self):
        """
        关闭所有窗口
        :return:
        """
        pyauto.keyPressChar('esc')

        for i in range(5):
            if self.is_esc_menu_open():
                pyauto.keyPressChar('esc')
            else:
                break

    def is_esc_menu_open(self):
        """
        检查是否打开了选择菜单
        :return: bool
        """
        ret = self.mm.FindPic(0, 0, 1067, 600, "关闭.bmp", 0.9)
        if ret:
            x, y = ret[0][1], ret[0][2]
            self.move_to(x, y)
            time.sleep(0.05)
            pyauto.click()
            time.sleep(0.5)
        text = self.player_instance.get_text(484, 45, 584, 75)
        chinese_only = re.sub(r'[^一-鿿]', '', text)
        if self.player_instance.yolo_handler.similarity(chinese_only, "选择菜单") >= 0.7:
            logger.info("选择菜单已打开")
            return True
        else:
            logger.info("选择菜单未打开")
        return False


    def has_two_common_chars(self, input_str, target_set):

        input_set = set(input_str)
        for target_str in target_set:
            # 计算当前目标字符串与输入字符串的交集
            common_chars = input_set & set(target_str)
            if len(common_chars) >= 2:
                return True
        return False

    def get_randint_xy(self, x1, y1, x2, y2):
        """
        生成一个在指定范围内的随机坐标点。

        参数:
        - x1: x坐标的最小值（包含）
        - y1: y坐标的最小值（包含）
        - x2: x坐标的最大值（包含）
        - y2: y坐标的最大值（包含）

        返回值:
        - 一个元组，包含随机生成的x坐标和y坐标。
        """
        return random.randint(x1, x2), random.randint(y1, y2)

    def sale_goods(self, sell):
        """
        销售货物
        :return:
        """
        pyauto.keyPressChar('a')

        time.sleep(0.5)
        # 识别并操作出售装备
        sell()
        time.sleep(0.2)

        # 点击材料
        ret = self.mm.FindPic(595, 278, 875, 317, "材料.bmp", 0.85)
        if ret:
            x, y = ret[0][1], ret[0][2]
            self.move_to(x, y)
            time.sleep(0.2)
            pyauto.click()

            time.sleep(0.2)
        else:
            logger.info("出售物品时没有找到材料栏")
            return
        # 点击出售
        self.move_to(264, 528)
        time.sleep(0.2)
        pyauto.click()

        time.sleep(0.2)
        xy = []
        ret = self.mm.FindPic(606, 302, 864, 566, "风化的碎骨.bmp|生锈的铁片.bmp|最下级砥石.bmp|破旧的皮革.bmp|生锈的铁片.bmp|碎布片.bmp|最下级硬化剂.bmp", 0.85, 1)
        if ret:
            logger.info(ret)
            for det in ret:
                xy.append((det[1], det[2]))
        for xy1 in xy:
            x, y = xy1[0], xy1[1]
            self.move_to(x, y)
            time.sleep(0.2)
            pyauto.click()

            time.sleep(0.2)
            pyauto.click()

            time.sleep(0.2)
            pyauto.click()

            time.sleep(0.2)

    def find_pic_sleep(self, pic_name, x1, y1, x2, y2):
        return self.mm.FindPic_sleep(x1, y1, x2, y2, pic_name, 0.9, drag=None, delta_color=([20, 0, 0], [23, 255, 255]), time_s=2)

    def get_menu_item_coordinates(self, item_name):
        x, y = 640, 40
        if item_name == "选择角色":
            x, y = 502, 504
        elif item_name == "返回城镇":
            x, y = 621, 502
        return x, y

    def click_menu_item(self, item_name):
        """
        单击选择菜单
        :param item_name:
        :return:
        """
        logger.info(item_name)
        x, y = self.get_menu_item_coordinates(item_name)
        if x == 0 and y == 0:
            return
        if item_name == "传送阵":
            return self.handle_transfer_matrix()
        st = time.time()
        while True:
            # 开始游戏页面
            if self.is_start_game_interface():
                return False
            if time.time() - st >= 10:
                logger.info(f"click_menu_item执行超时：{item_name}")
                return False
            if item_name == "选择角色":
                esc_status = self.is_esc_menu_open()
                if not esc_status:  # 如果没打开
                    self.move_to(640, 40)
                    time.sleep(0.2)
                    pyauto.click()
                    time.sleep(0.2)
                    open_status = self.open_window("选择菜单")
                    if not open_status:  # 如果没打开
                        continue
                    pyauto.keyPressChar("esc")
                    time.sleep(0.2)
                    pyauto.keyPressChar("esc")
                    time.sleep(0.2)
                self.move_to(x, y)
                time.sleep(0.5)
                pyauto.click()
                time.sleep(0.2)
                self.move_to(x + 100, y + 50)
                time.sleep(0.1)
                if not self.find_pic_sleep("选择角色.bmp", 344, 468, 733, 549):
                    pyauto.keyPressChar("esc")
                    time.sleep(0.2)
                    continue
            if item_name == "返回城镇":
                if self.handle_return_to_town():
                    return True
            time.sleep(1)
            esc_status = self.is_esc_menu_open()
            if not esc_status:  # 如果没打开，操作成功esc是关闭状态的
                return True
        return False

    def handle_return_to_town(self):
        logger.info("进入返回城镇(handle_return_to_town)")
        while True:
            open_status = self.open_window("选择菜单")
            if not open_status:  # 如果没打开
                continue
            """下面这两个退出是为了更新界面"""
            pyauto.keyPressChar("esc")
            time.sleep(0.2)
            pyauto.keyPressChar("esc")
            time.sleep(0.2)
            ret = self.mm.FindPic(0, 0, 1067, 600, "金币寄售.bmp", 0.9, drag=None, delta_color=([20, 0, 0], [23, 255, 255]))
            if ret:
                pyauto.keyPressChar("esc")
                time.sleep(0.2)
                logger.info("退出返回城镇(handle_return_to_town)")
                return True
            else:
                x, y = self.get_menu_item_coordinates("返回城镇")
                self.move_to(x, y)
                time.sleep(0.5)
                pyauto.click()
                time.sleep(0.2)
                pyauto.keyPressChar("f12")
                time.sleep(0.2)
                self.move_to(x + 100, y + 50)
                time.sleep(0.1)
                ret = self.mm.FindPic(408, 205, 670, 405, "确认.bmp", 0.9, drag=None)
                if ret:
                    pyauto.keyPressChar("space")
                    time.sleep(0.2)

    def handle_transfer_matrix(self):
        if self.is_esc_menu_open():
            pyauto.keyPressChar("esc")
            time.sleep(0.5)
        st = time.time()
        while True:
            ret = self.mm.FindPic(463, 0, 607, 43, "世界地图.bmp", 0.9, drag=None)
            if ret:
                pyauto.keyPressChar("f2")
                time.sleep(0.1)
                pyauto.keyPressChar("f2")
                time.sleep(0.5)
                # 不关这个会卡图
                # ret = self.mm.FindPic(55, 57, 210, 113, "进行栏位操作.bmp", 0.9, drag=None)
                return True
            else:
                pyauto.keyPressChar("n")
                time.sleep(0.5)

            if time.time() - st >= 10:
                logger.info(f"click_menu_item打开地图执行超时：选择传送阵")
                return False

    def ocr_pl(self, func: callable, func1: callable):
        """
        识别疲劳
        :return: int
        """

        def contains_digit(s):
            pattern = r'\d'
            return bool(re.search(pattern, s))

        ret = self.mm.FindPic(718, 30, 897, 107, "叉.bmp", 0.9)
        if ret:
            x, y = ret[0][1], ret[0][2]
            self.move_to(x, y)
            time.sleep(0.1)
            pyauto.click()
            time.sleep(0.2)
        for i in range(5):
            try:
                self.move_to(870, 593)
                time.sleep(0.1)
                # 用传进来的方法识别
                results = func(824, 570, 930, 589, amplify=True)
                if contains_digit(results):
                    match = re.search(r'(\d+)/', results)
                    if match:
                        pl_int = match.group(1)
                        if pl_int:
                            pl_int = int(pl_int)
                            logger.info(f"当前疲劳值：{pl_int}")
                            func1(f"当前疲劳值：{pl_int}")
                        else:
                            logger.info("满级角色ocr疲劳没有找到匹配项")
                            func1("满级角色ocr疲劳没有找到匹配项")
                            continue
                    else:
                        logger.info("满级角色ocr疲劳正则匹配失败")
                        func1("满级角色ocr疲劳正则匹配失败")
                        continue
                else:
                    # 用传进来的方法识别
                    results = func(641, 518, 762, 533, amplify=True)
                    logger.debug(f"未满级角色疲劳值识别原始结果: {results}")
                    
                    # 尝试多种可能的正则表达式匹配格式
                    match = None
                    patterns = [
                        r'(\d+)/',       # 标准格式 如: 156/
                        r'(\d+)\\s*点?',  # 带或不带"点"字 如: 156点或156
                        r'(\d+)\\s*疲劳', # 带"疲劳"字样 如: 156疲劳
                        r'疲劳值\\s*[:：]?\s*(\d+)', # 疲劳值: 156
                        r'^(\d+)$'       # 只有数字
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, results)
                        if match:
                            break
                    
                    if match:
                        pl_int = match.group(1)
                        if pl_int:
                            pl_int = int(pl_int)
                            logger.info(f"当前疲劳值：{pl_int}")
                            func1(f"当前疲劳值：{pl_int}")
                        else:
                            logger.info("未满级角色ocr疲劳没有找到匹配项")
                            func1("未满级角色ocr疲劳没有找到匹配项")
                            continue
                    else:
                        logger.info(f"未满级角色ocr疲劳正则匹配失败，尝试了多种格式")
                        func1("未满级角色ocr疲劳正则匹配失败")
                        continue
                self.move_to(random.randint(500, 560), 30)
                time.sleep(0.1)
                return pl_int
            except Exception as e:
                logger.info(e)
                continue
        self.move_to(random.randint(500, 560), 30)
        time.sleep(0.1)
        # 所有尝试都失败后，默认返回0表示疲劳为空
        logger.info("多次尝试识别疲劳值失败，默认返回0")
        return 0


    def get_base_speed(self, player_occupation, plain_speed):
        """
        获得基本速度
        :param player_occupation:玩家职业
        :param plain_speed:普通速度
        :return:
        """
        if plain_speed:
            base_x = occupationInfoMap[player_occupation].get("x_speed").get("30")
            base_y = occupationInfoMap[player_occupation].get("y_speed").get("30")
            return base_x, base_y
        return None, None

    def move_to(self, x, y):
        """
        移动鼠标
        :param x:
        :param y:
        :return:
        """
        x = gv.last_position[0] + x
        y = gv.last_position[1] + y
        logger.info("move_to:窗口左上角x = {}\t窗口左上角y = {}\tx={}\ty={}".format(gv.last_position[0], gv.last_position[1], x, y))
        pyauto.moveTo(x, y)
        time.sleep(0.2)
