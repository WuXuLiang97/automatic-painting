import logging
import copy
import logging
from PyQt5.QtCore import QObject
from utils.minimap_util import miniMapUtil
from core.common import a_mapInfo

logger = logging.getLogger(__name__)

class MapInitializationHandler(QObject):
    def __init__(self):
        super().__init__()
        self.player = None
        self.mm = None
        self.operator_module = None
        self.send_log = None
        
        # 地图状态
        self.room_info_map = None
        self.is_in_map = False
    
    def initialize_map(self, map_name):
        """初始化地图信息"""
        try:
            logger.info(f'初始化地图: {map_name}')
            
            # 获取地图信息
            self.room_info_map = copy.deepcopy(a_mapInfo.get(map_name))
            
            if not self.room_info_map:
                self.send_log(f"未找到地图信息: {map_name}")
                logger.error(f"未找到地图信息: {map_name}")
                return False
            
            # 打印地图房间信息
            for room_list in self.room_info_map:
                logger.info(room_list)
            
            # 设置小地图名称
            miniMapUtil.set_minimap_name(map_name)
            
            self.is_in_map = True
            return True
        except Exception as e:
            logger.error(f"初始化地图时发生异常: {str(e)}")
            self.send_log(f"初始化地图失败: {str(e)}")
            return False
    
    def check_map_support(self, map_name):
        """检查地图是否支持"""
        if map_name in miniMapUtil.minimap:
            return True
        else:
            self.send_log(f"{map_name}地图暂不支持，请检查配置文件")
            return False
    
    def reset_map_state(self):
        """重置地图状态"""
        self.room_info_map = None
        self.is_in_map = False
        logger.info("地图状态已重置")