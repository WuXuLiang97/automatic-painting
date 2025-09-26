# -*- coding: utf-8 -*-
import time
from utils.cross_control import pyauto
from utils.logging_setup import logger


class MovementRecorder:
    def __init__(self):
        self.last_direction = None  # 记录最后一次移动的方向
        self.sleep = pyauto.PAUSE

    def left_right_move(self, left_or_right, m_time):

        pyauto.keyDownChar(left_or_right)
        time.sleep(self.sleep)
        pyauto.keyUpChar(left_or_right)
        time.sleep(self.sleep)
        pyauto.keyDownChar(left_or_right)
        if m_time - 0.04 > 0:
            time.sleep(m_time - 0.04)
        else:
            if m_time - self.sleep > 0:
                time.sleep(m_time - self.sleep)
            else:
                time.sleep(m_time)
        pyauto.keyUpChar(left_or_right)
        self.last_direction = left_or_right  # 记录方向

    def already_left_right_move(self, left_or_right):
        pyauto.releaseallkey()
        time.sleep(self.sleep)
        pyauto.keyDownChar(left_or_right)
        time.sleep(self.sleep)
        pyauto.keyUpChar(left_or_right)
        time.sleep(self.sleep)
        pyauto.keyDownChar(left_or_right)
        time.sleep(self.sleep)
        self.last_direction = left_or_right  # 记录方向

    def up_down_move(self, up_or_down, m_time):
        pyauto.releaseallkey()
        time.sleep(self.sleep)
        pyauto.keyDownChar(up_or_down)
        time.sleep(m_time)
        pyauto.keyUpChar(up_or_down)
        time.sleep(self.sleep)

    def left_right_up_down_move_walk(self, left_or_right, up_or_down, x_time, y_time, left_right_move_status, run):
        # 当没有处于左右移动状态时（not left_right_move_status）
        # 且存在横向移动时间（x_time != 0）
        # 且目标方向与当前方向不一致时（方向改变）
        # 释放所有按键
        pyauto.releaseallkey()
        time.sleep(self.sleep)
        logger.info(f"目标方向： {left_or_right} 记录方向：{self.last_direction}")
        if left_or_right != self.last_direction:
            if run:
                logger.info("方向不同，加时0.1秒")
                x_time = x_time + 0.1
        if not left_right_move_status and x_time != 0 or left_or_right != self.last_direction:
            pyauto.keyDownChar(left_or_right)
            time.sleep(self.sleep)
        if x_time > y_time:
            if y_time > 0:
                pyauto.keyDownChar(up_or_down)
                time.sleep(y_time)
                pyauto.keyUpChar(up_or_down)
            if x_time - y_time > self.sleep:
                time.sleep(x_time - y_time - self.sleep)
            else:
                time.sleep(self.sleep)
            pyauto.keyUpChar(left_or_right)
        else:
            if x_time == 0:
                pyauto.keyUpChar(left_or_right)
                time.sleep(self.sleep)
                pyauto.keyDownChar(up_or_down)
                if y_time > self.sleep:
                    time.sleep(y_time)
                else:
                    time.sleep(self.sleep)
                pyauto.keyUpChar(up_or_down)
            else:
                pyauto.keyDownChar(up_or_down)
                if x_time > self.sleep:
                    time.sleep(x_time - self.sleep)
                else:
                    time.sleep(self.sleep)
                pyauto.keyUpChar(left_or_right)
                if y_time - x_time > self.sleep:
                    time.sleep(y_time - x_time - self.sleep)
                else:
                    time.sleep(self.sleep)
                pyauto.keyUpChar(up_or_down)
            time.sleep(self.sleep)
        self.last_direction = left_or_right  # 记录方向

    def left_right_up_down_move(self, left_or_right, up_or_down, x_time, y_time, left_right_move_status, run):
        # 当没有处于左右移动状态时（not left_right_move_status）
        # 且存在横向移动时间（x_time != 0）
        # 且目标方向与当前方向不一致时（方向改变）
        logger.info(f"目标方向： {left_or_right} 记录方向：{self.last_direction}")

        if left_or_right != self.last_direction:
            if run:
                logger.info("方向不同，加时0.1秒")
                x_time = x_time + 0.1
        # if not left_right_move_status and x_time != 0 or left_or_right != self.last_direction:
        self.already_left_right_move(left_or_right)
        if x_time > y_time:
            if y_time > 0:
                pyauto.keyDownChar(up_or_down)
                time.sleep(y_time)
                pyauto.keyUpChar(up_or_down)
            if x_time - y_time > self.sleep:
                time.sleep(x_time - y_time - self.sleep)
            else:
                time.sleep(self.sleep)
            pyauto.keyUpChar(left_or_right)
        else:
            if x_time == 0:
                pyauto.keyDownChar(up_or_down)
                if y_time > self.sleep:
                    time.sleep(y_time)
                else:
                    time.sleep(self.sleep)
                pyauto.keyUpChar(up_or_down)
            else:
                pyauto.keyDownChar(up_or_down)
                if x_time > self.sleep:
                    time.sleep(x_time - self.sleep)
                else:
                    time.sleep(self.sleep)
                pyauto.keyUpChar(left_or_right)
                if y_time - x_time > self.sleep:
                    time.sleep(y_time - x_time - self.sleep)
                else:
                    time.sleep(self.sleep)
                pyauto.keyUpChar(up_or_down)
            time.sleep(self.sleep)
        self.last_direction = left_or_right  # 记录方向

    def left_right_up_down_move_by(self, move_info, left_right_move_status):
        if move_info is None:
            return
        self.left_right_up_down_move(move_info.leftRightDirection, move_info.upDownDirection, move_info.xTime, move_info.yTime,
                                     left_right_move_status, move_info.run)

    def left_right_up_down_move_walk_by(self, move_info, left_right_move_status):
        if move_info is None:
            return
        self.left_right_up_down_move_walk(move_info.leftRightDirection, move_info.upDownDirection, move_info.xTime, move_info.yTime,
                                          left_right_move_status, move_info.run)

    def already_right_move(self):

        pyauto.keyDownChar("right")
        time.sleep(self.sleep)
        pyauto.keyUpChar("right")
        time.sleep(self.sleep)
        pyauto.keyDownChar("right")
        self.last_direction = "right"  # 记录方向

    def already_left_move(self):
        pyauto.keyDownChar("left")
        time.sleep(self.sleep)
        pyauto.keyUpChar("left")
        time.sleep(self.sleep)
        pyauto.keyDownChar("left")
        self.last_direction = "left"  # 记录方向

    def spiral_search(self, func: callable, duration=3.0):
        """
        螺旋式移动搜索玩家位置
        参数说明：
            duration: 总搜索时间（秒）
        移动策略：
            1. 采用"右→上→左→下"四方向循环
            2. 每个方向移动时间逐轮递增
            3. 形成逐渐扩大的螺旋路径
        """
        start_time = time.time()
        base_step = 0.3  # 基础移动时间（秒）
        step_increment = 0.15  # 每轮增加时间
        directions = ["right", "down", "left", "up"]  # 移动方向顺序

        current_step = base_step
        cycle_count = 0  # 循环轮次计数器

        # 在指定时间内持续执行螺旋搜索
        while time.time() - start_time < duration:
            # 每轮增加移动时间（前3轮保持基础时间）
            if cycle_count >= 3:
                current_step = base_step + step_increment * (cycle_count - 2)

            # 按当前方向顺序执行移动
            for direction in directions:
                # 检查剩余时间
                if time.time() - start_time >= duration:
                    break

                # 执行单方向移动
                if direction in ["left", "right"]:
                    self.left_right_move(direction, current_step)
                else:
                    self.up_down_move(direction, current_step)

                # 添加微小停顿避免连续移动
                time.sleep(self.sleep)

                cycle_count += 1  # 完成一轮循环
                player_pos_x = func()
                if player_pos_x:
                    pyauto.releaseallkey()
                    logger.info(f"已找回玩家位置：{player_pos_x}")
                    return

        # 确保最后释放所有按键
        pyauto.releaseallkey()
        logger.info(f"完成螺旋搜索，共进行{cycle_count}轮探测")
