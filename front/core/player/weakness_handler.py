import time
from PyQt5.QtCore import QObject

class WeaknessHandler(QObject):
    """处理游戏中的虚弱状态"""
    
    def __init__(self):
        super().__init__()
        self.player = None
        self.mm = None
        self.operator_module = None
        self.send_log = None
        self.brush_running = None
    
    def handle_weakness(self, setting=None):
        """
        处理虚弱状态
        
        Args:
            setting: 虚弱设置，可以是'gold', 'contract', 'wait'或'ignore'
        
        Returns:
            bool: 是否成功处理虚弱状态
        """
        try:
            if setting == 'gold' or setting == 'contract':
                # 使用金币或契约移除虚弱
                self.operator_module.remove_weakness()
                return True
            elif setting == 'wait':
                # 等待虚弱自动恢复
                _sleep = 30  # 默认等待30秒
                if isinstance(setting, dict) and 'wait_seconds' in setting:
                    _sleep = setting['wait_seconds']
                self.send_log(f"虚弱，休息{_sleep}秒")
                time.sleep(_sleep)
                return True
            elif setting == 'ignore':
                # 忽略虚弱状态
                self.send_log("忽略虚弱状态")
                return True
            else:
                # 默认行为
                self.send_log(f"未知的虚弱设置: {setting}")
                return False
        except Exception as e:
            self.send_log(f"处理虚弱状态时出错: {str(e)}")
            return False