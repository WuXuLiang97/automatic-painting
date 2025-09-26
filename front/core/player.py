# -*- coding: utf-8 -*-
import time
import random
from PyQt5.QtCore import QThread, pyqtSignal
import os

from core.Config import key_config_file
from utils.cross_control import pyauto
from utils.logging_setup import logger
from view.key_config_run import DEFAULT_KEY_CONFIG

# 导入拆分的模块
from .player import PlayerThread as NewPlayerThread
from .player import NavigationHandler, RoomNavigationHandler, CombatHandler, ItemHandler, TaskHandler, MapHandler
from .player import RoleManager
from .player import PlValueHandler
from .role_selection_handler import RoleSelectionHandler
from .map_initialization_handler import MapInitializationHandler
from .game_flow_handler import GameFlowHandler
from .weakness_handler import WeaknessHandler
from .plot_handler import PlotHandler
from .ui_interaction_handler import UIInteractionHandler

# 基础时间单位（秒）
MINUTE = 60
HOUR = 60 * MINUTE

# 键盘配置
try:
    if os.path.exists(key_config_file):
        import json
        with open(key_config_file, 'r', encoding='utf-8') as f:
            key_config = json.load(f)
            logger.info(f"成功加载键盘配置: {key_config_file}")
    else:
        logger.warning(f"键盘配置文件不存在: {key_config_file}，使用默认配置")
        key_config = DEFAULT_KEY_CONFIG
except Exception as e:
    logger.error(f"加载键盘配置失败: {e}，使用默认配置")
    key_config = DEFAULT_KEY_CONFIG

one_key_gather_value = key_config['one_key_gather']['key'].lower()  # 一键聚物
move_character_value = key_config['move_character']['key'].lower()  # 移动角色
back_to_selia_value = key_config['back_to_selia']['key'].lower()  # 回赛利亚房间
challenge_again_value = key_config['challenge_again']['key'].lower()  # 再次挑战


class PlayerThread(QThread):
    """玩家线程，使用拆分后的模块处理游戏逻辑"""
    message = pyqtSignal(str)
    role_table_message = pyqtSignal()
    MAX_PICKUP_TIME = 30  # 最大捡取时长

    def __init__(self, dic=None):
        super().__init__()
        self.dic = dic
        self.mm = None  # 鼠标管理器将在初始化时设置
        self.running = True
        self.brush_running = True
        
        # 初始化处理器
        self.navigation_handler = NavigationHandler()
        self.room_navigation_handler = RoomNavigationHandler()
        self.combat_handler = CombatHandler()
        self.item_handler = ItemHandler()
        self.task_handler = TaskHandler()
        self.map_handler = MapHandler()
        self.role_manager = RoleManager()
        self.pl_value_handler = PlValueHandler()
        self.role_selection_handler = RoleSelectionHandler()
        self.map_initialization_handler = MapInitializationHandler()
        self.game_flow_handler = GameFlowHandler()
        self.weakness_handler = WeaknessHandler()
        self.plot_handler = PlotHandler(self, None, None, self.map_handler)
        self.ui_interaction_handler = UIInteractionHandler(self, None, None)
        
        # 设置处理器之间的引用
        self._setup_module_references()
        
        # 设置随机大休息时间（3-4小时后）
        self.set_big_break_time()
    
    def _setup_module_references(self):
        """设置各模块的引用关系"""
        # 设置处理器之间的相互引用
        self.navigation_handler.player = self
        self.room_navigation_handler.player = self
        self.combat_handler.player = self
        self.item_handler.player = self
        self.task_handler.player = self
        self.map_handler.player = self
        self.role_manager.player = self
        self.pl_value_handler.player = self
        self.pl_value_handler.mm = self.mm
        self.pl_value_handler.operator_module = self.operator_module
        
        # 共享必要的状态
        self.navigation_handler.brush_running = self.brush_running
        self.room_navigation_handler.brush_running = self.brush_running
        self.combat_handler.brush_running = self.brush_running
        self.item_handler.brush_running = self.brush_running
        self.task_handler.brush_running = self.brush_running
        self.pl_value_handler.brush_running = self.brush_running
        
        # 设置新处理器的引用
        self.role_selection_handler.player = self
        self.role_selection_handler.mm = self.mm
        self.role_selection_handler.operator_module = self.operator_module
        self.role_selection_handler.send_log = self.send_log
        self.role_selection_handler.brush_running = self.brush_running
        
        self.map_initialization_handler.player = self
        self.map_initialization_handler.mm = self.mm
        self.map_initialization_handler.operator_module = self.operator_module
        self.map_initialization_handler.send_log = self.send_log
        self.map_initialization_handler.brush_running = self.brush_running
        
        # 设置GameFlowHandler的引用
        self.game_flow_handler.player = self
        self.game_flow_handler.mm = self.mm
        self.game_flow_handler.operator_module = self.operator_module
        self.game_flow_handler.send_log = self.send_log
        self.game_flow_handler.brush_running = self.brush_running
        
        # 设置WeaknessHandler的引用
        self.weakness_handler.player = self
        self.weakness_handler.mm = self.mm
        self.weakness_handler.operator_module = self.operator_module
        self.weakness_handler.send_log = self.send_log
        self.weakness_handler.brush_running = self.brush_running
        
        # 设置PlotHandler的引用
        self.plot_handler.player = self
        self.plot_handler.mm = self.mm
        self.plot_handler.operator_module = self.operator_module
        self.plot_handler.map_handler = self.map_handler
        self.plot_handler.brush_running = self.brush_running
        
        # 设置UIInteractionHandler的引用
        self.ui_interaction_handler.player = self
        self.ui_interaction_handler.mm = self.mm
        self.ui_interaction_handler.operator_module = self.operator_module
        self.ui_interaction_handler.brush_running = self.brush_running

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
        """\调用RoleManager的read_role_config方法"""
        return self.role_manager.read_role_config()

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
                # 使用体力值处理器检测体力
                if self.pl_value_handler.check_pl_value():
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
                # 使用地图初始化处理器初始化地图
                self.room_info_map = self.map_initialization_handler.initialize_map(self.player.map_name)
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
        """剧情模式入口方法，使用PlotHandler处理剧情逻辑"""
        try:
            # 初始化连接
            self.player.pl_value = 0
            self.sock_connect()  # 连接yolo识别服务器
            self.running = True
            
            # 启动倒计时
            for i in range(2, 0, -1):
                self.send_log(f"程序启动倒计时{i}s")
                time.sleep(1)
            self.send_log("程序已启动")
            
            # 激活窗口
            self.operator_module.move_to(640, 40)
            time.sleep(0.1)
            pyauto.click()
            time.sleep(0.1)
            
            # 使用PlotHandler处理剧情逻辑
            while self.running:
                self.brush_running = True
                
                # 初始化剧情设置
                self.plot_handler.initialize_plot()
                
                # 进入剧情地图
                if not self.plot_handler.enter_plot_map():
                    break
                
                # 处理地图逻辑
                if not self.plot_handler.handle_plot_map_logic():
                    break
                
                # 开始剧情刷图
                self.plot_handler.start_plot_brushing(self.brush_map)
                
        except Exception as e:
            logger.exception(f"剧情模式异常:{e}")
            # 打印完整的堆栈跟踪信息
            traceback.print_exc()
        finally:
            # 停止剧情
            self.plot_handler.stop_plot()
            # 关闭连接
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
                # 使用体力值处理器检测体力
                if self.pl_value_handler.check_pl_value(0):
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
        self.Number_of_moves_to_the_next_room.clear()
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
                ###############################虚弱设置
                weak_config = get_gui_config()
                setting = weak_config.get('weak_setting', 'gold')
                self.weakness_handler.handle_weakness(setting)
                ####################################
                time.sleep(2)
                self.select_role()  # 选择角色
                time.sleep(2)
                # 使用体力值处理器检测体力
                if self.pl_value_handler.check_pl_value():
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
        """剧情刷图方法，已迁移到PlotHandler中实现"""
        return self.plot_handler.start_plot_brushing(func)

    def juqing_brush_2(self, func: callable):
        """剧情刷图方法2，已迁移到PlotHandler中实现"""
        return self.plot_handler.start_plot_brushing(func)

    def brush_map(self):
        """调用GameFlowHandler的刷图方法"""
        return self.game_flow_handler.brush_map()

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
        """存金币或取金绿柱石，使用UIInteractionHandler处理账号金库操作"""
        try:
            pyauto.releaseallkey()
            
            # 调用UIInteractionHandler处理账号金库操作
            result = self.ui_interaction_handler.access_account_vault(self.player.map_name)
            
            # 调用物品处理相关逻辑
            if hasattr(self.item_handler, 'access_0'):
                self.item_handler.access_0()
                
            # 打开选择菜单并按下ESC关闭
            self.operator_module.open_window("选择菜单")
            pyauto.keyPressChar("esc")
            time.sleep(0.1)
            
            logger.info(f"账号金库操作完成，结果: {result}")
            return result
        except Exception as e:
            logger.error(f"账号金库操作异常: {str(e)}")
            if hasattr(self, 'send_log'):
                self.send_log(f"账号金库操作异常: {str(e)}")
            return False

    def enter_door(self):
        """
        进入门并尝试移动到门的位置
        委托给navigation_handler处理
        """
        return self.navigation_handler.enter_door()

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
        """ 拾取物品，调用item_handler中的实现 """
        return self.item_handler.pick_up_goods()

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
        """\调用RoleManager的read_current_role_config方法"""
        return self.role_manager.read_current_role_config()

    def process_boss_room(self):
        """
        处理Boss房间的逻辑。

        委托给combat_handler处理Boss房间的相关逻辑。
        """
        # 直接调用combat_handler中的process_boss_room方法
        self.combat_handler.process_boss_room()

    def attach_monster(self):
        """
        攻击怪物的方法
        委托给combat_handler处理
        """
        return self.combat_handler.attack_monster()

    def release_buffer(self):
        """
        释放Buff
        委托给combat_handler处理
        """
        result = self.combat_handler.release_buff()
        self.buffer_is_release = True
        return result

    def find_nearest_zero_to_target(self, room_info_map, target):
        """
        找不到问号房间和精英房间的情况下找到最靠近boss房的房间坐标
        委托给navigation_handler处理
        """
        return self.navigation_handler.find_nearest_zero_to_target(room_info_map, target)

    def find_door_pos(self, down):
        """
        寻找玩家当前房间内的门的位置
        委托给navigation_handler处理
        """
        return self.navigation_handler.find_door_pos(down)

    # def get_next_door_direction(self):
    #     if len(self.doors) <= 0 or self.player.map_name not in mapDictInfo:
    #         return None
    #     room_info_map = mapDictInfo.get(self.player.map_name)
    #     room_info = room_info_map.get(self.player.player_room_id)
    #     return room_info['direction']

    def get_move_speed(self):
        """
        获取移动速度
        委托给navigation_handler处理
        """
        return self.navigation_handler.get_move_speed()

    def compute_move_info(self, player_pos, target_pos, diff_x, diff_y):
        """委托给导航处理器计算移动信息"""
        return self.navigation_handler.compute_move_info(player_pos, target_pos, diff_x, diff_y)
    
    def compute_move_info_walk(self, player_pos, target_pos, diff_x, diff_y):
        """委托给导航处理器计算行走模式下的移动信息"""
        return self.navigation_handler.compute_move_info_walk(player_pos, target_pos, diff_x, diff_y)
    
    def move_to_monster(self):
        """委托给导航处理器执行向怪物移动的操作"""
        return self.navigation_handler.move_to_monster()

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
                            if self.player.map_name == "深渊：终末崇拜者":
                                self.is_boss = True
                            else:
                                ocr_text = self.get_text(int(data[1]), int(data[2]), int(data[3]), int(data[4]), game_image).strip()
                                pattern = r'[\u4e00-\u9fa5]+'
                                # 使用 re.findall() 找出所有匹配的内容
                                matches = re.findall(pattern, ocr_text)
                                t = "".join(matches)
                                logger.info(f"识别领主：{ocr_text}")
                                if "领主" in t:
                                    self.is_boss = True
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

                self.doors.append(Point(x, y))  # 将门添加到列表中
            elif data[0].startswith("forward") and self.player.map_name == "深渊：终末崇拜者":
                self.forward = True
                if data[1] > 1067 / 2:
                    self.doors.append(Point(random.randint(1350, 1467), random.randint(400, 450)))  # 将门添加到列表中
                else:
                    continue

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
                # 使用体力值处理器检测体力
                if self.pl_value_handler.check_pl_value():  # 识别到疲劳且小于预留

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
                    self.Number_of_moves_to_the_next_room.clear()
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
                            self.Number_of_moves_to_the_next_room.clear()
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
                # 使用体力值处理器检测体力
                x1, y1, x2, y2 = (899, 77, 964, 96)
                min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
                ret = self.mm.is_colored(min_img, 30)
                # 如果体力小于预留体力、ret是False代表按f10不能再刷
                if self.pl_value_handler.check_pl_value() or not ret:
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
                    self.Number_of_moves_to_the_next_room.clear()
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
                            self.Number_of_moves_to_the_next_room.clear()
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
                        # 初始化地图
                        self.room_info_map = deepcopy(a_mapInfo.get(self.player.map_name))
                        logger.info('初始化地图')
                        for room_list in self.room_info_map:
                            logger.info(room_list)
                        syst = time.time()
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
                                pyauto.keyPressChar('esc')
                                time.sleep(0.1)
                                return 0
                            game_image = screenshot_util.get_game_screenshot()
                            text = self.get_text(927, 2, 1031, 22, game_image)
                            logger.info(f"识别右上角文字：{text}")
                            cleaned_text = re.sub(r'[^\u4e00-\u9fa5]', '', text)
                            if time.time() - syst > 20:
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
                                pyauto.keyPressChar('esc')
                                time.sleep(0.1)
                                return 0
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
                while self.brush_running:

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









    def find_path_to_boss_room(self):
        return self.navigation_handler.find_path_to_boss_room()
        
    def find_path_to_query_room(self):
        return self.navigation_handler.find_path_to_query_room()
        
    def find_path_to_elite_room(self):
        return self.navigation_handler.find_path_to_elite_room()
        
    def find_path_to_nearest_room_to_boss(self):
        return self.navigation_handler.find_path_to_nearest_room_to_boss()
        
    def find_door_direction(self):
        return self.navigation_handler.find_door_direction()

    def getOpenedRoomsCount(self):
        return self.map_handler.getOpenedRoomsCount()

    def handle_mouse_press(self, x, y):
        if gv.banzhuan == 2:
            self.mouse_pos = (x, y)

    def test_move(self):
        return self.navigation_handler.test_move()

    def wait_until_next_start(self):
        return self.task_handler.wait_until_next_start()
