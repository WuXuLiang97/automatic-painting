import time
import random
from utils.logging_setup import logger
from core import global_variable as gv
from core.utils.image_detection import ImageDetection
from core.utils.socket_client import SocketClient

class MapHandler:
    def __init__(self):
        """初始化地图处理器"""
        self.player = None  # 玩家引用，在PlayerThread中设置
        self.mm = None  # 鼠标管理器引用，在PlayerThread中设置
        self.send_log = None  # 日志发送函数，在PlayerThread中设置
        
        # 地图相关配置
        self.map_config = {
            "min_rooms": {
                "风暴逆鳞普通": 2,
                "德洛斯矿山外围": 2,
                "风暴幽城": 2,
                "深渊：终末崇拜者": 3,
                "流雨瀑布": 2,
                "海伯伦的预言所": 2,
                "红矿村": 2,
                "跌宕群岛": 2
            }
        }
        
        # 房间信息
        self.room_info_map = None
        self.boss_room_id = None
        self.query_room_id = None
        self.elite_room_id = None
        
        # 地图检测相关
        self.image_detection = ImageDetection()
        self.socket_client = SocketClient()
    
    def apply_config(self, config_data):
        """应用配置数据"""
        if not config_data:
            return
        
        # 更新地图配置
        if "map_config" in config_data:
            self.map_config.update(config_data["map_config"])
        
        # 更新最小房间配置
        if "min_rooms" in config_data:
            self.map_config["min_rooms"].update(config_data["min_rooms"])
    
    def initialize_map(self, map_name):
        """初始化地图信息"""
        try:
            logger.info(f"初始化地图: {map_name}")
            
            # 这里应该从配置或数据库获取地图信息
            # self.room_info_map = self._get_map_info(map_name)
            
            # 记录地图名称
            if self.player:
                self.player.map_name = map_name
            
            # 查找特殊房间
            self._find_special_rooms()
            
            return True
        except Exception as e:
            logger.error(f"初始化地图失败: {str(e)}")
            return False
    
    def _get_map_info(self, map_name):
        """获取地图信息"""
        # 这里应该从配置或数据库获取地图信息
        # 暂时返回空字典
        return {}
    
    def _find_special_rooms(self):
        """查找特殊房间（BOSS房、问号房、精英房）"""
        try:
            # 这里应该根据地图信息查找特殊房间
            # 暂时返回默认值
            self.boss_room_id = 5
            self.query_room_id = 3
            self.elite_room_id = 2
        except Exception as e:
            logger.error(f"查找特殊房间失败: {str(e)}")
    
    def enter_map(self, map_name):
        """进入地图"""
        try:
            logger.info(f"尝试进入地图: {map_name}")
            
            # 调用初始化地图
            if not self.initialize_map(map_name):
                logger.error(f"初始化地图失败，无法进入地图: {map_name}")
                return 0
            
            # 这里应该有进入地图的具体逻辑
            # 例如点击NPC、选择地图难度等
            
            # 等待进入地图
            time.sleep(2)
            
            # 检查是否成功进入地图
            if not self.is_in_map():
                logger.error(f"进入地图失败: {map_name}")
                return 0
            
            logger.info(f"成功进入地图: {map_name}")
            return 1
        except Exception as e:
            logger.error(f"进入地图异常: {str(e)}")
            return 0
    
    def is_in_map(self):
        """检查是否在地图中"""
        try:
            # 这里应该有检查是否在地图中的逻辑
            # 例如检测地图界面元素
            return True
        except Exception as e:
            logger.error(f"检查是否在地图中异常: {str(e)}")
            return False
    
    def is_valid_map(self):
        """检查地图是否有效"""
        try:
            if not self.player or not self.player.map_name:
                return False
            
            # 检查地图是否在支持列表中
            if self.player.map_name not in self.map_config["min_rooms"]:
                return False
            
            # 检查已打开的房间数量是否满足最小要求
            if self.getOpenedRoomsCount() < self.map_config["min_rooms"][self.player.map_name]:
                return False
            
            return True
        except Exception as e:
            logger.error(f"检查地图有效性异常: {str(e)}")
            return False
    
    def getOpenedRoomsCount(self):
        """获取已打开的房间数量"""
        try:
            # 这里应该有获取已打开房间数量的逻辑
            # 暂时返回随机值
            return random.randint(1, 5)
        except Exception as e:
            logger.error(f"获取已打开房间数量异常: {str(e)}")
            return 0
    
    def find_player_room(self):
        """查找玩家所在房间"""
        try:
            # 这里应该有查找玩家所在房间的逻辑
            # 例如通过小地图识别
            if self.player:
                # 暂时返回随机房间ID
                self.player.player_room_id = random.randint(1, 5)
                return self.player.player_room_id
            return None
        except Exception as e:
            logger.error(f"查找玩家所在房间异常: {str(e)}")
            return None
    
    def get_room_info(self, room_id):
        """获取房间信息"""
        try:
            if not self.room_info_map or room_id not in self.room_info_map:
                return None
            return self.room_info_map[room_id]
        except Exception as e:
            logger.error(f"获取房间信息异常: {str(e)}")
            return None
    
    def is_boss_room(self, room_id):
        """检查是否为BOSS房间"""
        try:
            return room_id == self.boss_room_id
        except Exception as e:
            logger.error(f"检查是否为BOSS房间异常: {str(e)}")
            return False
    
    def is_query_room(self, room_id):
        """检查是否为问号房间"""
        try:
            return room_id == self.query_room_id
        except Exception as e:
            logger.error(f"检查是否为问号房间异常: {str(e)}")
            return False
    
    def is_elite_room(self, room_id):
        """检查是否为精英房间"""
        try:
            return room_id == self.elite_room_id
        except Exception as e:
            logger.error(f"检查是否为精英房间异常: {str(e)}")
            return False
    
    def update_room_status(self, room_id, status):
        """更新房间状态"""
        try:
            if not self.room_info_map:
                return False
            
            if room_id not in self.room_info_map:
                self.room_info_map[room_id] = {}
            
            self.room_info_map[room_id]["status"] = status
            return True
        except Exception as e:
            logger.error(f"更新房间状态异常: {str(e)}")
            return False
    
    def reset_map(self):
        """重置地图信息"""
        try:
            self.room_info_map = None
            self.boss_room_id = None
            self.query_room_id = None
            self.elite_room_id = None
            
            if self.player:
                self.player.player_room_id = None
                self.player.is_boss = False
        except Exception as e:
            logger.error(f"重置地图信息异常: {str(e)}")
    
    def handle_map_exit(self):
        """处理地图退出"""
        try:
            logger.info("退出地图")
            
            # 重置地图信息
            self.reset_map()
            
            # 这里应该有退出地图后的处理逻辑
            # 例如返回城镇、清理状态等
            
            return True
        except Exception as e:
            logger.error(f"处理地图退出异常: {str(e)}")
            return False
    
    def get_map_min_rooms(self, map_name):
        """获取地图最小房间要求"""
        try:
            if map_name in self.map_config["min_rooms"]:
                return self.map_config["min_rooms"][map_name]
            return 2  # 默认最小房间数
        except Exception as e:
            logger.error(f"获取地图最小房间要求异常: {str(e)}")
            return 2
    
    def check_map_conditions(self):
        """检查地图条件"""
        try:
            if not self.player or not self.player.map_name:
                return False
            
            # 检查已打开的房间数量是否满足最小要求
            min_rooms = self.get_map_min_rooms(self.player.map_name)
            opened_rooms = self.getOpenedRoomsCount()
            
            if opened_rooms < min_rooms:
                logger.info(f"已打开房间数量不足，需要{min_rooms}个，当前{opened_rooms}个")
                return False
            
            # 检查是否在有效地图中
            if not self.is_in_map():
                logger.info("不在地图中")
                return False
            
            return True
        except Exception as e:
            logger.error(f"检查地图条件异常: {str(e)}")
            return False