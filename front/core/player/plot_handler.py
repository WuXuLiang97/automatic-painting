import time
import logging
from PyQt5.QtCore import QObject
import pyautogui as pyauto
from utils import skill_util, screenshot_util

logger = logging.getLogger(__name__)

class PlotHandler(QObject):
    """剧情模式处理器，负责处理游戏中的剧情模式相关逻辑"""
    
    def __init__(self, player, mm, operator_module, map_handler):
        super().__init__()
        self.player = player
        self.mm = mm
        self.operator_module = operator_module
        self.map_handler = map_handler
        self.plot_running = True
        
    def initialize_plot(self):
        """初始化剧情模式的必要设置"""
        # 设置玩家信息
        if not hasattr(self.player, 'player_height') or not self.player.player_height:
            self.player.player_height = 140
            
        # 根据职业调整玩家身高
        if hasattr(self.player, 'player_occupation') and self.player.player_occupation:
            from core.common import occupationInfoMap
            if self.player.player_occupation in occupationInfoMap:
                self.player.player_height = occupationInfoMap[self.player.player_occupation][3]
                
        # 初始化地图信息
        self.player.map_name = "通用"
        self.player.map_level = 1
        self.player.has_get_speed = False
        self.player.is_daily_tasks = "是"
        
    def enter_plot_map(self):
        """进入剧情地图"""
        logger.info(f"准备进入剧情地图: {self.player.map_name}")
        
        # 地图名称处理
        self.player.send_log(f"地图名称: {self.player.map_name}")
        self.player.miniMapUtil.set_map_name(self.player.map_name)
        
        # 激活窗口
        self.player.win32_api.set_active_window(self.player.game_hwnd)
        
        # 设置半自动剧情
        self.player.send_log(f"半自动剧情")
        
        # 检查体力值
        if not self.player.pl_value_handler.check_pl_value():
            return False
        
        # 初始化地图信息
        from core.common import a_mapInfo
        import copy
        self.player.room_info_map = copy.deepcopy(a_mapInfo.get(self.player.map_name, {}))
        logger.info(f"地图初始化完成: {self.player.room_info_map}")
        self.player.send_log(f"房间列表: {list(self.player.room_info_map.keys())}")
        
        return True
    
    def handle_plot_map_logic(self):
        """处理剧情地图的核心逻辑"""
        while self.plot_running:
            # 普通图处理逻辑
            if self.player.map_name != "深渊：终末崇拜者":
                # 获取当前房间ID
                self.player.player_room_id = self.player.miniMapUtil.get_current_room_id()
                logger.info(f"当前房间ID: {self.player.player_room_id}")
                
                # 获取小地图YOLO结果
                self.player.get_yolo_res()
                
                # 等待房间ID变化
                if not self.player.player_room_id:
                    time.sleep(0.5)
                    continue
            else:
                # 深渊图特殊处理
                screenshot = self.player.capture.screenshot(self.player.game_hwnd)
                # 识别右上角文字
                text = self.player.identifier.identify_upper_right_text(screenshot)
                # 清理非中文字符
                import re
                text = re.sub(r'[^\u4e00-\u9fa5]', '', text)
                # 相似度判断
                if hasattr(self.player, 'calculate_similarity'):
                    similarity = self.player.calculate_similarity(text, "深渊：终末崇拜者")
                    if similarity > 0.7:
                        break
                time.sleep(0.5)
                continue
            
            break
        
        # 检查地图是否支持
        if self.player.map_name not in self.player.miniMapUtil.minimap:
            self.player.send_log(f"当前地图 {self.player.map_name} 不支持自动刷图")
            return False
        
        return True
    
    def start_plot_brushing(self, brush_func):
        """开始剧情刷图
        
        Args:
            brush_func: 刷图函数
        
        Returns:
            bool: 是否成功开始刷图
        """
        try:
            # 重置boss状态
            self.player.direction_dic.clear()
            self.player.is_boss = False
            self.player.to_door_count = 0
            self.player.first_press_to_exit = True
            
            # 打印房间信息
            for room_list in self.player.room_info_map:
                logger.info(room_list)
            
            # 使用buff
            if hasattr(self.player, 'release_buffer'):
                self.player.release_buffer()
                time.sleep(0.2)
            
            # 获取移速
            if not self.player.has_get_speed:
                if hasattr(self.player, 'get_move_speed'):
                    self.player.get_move_speed()
            
            # 技能初始化
            while self.player.brush_running and not getattr(self.player, 'ghost_state', False):
                logger.info("技能初始化")
                init_status = skill_util.init(screenshot_util.get_game_screenshot(), self.player.player_occupation)
                if init_status:
                    break
            
            # 关闭铃铛
            ret = self.mm.FindPic(727, 474, 885, 557, "魔界人.bmp", 0.9)
            if ret:
                self.operator_module.move_to(743, 576)
                time.sleep(0.05)
                pyauto.click()
                time.sleep(0.05)
            
            logger.info('开始剧情刷图')
            
            # 执行刷图函数
            while self.player.brush_running:
                self.player.get_yolo_res()
                brush_func()
            
            return True
        except Exception as e:
            logger.error(f"剧情刷图发生异常: {str(e)}")
            self.player.send_log(f"剧情刷图失败: {str(e)}")
            return False
    
    def stop_plot(self):
        """停止剧情模式"""
        self.plot_running = False
        self.player.brush_running = False
        logger.info("剧情模式已停止")