import time
import random
import threading
import pyautogui as pyauto
from core import global_variable as gv
from utils import screenshot_util
from utils.logging_setup import logger
from core.utils.socket_client import SocketClient
from core.utils.image_detection import get_similarity
from core.utils.ocr_module import OCRModule
from core.utils.movement_recorder import MovementRecorder
from core.operator_module import OperatorModule
from .map_handler import MapHandler
from .navigation import NavigationHandler
from .navigation_handler import RoomNavigationHandler
from .combat_handler import CombatHandler
from .item_handler import ItemHandler
from .task_handler import TaskHandler
from .role_manager import RoleManager
from .game_flow_handler import GameFlowHandler

class PlayerThread(threading.Thread):
    def __init__(self, mm, send_log, config_data):
        threading.Thread.__init__(self)
        self.mm = mm
        self.send_log = send_log
        self.brush_running = True
        self.ghost_state = False
        self.map_name = ""
        self.player_room_id = None
        self.player_pos = None
        
        # 初始化各模块
        self.map_handler = MapHandler()
        self.navigation_handler = NavigationHandler()
        self.room_navigation_handler = RoomNavigationHandler()
        self.combat_handler = CombatHandler()
        self.item_handler = ItemHandler()
        self.task_handler = TaskHandler()
        self.role_manager = RoleManager()
        self.game_flow_handler = GameFlowHandler()
        
        # 初始化工具模块
        self.operator_module = OperatorModule()
        self.ocr_module = OCRModule()
        self.movement_recorder = MovementRecorder()
        
        # 配置数据
        self.config_data = config_data
        
        # 设置各模块的引用
        self._setup_module_references()
        
        # 设置配置
        self._apply_config()
        
        # 房间信息
        self.room_info_map = None
        self.boss_room_id = None
        self.query_room_id = None
        self.elite_room_id = None
        
        # 检测信息
        self.monsters = []
        self.goods = []
        self.doors = []
        self.box = []
        self.boss = None
        self.query = None
        self.elite = None
        
        # 房间物品拾取计数
        self.room_item_pickup_counts = {}
        
        # 房间属性
        self.is_boss = False
        self.has_continue = False
        
        # socket通信
        self.socket_client = None
        
        # 地图最小房间要求配置
        self.map_min_rooms = {
            "风暴逆鳞普通": 2,
            "德洛斯矿山外围": 2,
            "风暴幽城": 2,
            "深渊：终末崇拜者": 3,
            "流雨瀑布": 2,
            "海伯伦的预言所": 2,
            "红矿村": 2,
            "跌宕群岛": 2
        }
    
    def _setup_module_references(self):
        """设置各模块的引用关系"""
        # 设置各模块对PlayerThread的引用
        self.map_handler.player = self
        self.navigation_handler.player = self
        self.room_navigation_handler.player = self
        self.combat_handler.player = self
        self.item_handler.player = self
        self.task_handler.player = self
        self.role_manager.player = self
        self.game_flow_handler.player = self
        
        # 设置工具模块引用
        self.navigation_handler.mm = self.mm
        self.room_navigation_handler.mm = self.mm
        self.combat_handler.mm = self.mm
        self.item_handler.mm = self.mm
        self.task_handler.mm = self.mm
        self.game_flow_handler.mm = self.mm
        
        self.navigation_handler.send_log = self.send_log
        self.room_navigation_handler.send_log = self.send_log
        self.combat_handler.send_log = self.send_log
        self.item_handler.send_log = self.send_log
        self.task_handler.send_log = self.send_log
        self.role_manager.send_log = self.send_log
        self.game_flow_handler.send_log = self.send_log
        
        self.navigation_handler.movement_recorder = self.movement_recorder
        self.room_navigation_handler.movement_recorder = self.movement_recorder
        self.combat_handler.movement_recorder = self.movement_recorder
        self.item_handler.movement_recorder = self.movement_recorder
        
        self.navigation_handler.operator_module = self.operator_module
        self.room_navigation_handler.operator_module = self.operator_module
        self.combat_handler.operator_module = self.operator_module
        self.item_handler.operator_module = self.operator_module
        self.task_handler.operator_module = self.operator_module
        self.role_manager.operator_module = self.operator_module
        self.game_flow_handler.operator_module = self.operator_module
        
        self.navigation_handler.ocr_module = self.ocr_module
        self.combat_handler.ocr_module = self.ocr_module
        self.item_handler.ocr_module = self.ocr_module
        self.task_handler.ocr_module = self.ocr_module
        
        # 设置导航模块的特殊引用
        self.navigation_handler.get_min_map_yolo_res = self.get_min_map_yolo_res
    
    def _apply_config(self):
        """应用配置数据"""
        if not self.config_data:
            return
        
        # 应用各模块的配置
        self.map_handler.apply_config(self.config_data)
        self.combat_handler.apply_config(self.config_data)
        self.item_handler.apply_config(self.config_data)
        self.task_handler.apply_config(self.config_data)
    
    def run(self):
        """线程主函数"""
        try:
            logger.info("开始运行玩家线程")
            
            # 初始化Socket连接
            self._init_socket()
            
            # 主循环
            while self.brush_running:
                try:
                    # 处理游戏逻辑
                    self._process_game_logic()
                    
                    # 小暂停
                    time.sleep(0.1)
                except Exception as e:
                    logger.info(f"主循环异常: {str(e)}")
                    time.sleep(0.5)
        except Exception as e:
            logger.info(f"玩家线程异常: {str(e)}")
        finally:
            logger.info("玩家线程结束")
            self._cleanup()
    
    def _init_socket(self):
        """初始化Socket连接"""
        try:
            # 这里应该初始化Socket连接
            # self.socket_client = SocketClient(...)
            pass
        except Exception as e:
            logger.info(f"Socket初始化异常: {str(e)}")
    
    def _process_game_logic(self):
        """处理游戏逻辑"""
        # 检查幽灵状态
        if self.ghost_state:
            logger.info("角色处于幽灵状态，等待恢复")
            time.sleep(1.0)
            return
        
        # 获取小地图识别结果
        self.get_min_map_yolo_res()
        
        # 检测游戏元素
        self._detect_game_elements()
        
        # 使用GameFlowHandler处理核心游戏流程
        # 处理战斗
        if self.combat_handler.is_in_combat():
            self.combat_handler.attack_monster()
        
        # 处理移动
        self._process_movement()
        
        # 处理物品拾取
        self.item_handler.pick_up_goods()
        
        # 处理任务
        if not self.task_handler.daily_tasks_completed:
            self.task_handler.daily_tasks()
        
        # 刷图逻辑由GameFlowHandler独立处理，不在此循环中调用
    
    def _detect_game_elements(self):
        """检测游戏元素"""
        try:
            # 这里应该获取检测结果
            # detect_result = self.socket_client.send_and_receive("detect")
            # self.navigation_handler.process_detect_message(detect_result)
            
            # 更新PlayerThread的检测信息
            # self.monsters = self.navigation_handler.monsters
            # self.goods = self.navigation_handler.goods
            # ... 其他检测信息
            pass
        except Exception as e:
            logger.info(f"检测游戏元素异常: {str(e)}")
    
    def _process_movement(self):
        """处理移动"""
        try:
            # 寻找门方向
            door_direction = self.navigation_handler.find_door_direction()
            
            # 如果找到门方向，尝试进入门
            if door_direction and self.doors:
                self.navigation_handler.enter_door()
        except Exception as e:
            logger.info(f"处理移动异常: {str(e)}")
    
    def _cleanup(self):
        """清理资源"""
        try:
            # 释放所有按键
            pyauto.releaseallkey()
            
            # 关闭Socket连接
            if self.socket_client:
                # self.socket_client.close()
                pass
        except Exception as e:
            logger.info(f"清理资源异常: {str(e)}")
    
    def stop(self):
        """停止线程"""
        logger.info("停止玩家线程")
        self.brush_running = False
        
        # 通知各模块停止
        self.combat_handler.brush_running = False
        self.navigation_handler.brush_running = False
        self.item_handler.brush_running = False
        self.task_handler.brush_running = False
        self.game_flow_handler.brush_running = False
        
        # 等待线程结束
        if self.is_alive():
            self.join(timeout=5.0)
    
    def start_brushing(self):
        """开始刷图"""
        logger.info("开始启动刷图流程")
        try:
            # 确保地图已设置
            if not hasattr(self.player, 'map_name') or not self.player.map_name:
                logger.error("未设置地图名称，无法启动刷图")
                return False
                
            # 进入地图
            result = self.enter_map()
            if result != 0:
                logger.error(f"进入地图失败，返回值: {result}")
                return False
                
            # 启动刷图逻辑
            logger.info(f"开始在地图 {self.player.map_name} 中刷图")
            self.game_flow_handler.brush_map()
            return True
        except Exception as e:
            logger.error(f"启动刷图流程时发生异常: {str(e)}")
            return False
    
    def handle_mouse_press(self, x, y):
        """鼠标事件处理"""
        logger.info(f"鼠标按下事件: ({x}, {y})")
        # 记录鼠标位置
        self.last_mouse_pos = (x, y)
    
    def get_move_speed(self):
        """获取移动速度"""
        return self.navigation_handler.get_move_speed()
    
    def enter_map(self, map_name=None):
        """
        进入地图，通过GameFlowHandler处理
        如果不指定map_name，则使用player对象中存储的地图名称
        """
        if map_name:
            self.player.map_name = map_name
        return self.game_flow_handler.enter_map()
    
    def is_valid_map(self):
        """检查地图有效性"""
        return self.map_handler.is_valid_map()
    
    def getOpenedRoomsCount(self):
        """获取已打开的房间数量"""
        return self.map_handler.getOpenedRoomsCount()
    
    def get_min_map_yolo_res(self):
        """获取小地图YOLO识别结果"""
        try:
            # 这里应该从Socket获取小地图识别结果
            # result = self.socket_client.send_and_receive("min_map_yolo")
            
            # 解析结果并更新房间信息
            # self._update_room_info(result)
            pass
        except Exception as e:
            logger.info(f"获取小地图识别结果异常: {str(e)}")
    
    def _update_room_info(self, result):
        """更新房间信息"""
        # 解析房间信息并更新相关属性
        pass
    
    def sell_items(self):
        """出售物品"""
        return self.item_handler.sell()
    
    def agg_pick_up_goods(self):
        """BOSS房聚物拾取"""
        return self.item_handler.agg_pick_up_goods()
        
    def pickup_goods(self):
        """拾取物品，由game_flow_handler调用"""
        return self.item_handler.pick_up_goods()
    
    def release_buffer(self):
        """释放Buff"""
        return self.combat_handler.release_buffer()
    
    def select_role(self):
        """
        选择角色，通过RoleManager处理
        :return:
        """
        self.role_manager.select_role()
    
    def receive_ghost_state_message(self, message):
        """接收幽灵状态消息"""
        self.combat_handler.receive_ghost_state_message(message)
        self.ghost_state = self.combat_handler.ghost_state
    
    def clearingobstacles(self):
        """清除障碍物"""
        return self.combat_handler.clearingobstacles()
    
    def wait_until_next_start(self):
        """等待直到下次开始"""
        return self.task_handler.wait_until_next_start()
    
    def compute_move_info(self, player_pos, target_pos, offset_x, offset_y):
        """计算移动信息"""
        return self.navigation_handler.compute_move_info(player_pos, target_pos, offset_x, offset_y)
    
    def compute_move_info_walk(self, player_pos, target_pos, offset_x, offset_y):
        """计算步行移动信息"""
        return self.navigation_handler.compute_move_info_walk(player_pos, target_pos, offset_x, offset_y)
    
    def move_to_monster(self):
        """向怪物移动"""
        return self.navigation_handler.move_to_monster()
    
    def process_detect_message(self, message):
        """处理检测消息"""
        self.navigation_handler.process_detect_message(message)
        
        # 更新PlayerThread的检测信息
        self.player_pos = self.navigation_handler.player_pos
        self.monsters = self.navigation_handler.monsters
        self.goods = self.navigation_handler.goods
        self.doors = self.navigation_handler.doors
        self.box = self.navigation_handler.box
        self.boss = self.navigation_handler.boss
        self.query = self.navigation_handler.query
        self.elite = self.navigation_handler.elite
    
    def find_nearest_zero_to_target(self, matrix, target):
        """找到离目标最近的0值"""
        return self.navigation_handler.find_nearest_zero_to_target(matrix, target)
    
    def find_door_pos(self):
        """找到门的位置"""
        return self.navigation_handler.find_door_pos()
    
    def test_move(self):
        """测试移动"""
        return self.navigation_handler.test_move()
    
    def player_left_right_move(self):
        """玩家左右移动"""
        return self.navigation_handler.player_left_right_move()
    
    def access_0(self):
        """访问消耗品与金绿柱石"""
        return self.item_handler.access_0()
    
    def auto_pick(self):
        """自动拾取"""
        return self.item_handler.auto_pick()
    
    def waiting_for_the_text_to_appear(self, text_pattern, timeout=10):
        """等待文本出现"""
        return self.task_handler.waiting_for_the_text_to_appear(text_pattern, timeout)
    
    def find_path_to_boss_room(self):
        """寻找BOSS房间路径"""
        return self.navigation_handler.find_path_to_boss_room()
    
    def find_path_to_query_room(self):
        """寻找问号房间路径"""
        return self.navigation_handler.find_path_to_query_room()
    
    def find_path_to_elite_room(self):
        """寻找精英房间路径"""
        return self.navigation_handler.find_path_to_elite_room()
    
    def find_path_to_nearest_room_to_boss(self):
        """寻找离BOSS房间最近的房间路径"""
        return self.navigation_handler.find_path_to_nearest_room_to_boss()
    
    def find_door_direction(self):
        """寻找门方向"""
        return self.navigation_handler.find_door_direction()
    
    def reset_all_states(self):
        """重置所有状态"""
        # 重置各模块状态
        self.combat_handler.reset_combat_state()
        self.item_handler.reset_pickup_state()
        self.task_handler.reset_task_state()
        
        # 重置PlayerThread状态
        self.player_room_id = None
        self.player_pos = None
        self.monsters = []
        self.goods = []
        self.doors = []
        self.box = []
        self.boss = None
        self.query = None
        self.elite = None
        
        logger.info("所有状态已重置")