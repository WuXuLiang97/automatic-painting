# -*- coding: utf-8 -*-
"""
移动记录模块
负责记录和回放玩家的移动操作
"""
import time
import random
import pyautogui as pyauto
from utils.logging_setup import logger

class MovementRecorder:
    def __init__(self):
        """初始化移动记录器"""
        self.recorded_movements = []
        self.is_recording = False
        self.recording_start_time = 0
    
    def start_recording(self):
        """开始记录移动"""
        self.recorded_movements = []
        self.is_recording = True
        self.recording_start_time = time.time()
        logger.info("开始记录移动操作")
    
    def stop_recording(self):
        """停止记录移动"""
        self.is_recording = False
        logger.info(f"停止记录移动操作，共记录了 {len(self.recorded_movements)} 个操作")
        return self.recorded_movements
    
    def record_movement(self, movement_type, *args):
        """记录单个移动操作"""
        if self.is_recording:
            timestamp = time.time() - self.recording_start_time
            self.recorded_movements.append({
                'type': movement_type,
                'args': args,
                'timestamp': timestamp
            })
    
    def replay_movements(self, movements=None):
        """
        回放记录的移动操作
        :param movements: 要回放的移动操作列表，如果为None则回放当前记录的操作
        """
        try:
            movements_to_replay = movements if movements else self.recorded_movements
            if not movements_to_replay:
                logger.warning("没有可回放的移动操作")
                return False
            
            logger.info(f"开始回放 {len(movements_to_replay)} 个移动操作")
            
            # 回放第一个操作前不需要等待
            if movements_to_replay:
                self._execute_movement(movements_to_replay[0])
                
                # 回放后续操作，保持时间间隔
                for i in range(1, len(movements_to_replay)):
                    prev_movement = movements_to_replay[i-1]
                    current_movement = movements_to_replay[i]
                    
                    # 计算两个操作之间的时间间隔
                    time_diff = current_movement['timestamp'] - prev_movement['timestamp']
                    if time_diff > 0:
                        time.sleep(time_diff)
                    
                    self._execute_movement(current_movement)
            
            logger.info("移动操作回放完成")
            return True
        except Exception as e:
            logger.error(f"回放移动操作时发生异常: {str(e)}")
            return False
    
    def _execute_movement(self, movement):
        """执行单个移动操作"""
        movement_type = movement['type']
        args = movement['args']
        
        try:
            if movement_type == 'left_right_move':
                direction, duration = args
                self.left_right_move(direction, duration)
            elif movement_type == 'up_down_move':
                direction, duration = args
                self.up_down_move(direction, duration)
            elif movement_type == 'left_right_up_down_move_by':
                move_info, is_forever = args
                self.left_right_up_down_move_by(move_info, is_forever)
            # 可以根据需要添加更多的移动类型
        except Exception as e:
            logger.error(f"执行移动操作时发生异常: {str(e)}")
    
    # 以下是实际的移动控制方法
    def left_right_move(self, direction, duration):
        """左右移动角色"""
        try:
            logger.info(f"左右移动: {direction}, 持续时间: {duration}秒")
            if direction == "left":
                pyauto.keyDown('left')
                time.sleep(duration)
                pyauto.keyUp('left')
            elif direction == "right":
                pyauto.keyDown('right')
                time.sleep(duration)
                pyauto.keyUp('right')
        except Exception as e:
            logger.error(f"左右移动时发生异常: {str(e)}")
            pyauto.keyUp('left')
            pyauto.keyUp('right')
    
    def up_down_move(self, direction, duration):
        """上下移动角色"""
        try:
            logger.info(f"上下移动: {direction}, 持续时间: {duration}秒")
            if direction == "up":
                pyauto.keyDown('up')
                time.sleep(duration)
                pyauto.keyUp('up')
            elif direction == "down":
                pyauto.keyDown('down')
                time.sleep(duration)
                pyauto.keyUp('down')
        except Exception as e:
            logger.error(f"上下移动时发生异常: {str(e)}")
            pyauto.keyUp('up')
            pyauto.keyUp('down')
    
    def left_right_up_down_move_by(self, move_info, is_forever=False):
        """根据移动信息进行复合移动"""
        try:
            # 模拟玩家的移动行为
            if hasattr(move_info, 'leftRightDirection') and hasattr(move_info, 'xTime'):
                direction = move_info.leftRightDirection
                duration = move_info.xTime / 1000.0  # 假设xTime是以毫秒为单位的
                self.left_right_move(direction, duration)
                
            if hasattr(move_info, 'upDownDirection') and hasattr(move_info, 'yTime'):
                direction = move_info.upDownDirection
                duration = move_info.yTime / 1000.0  # 假设yTime是以毫秒为单位的
                self.up_down_move(direction, duration)
            
        except Exception as e:
            logger.error(f"复合移动时发生异常: {str(e)}")
            # 释放所有按键
            pyauto.keyUp('left')
            pyauto.keyUp('right')
            pyauto.keyUp('up')
            pyauto.keyUp('down')

# 提供一个默认的实例
movement_recorder = MovementRecorder()