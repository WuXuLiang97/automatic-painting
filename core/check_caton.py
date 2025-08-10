import time
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QRunnable, QThread
from core.player_move import MovementRecorder
from utils.pyauto_b import pyauto


class CheckPlayerDynamics(QThread):
    def __init__(self):
        super().__init__()
        self.player_dynamics_lists = []
        self.movement_recorder = MovementRecorder()
        self.running = True

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

    def _recover_player_position(self):
        """ 玩家位置丢失恢复策略 """
        print("尝试螺旋搜索恢复位置")
        pyauto.KeyPressChar('=')
        time.sleep(0.05)
        pyauto.KeyPressChar('space')
        time.sleep(0.05)
        self.movement_recorder.spiral_search(duration=1)

    def run(self):
        while self.running:
            if len(self.player_dynamics_lists) >= 3:
                print(f"玩家所在坐标记录：{self.player_dynamics_lists}")
                x_val, y_val = self.find_coordinate_variation(self.player_dynamics_lists)
                print(f"玩家所在坐标记录动态x轴变化幅度为：{x_val}")
                print(f"玩家所在坐标记录动态y轴变化幅度为：{y_val}")
                if x_val <= 20:
                    print(f"执行坐标恢复策略")
                    # 玩家位置恢复
                    self._recover_player_position()
                self.player_dynamics_lists = []
            time.sleep(0.1)

    def stop(self):
        self.running = False
