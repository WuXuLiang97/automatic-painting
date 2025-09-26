import time
import random
import time
from utils.logging_setup import logger
from core import global_variable as gv
from datetime import datetime, timedelta

class TaskHandler:
    def __init__(self):
        """初始化任务处理器"""
        self.player = None  # 玩家引用，在PlayerThread中设置
        self.mm = None  # 鼠标管理器引用，在PlayerThread中设置
        self.send_log = None  # 日志发送函数，在PlayerThread中设置
        self.operator_module = None  # 操作模块引用，在PlayerThread中设置
        self.ocr_module = None  # OCR模块引用，在PlayerThread中设置
        self.image_detection = None  # 图像检测模块引用，在PlayerThread中设置
        
        # 任务状态
        self.task_state = {
            "current_task": "",
            "task_step": 0,
            "task_progress": 0,
            "task_completed": False,
            "last_task_time": 0
        }
        
        # 任务配置
        self.task_config = {
            "task_interval": 3600,  # 任务间隔（秒）
            "max_task_time": 1800,  # 最大任务时间（秒）
            "task_retry_count": 3  # 任务重试次数
        }
        
        # 每日任务相关
        self.daily_tasks_completed = False
        self.daily_task_last_run = 0
        self.role_selection_index = 0
    
    def apply_config(self, config_data):
        """应用配置数据"""
        if not config_data:
            return
        
        # 更新任务配置
        if "task_config" in config_data:
            self.task_config.update(config_data["task_config"])
    
    def daily_tasks(self):
        """处理每日任务"""
        try:
            current_time = time.time()
            # 检查是否已经完成每日任务
            if self.daily_tasks_completed:
                # 检查是否已经过了一天
                if current_time - self.daily_task_last_run >= 86400:  # 24小时
                    self.daily_tasks_completed = False
                else:
                    return True
            
            # 执行每日任务逻辑
            self.select_role()
            self.waiting_for_the_text_to_appear()
            
            # 标记每日任务已完成
            self.daily_tasks_completed = True
            self.daily_task_last_run = current_time
            return True
        except Exception as e:
            logger.error(f"执行每日任务时出错: {str(e)}")
            return False
    
    def select_role(self):
        """选择角色"""
        try:
            # 角色选择逻辑
            self.send_log("正在选择角色...")
            # 这里可以实现具体的角色选择逻辑
            # 例如，使用鼠标点击特定位置
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"选择角色时出错: {str(e)}")
            return False
    
    def waiting_for_the_text_to_appear(self):
        """等待文本出现"""
        try:
            self.send_log("等待文本出现...")
            # 实现等待特定文本出现的逻辑
            # 可以使用OCR模块来检测文本
            time.sleep(3)
            return True
        except Exception as e:
            logger.error(f"等待文本出现时出错: {str(e)}")
            return False
    
    def reset_task_state(self):
        """重置任务状态"""
        self.task_state = {
            "current_task": "",
            "task_step": 0,
            "task_progress": 0,
            "task_completed": False,
            "last_task_time": time.time()
        }
        
    def wait_until_next_start(self, hour=6):
        """等待到次日指定时间"""
        try:
            wait_time = self.calculate_wait_time(hour)
            self.send_log(f"等待到次日{hour}点，还需等待{int(wait_time/3600)}小时{int((wait_time%3600)/60)}分钟")
            
            # 等待过程中可以添加一些状态检查
            start_time = time.time()
            while time.time() - start_time < wait_time:
                # 每30秒检查一次是否需要提前退出等待
                time.sleep(30)
                if not self.player.brush_running:
                    break
            
            # 重置任务状态
            self.reset_task_state()
            return True
        except Exception as e:
            logger.error(f"等待到次日指定时间时出错: {str(e)}")
            return False
    
    def calculate_wait_time(self, hour=6):
        """计算到次日指定时间的等待时间"""
        try:
            now = datetime.now()
            # 设置目标时间为明天的指定小时
            target = (now + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)
            # 计算等待时间
            wait_seconds = (target - now).total_seconds()
            return wait_seconds
        except Exception as e:
            logger.error(f"计算等待时间时出错: {str(e)}")
            return 0