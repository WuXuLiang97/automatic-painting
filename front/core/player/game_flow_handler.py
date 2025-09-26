import time
import random
import logging
import re
import time
from PyQt5.QtCore import pyqtSignal, QObject
from core import global_variable as gv
from utils.screenshot_util import screenshot_util
from utils.minimap_util import miniMapUtil
from core.common import a_mapInfo

logger = logging.getLogger(__name__)

class GameFlowHandler(QObject):
    def __init__(self):
        super().__init__()
        self.brush_running = True  # 用于控制刷图流程的运行状态
    def enter_map(self):
        """进入地图的具体实现"""
        logger.info(f"准备进入地图: {self.player.map_name}")
        
        try:
            # 关闭按钮检测与点击逻辑
            close_button = self.mm.find_close_button()
            if close_button:
                self.operator_module.click(close_button)
                time.sleep(0.5)
                
            # 传送阵菜单点击操作
            teleport_pos = self.mm.find_teleport_position()
            if teleport_pos:
                self.operator_module.click(teleport_pos)
                time.sleep(1.0)
                
                # 风暴幽城地图特殊处理
                if "风暴幽城" in self.player.map_name:
                    storm_pos = self.mm.find_storm_position()
                    if storm_pos:
                        self.operator_module.move_to_and_click(storm_pos)
                        time.sleep(1.0)
                        
                # 方向键控制逻辑
                for _ in range(10):
                    if self.check_back_to_town_button():
                        break
                    self.operator_module.press_right_key()
                    time.sleep(0.2)
                
                # 地图等级选择
                for _ in range(5):
                    self.operator_module.press_right_key()
                    time.sleep(0.1)
                    
                # 点击确定进入地图
                confirm_pos = self.mm.find_confirm_position()
                if confirm_pos:
                    self.operator_module.click(confirm_pos)
                    time.sleep(2.0)
                    return 0
                    
            return -1
        except Exception as e:
            logger.error(f"进入地图时发生异常: {str(e)}")
            self.send_log(f"进入地图失败: {str(e)}")
            return -1
            
    def check_back_to_town_button(self):
        """检查是否出现返回城镇按钮"""
        try:
            back_button = self.mm.find_back_to_town_button()
            return back_button is not None
        except Exception:
            return False
    def brush_map(self):
        """核心刷图逻辑实现"""
        logger.info('开始刷图')
        while self.player.brush_running and self.brush_running:
            # 获取检测结果
            self.player.get_yolo_res()
            
            # 提取重复使用的变量，减少计算次数
            current_room_id = self.player.player_room_id
            pickup_count = getattr(self.player, 'room_item_pickup_counts', {}).get(current_room_id, 0)
            has_doors = len(getattr(self.player, 'doors', [])) > 0
            has_monsters = len(getattr(self.player, 'monsters', [])) > 0
            has_goods = len(getattr(self.player, 'goods', [])) > 0
            is_boss = getattr(self.player, 'is_boss', False)
            has_continue = getattr(self.player, 'has_continue', False)
            
            # 添加拾取次数检查 - 如果已经拾取超过10次，不再拾取
            can_pickup_goods = has_goods and pickup_count < 10
            
            # 调试日志
            logger.info(
                f"\nbrush_map:"\
                f"\n\tself.doors:{len(getattr(self.player, 'doors', []))}"\
                f"\n\tself.has_continue:{has_continue}"\
                f"\n\tself.player.player_room_id:{current_room_id}"\
                f"\n\tself.room_item_pickup_counts:{pickup_count}"\
                f"\n\tself.goods:{len(getattr(self.player, 'goods', []))}"\
                f"\n\tself.monsters:{len(getattr(self.player, 'monsters', []))}"\
                f"\n\tself.is_boss:{is_boss}"
            )
            
            # 分支1：存在门且无需继续上一操作
            if has_doors and not has_continue:
                if can_pickup_goods:  # 只有在拾取次数未超限时才拾取
                    self.player.pickup_goods()
                else:
                    self.player.enter_door()
            
            # 分支2：无门 或 需要继续上一操作
            else:
                # 优先处理怪物逻辑
                if has_monsters:
                    if is_boss:
                        self.player.process_boss_room()
                    else:
                        self.player.attach_monster()
                # 无怪物时，处理物品或进门
                else:
                    # 满足物品拾取条件且拾取次数未超限时优先拾取
                    if can_pickup_goods and not has_continue:
                        self.player.pickup_goods()
                    # 非BOSS房间：无物品/不可拾取时进门
                    elif not is_boss:
                        self.player.enter_door()
                    # BOSS房间：无物品/不可拾取时处理BOSS逻辑
                    else:
                        self.player.process_boss_room()
        return 0