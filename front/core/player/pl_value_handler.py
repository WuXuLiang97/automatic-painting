# -*- coding: utf-8 -*-
import time
import re
from utils.logging_setup import logger
from utils.cross_control import pyauto


class PlValueHandler:
    """
    体力值处理类，负责识别和管理玩家的体力值
    """
    
    def __init__(self, player=None, mm=None, operator_module=None):
        """
        初始化体力值处理器
        
        :param player: 玩家对象
        :param mm: 图像匹配工具
        :param operator_module: 操作模块
        """
        self.player = player
        self.mm = mm
        self.operator_module = operator_module
        self.pl_value_config = {
            "ocr_retry_times": 5,
            "ocr_timeout": 10
        }
        
    def apply_config(self, config_data):
        """
        应用配置数据
        
        :param config_data: 配置字典
        """
        if not config_data:
            return
        
        # 更新体力值配置
        if "pl_value_config" in config_data:
            self.pl_value_config.update(config_data["pl_value_config"])
    
    def ocr_pl(self, get_text_func, send_log_func):
        """
        识别疲劳值
        
        :param get_text_func: 获取文本的函数
        :param send_log_func: 发送日志的函数
        :return: 体力值整数或None
        """
        def contains_digit(s):
            """检查字符串是否包含数字"""
            pattern = r'\d'
            return bool(re.search(pattern, s))
        
        # 尝试关闭可能存在的弹窗
        ret = self.mm.FindPic(718, 30, 897, 107, "叉.bmp", 0.9)
        if ret:
            x, y = ret[0][1], ret[0][2]
            self.operator_module.move_to(x, y)
            time.sleep(0.1)
            pyauto.click()
            time.sleep(0.2)
        
        start_time = time.time()
        for i in range(self.pl_value_config["ocr_retry_times"]):
            try:
                # 超时检查
                if time.time() - start_time > self.pl_value_config["ocr_timeout"]:
                    logger.warning("识别疲劳值超时")
                    send_log_func("识别疲劳值超时")
                    return None
                
                # 定位到体力值区域
                self.operator_module.move_to(870, 593)
                time.sleep(0.1)
                
                # 尝试第一种识别方式
                results = get_text_func(824, 570, 930, 589, amplify=True)
                if contains_digit(results):
                    match = re.search(r'(\d+)/', results)
                    if match:
                        pl_int = int(match.group(1))
                        logger.info(f"当前疲劳值：{pl_int}")
                        send_log_func(f"当前疲劳值：{pl_int}")
                        return pl_int
                    else:
                        logger.info("满级角色ocr疲劳没有找到匹配项")
                        send_log_func("满级角色ocr疲劳没有找到匹配项")
                        continue
                
                # 尝试第二种识别方式
                results = get_text_func(641, 518, 762, 533, amplify=True)
                match = re.search(r'(\d+)/', results)
                if match:
                    pl_int = int(match.group(1))
                    logger.info(f"当前疲劳值：{pl_int}")
                    send_log_func(f"当前疲劳值：{pl_int}")
                    return pl_int
                else:
                    logger.info("未满级角色ocr疲劳没有找到匹配项")
                    send_log_func("未满级角色ocr疲劳没有找到匹配项")
                    
            except Exception as e:
                logger.error(f"识别疲劳值异常：{str(e)}")
                send_log_func(f"识别疲劳值异常：{str(e)}")
            
            time.sleep(0.5)
        
        logger.warning("多次尝试识别疲劳值失败")
        send_log_func("多次尝试识别疲劳值失败")
        return None
        
    def check_pl_value(self, target_pl_value=None):
        """
        检查体力值是否小于等于目标体力值
        
        :param target_pl_value: 目标体力值，如果为None则使用玩家对象中的pl_value
        :return: 布尔值，表示是否满足条件
        """
        if not self.player or not hasattr(self.player, 'pl_value'):
            logger.warning("玩家对象或pl_value属性不存在")
            return False
        
        # 使用传入的目标体力值或玩家对象中的体力值
        check_pl_value = target_pl_value if target_pl_value is not None else self.player.pl_value
        
        # 定义临时的日志函数，避免过多的日志输出
        def temp_send_log(msg):
            pass
        
        # 识别当前体力值
        current_pl = self.ocr_pl(self.player.get_text, temp_send_log)
        
        # 检查体力值是否满足条件
        if current_pl is not None and isinstance(current_pl, (int, float)) and current_pl <= check_pl_value:
            logger.info(f"当前体力值{current_pl}小于等于目标体力值{check_pl_value}")
            return True
        
        return False
        
    def get_pl_value_status(self):
        """
        获取体力值状态信息
        
        :return: 包含体力值状态的字典
        """
        # 定义临时的日志函数
        def temp_send_log(msg):
            pass
        
        # 识别当前体力值
        current_pl = self.ocr_pl(self.player.get_text, temp_send_log)
        
        # 构建状态信息
        status = {
            "current_pl": current_pl,
            "player_pl_value": self.player.pl_value if self.player and hasattr(self.player, 'pl_value') else None,
            "is_enough": False
        }
        
        # 检查体力是否足够
        if status["current_pl"] is not None and status["player_pl_value"] is not None:
            status["is_enough"] = status["current_pl"] > status["player_pl_value"]
        
        return status