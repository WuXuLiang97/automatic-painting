import re
import time
import random
from utils.logging_setup import logger
from core.common import Point

class PlayerStateMonitor:
    """
    角色状态监控器
    职责：集中检测游戏状态、疲劳值、角色状态、坐标位置等
    """
    def __init__(self, operator_module, player, yolo_handler, movement_recorder=None):
        """
        初始化角色状态监控器
        
        :param operator_module: 操作模块实例，用于执行OCR和移动操作
        :param player: 玩家对象，存储玩家基本信息
        :param yolo_handler: YOLO处理模块实例，用于图像处理
        :param movement_recorder: 移动记录器实例，用于位置恢复
        """
        self.operator_module = operator_module
        self.player = player
        self.yolo_handler = yolo_handler
        self.movement_recorder = movement_recorder
        
        # 初始化状态变量
        self.player_pos = Point(None, None)  # 玩家坐标，使用None作为默认值
        self.ghost_state = False  # 死亡状态
        self.brush_running = True  # 刷图状态
        self.brush_cnt = 0  # 刷图次数
        self.pl_value = 0  # 疲劳值
        
        # 初始化记录器
        logger.info("PlayerStateMonitor初始化完成")
    
    def get_player_position(self):
        """
        获取玩家当前坐标位置
        
        :return: 玩家X坐标
        """
        self.get_yolo_res()
        logger.info(f"获取玩家坐标：{self.player_pos.x, self.player_pos.y}")
        return self.player_pos.x
        
    def get_player_full_position(self):
        """
        获取玩家完整坐标位置（包含x和y）
        
        :return: 玩家坐标对象
        """
        self.get_yolo_res()
        return self.player_pos
        
    def get_brush_count(self):
        """
        获取当前刷图次数
        
        :return: 刷图次数
        """
        return self.brush_cnt
    
    def get_yolo_res(self, game_image=None):
        """
        获取YOLO识别结果，更新玩家位置
        
        :param game_image: 可选的游戏图像，如果没有则会自动获取
        :return: 识别结果
        """
        try:
            # 定义处理函数，获取结果并应用到context
            def process_and_apply(cls, img):
                result = self.yolo_handler.process_detect_message(cls, img)
                self.yolo_handler.apply_to_context(cls, result)
                # 更新玩家位置
                if hasattr(self.yolo_handler, 'player_pos'):
                    self.player_pos = self.yolo_handler.player_pos
                return result  # 返回结果对象，但保持原有功能
                
            # 确保communication_service已经初始化
            if hasattr(self, 'communication_service') and self.communication_service:
                return self.communication_service.get_yolo_res(
                    game_image=game_image,
                    screenshot_util=getattr(self, 'screenshot_util', None),
                    process_detect_message=process_and_apply
                )
            # 如果没有communication_service，尝试直接从yolo_handler获取
            elif hasattr(self.yolo_handler, 'player_pos'):
                logger.info("通过yolo_handler直接获取玩家位置")
                self.player_pos = self.yolo_handler.player_pos
                return True
            else:
                logger.warning("无法获取YOLO识别结果，communication_service或yolo_handler不可用")
                return False
        except Exception as e:
            logger.info(f"获取YOLO识别结果时发生异常: {e}")
            # 尝试重连
            if hasattr(self, '_reconnect') and callable(getattr(self, '_reconnect')):
                self._reconnect()
            return False
    
    def _recover_player_position(self):
        """
        玩家位置丢失时的恢复策略
        """
        logger.info("尝试螺旋搜索恢复位置")
        if self.movement_recorder:
            self.movement_recorder.spiral_search(self.get_player_position, duration=2)
        self.get_yolo_res()
    
    def ocr_pl(self, get_text_func, send_log_func):
        """
        识别并更新疲劳值
        
        :param get_text_func: 获取文本的函数
        :param send_log_func: 发送日志的函数
        :return: 当前疲劳值
        """
        def contains_digit(s):
            pattern = r'\d'
            return bool(re.search(pattern, s))
        
        ret = self.operator_module.mm.FindPic(718, 30, 897, 107, "叉.bmp", 0.9)
        if ret:
            x, y = ret[0][1], ret[0][2]
            self.operator_module.move_to(x, y)
            time.sleep(0.1)
            pyauto.click()
            time.sleep(0.2)
        
        for i in range(5):
            try:
                self.operator_module.move_to(870, 593)
                time.sleep(0.1)
                # 用传进来的方法识别
                results = get_text_func(824, 570, 930, 589, amplify=True)
                if contains_digit(results):
                    match = re.search(r'(\d+)/', results)
                    if match:
                        pl_int = match.group(1)
                        if pl_int:
                            pl_int = int(pl_int)
                            logger.info(f"当前疲劳值：{pl_int}")
                            send_log_func(f"当前疲劳值：{pl_int}")
                            self.pl_value = pl_int
                        else:
                            logger.info("满级角色ocr疲劳没有找到匹配项")
                            send_log_func("满级角色ocr疲劳没有找到匹配项")
                            continue
                    else:
                        logger.info("满级角色ocr疲劳正则匹配失败")
                        send_log_func("满级角色ocr疲劳正则匹配失败")
                        continue
                else:
                    # 用传进来的方法识别
                    results = get_text_func(641, 518, 762, 533, amplify=True)
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
                            send_log_func(f"当前疲劳值：{pl_int}")
                            self.pl_value = pl_int
                        else:
                            logger.info("未满级角色ocr疲劳没有找到匹配项")
                            send_log_func("未满级角色ocr疲劳没有找到匹配项")
                            continue
                    else:
                        logger.info(f"未满级角色ocr疲劳正则匹配失败，尝试了多种格式")
                        send_log_func("未满级角色ocr疲劳正则匹配失败")
                        continue
                
                self.operator_module.move_to(random.randint(500, 560), 30)
                time.sleep(0.1)
                return self.pl_value
            except Exception as e:
                logger.error(f"OCR疲劳值识别失败: {e}")
                time.sleep(0.5)
                continue
        
        logger.warning("多次尝试后仍无法识别疲劳值")
        return 0
    
    def set_ghost_state(self, state):
        """
        设置角色死亡状态
        
        :param state: 死亡状态（True/False）
        """
        self.ghost_state = state
        logger.info(f"角色死亡状态更新为: {'死亡' if state else '存活'}")
    
    def set_brush_running(self, running):
        """
        设置刷图运行状态
        
        :param running: 运行状态（True/False）
        """
        self.brush_running = running
        logger.info(f"刷图状态更新为: {'运行中' if running else '已停止'}")
    
    def increment_brush_count(self):
        """
        增加刷图次数计数
        """
        self.brush_cnt += 1
        logger.info(f"当前刷图次数: {self.brush_cnt}")
        
    def reset_brush_count(self):
        """
        重置刷图次数计数
        """
        self.brush_cnt = 0
        logger.info("刷图次数已重置")
    
    def is_player_alive(self):
        """
        检查角色是否存活
        
        :return: 是否存活
        """
        return not self.ghost_state
    
    def is_brushing(self):
        """
        检查是否正在刷图
        
        :return: 是否在刷图
        """
        return self.brush_running
    
    def has_enough_pl(self):
        """
        检查是否有足够的疲劳值
        
        :return: 是否有足够疲劳值
        """
        # 考虑玩家对象中的预留疲劳值设置
        if hasattr(self.player, 'pl_value'):
            return self.pl_value > self.player.pl_value
        return self.pl_value > 0
    
    def get_current_state_summary(self):
        """
        获取当前状态的摘要信息
        
        :return: 状态摘要字典
        """
        return {
            "player_pos": (self.player_pos.x, self.player_pos.y),
            "ghost_state": self.ghost_state,
            "brush_running": self.brush_running,
            "brush_count": self.brush_cnt,
            "pl_value": self.pl_value,
            "map_name": getattr(self.player, 'map_name', '未知'),
            "player_alive": self.is_player_alive(),
            "has_enough_pl": self.has_enough_pl()
        }

# 导入pyauto库，用于点击操作
try:
    import pyauto
except ImportError:
    logger.error("未找到pyauto库，请确保正确安装")
    # 创建一个简单的替代实现
    class pyauto:
        @staticmethod
        def click():
            pass
        
        @staticmethod
        def keyPressChar(char):
            pass