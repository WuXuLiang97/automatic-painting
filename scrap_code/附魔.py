import ctypes
import random
import time

import pywintypes
import win32con
import win32gui
from pynput import keyboard

from utils.cross_control import pyauto
from mm import MM

mm = MM()


def get_hwnd():
    dnf_hwnd = win32gui.FindWindow('地下城与勇士', '地下城与勇士：创新世纪')
    if dnf_hwnd != 0:
        print("地下城与勇士：创新世纪窗口的句柄:", dnf_hwnd)
    return dnf_hwnd


hwnd = get_hwnd()


def activate_window_by_handle():
    """如果激活成功，已随机延迟10~20毫秒"""
    # 确保handle是整数类型
    if not isinstance(hwnd, int):
        # my_print(f"窗口句柄 {handle} 必须是整数类型")

        return False

        # 检查窗口句柄是否有效
    if not win32gui.IsWindow(hwnd):
        # my_print(f"窗口句柄 {handle} 无效或窗口已关闭")

        return False

    try:
        # 尝试将窗口设置为最前端并激活它
        win32gui.SetForegroundWindow(hwnd)
        win32gui.SendMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)

        time.sleep(random.uniform(0.01, 0.02))
        return True
    except pywintypes.error as e:
        # 如果设置前台窗口失败，并且错误码是ERROR_ACCESS_DENIED，则尝试获取设置前台窗口的权限
        if e.winerror == 5:  # ERROR_ACCESS_DENIED
            current_process_id = ctypes.windll.kernel32.GetCurrentProcessId()
            ctypes.windll.user32.AllowSetForegroundWindow(current_process_id)
            try:
                # 再次尝试设置窗口为最前端并激活它
                win32gui.SetForegroundWindow(hwnd)
                win32gui.SendMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)
                time.sleep(random.uniform(0.01, 0.02))
                return True
            except pywintypes.error as e:
                print(f"激活窗口时出错: {e}")
        else:
            print(f"激活窗口时发生未知错误: {e}")
        return False


def get_window_rect():
    activate_window_by_handle()
    time.sleep(0.2)
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return left, top


left, top = get_window_rect()


def move_too(x, y):
    pyauto.moveTo(left + x, top + y)


pyauto.sign = 1


def move_and_click(x, y, button="left", delay=0.1):
    """移动到指定位置并点击，添加适当延迟"""
    move_too(x, y)
    time.sleep(delay)
    pyauto.click(button)
    time.sleep(delay)


def fumo(c, n, mode=0):
    """
    执行批量操作，支持两种模式：强攻(0)和协(1)

    参数:
    n (int): 操作次数
    mode (int): 模式选择，"0" 或 "1"
    """
    # 模式配置映射
    mode_config = {0: {"position": (537, 229), "key": "强攻"}, 1: {"position": (537, 243), "key": "协"}}

    # 验证模式参数
    if mode not in mode_config:
        raise ValueError(f"不支持的模式: {mode}，请使用int '0' 或 '1'")
    yy = 0
    # 获取模式配置
    config = mode_config[mode]
    ret = mm.FindPic(714, 272, 786, 414, "装备.bmp", 0.9)
    if ret:
        yy = int(ret[0][4] + 37)
        print(yy)
        print(type(yy))
    for i in range(n):
        # 第一步：初始操作
        if c == 0:
            move_and_click(738, yy, "right", 0.5)  # 右键点击，延迟1秒
        elif c == 1:
            move_and_click(770, yy, "right", 0.5)  # 右键点击，延迟1秒
        elif c == 2:
            move_and_click(800, yy, "right", 0.5)  # 右键点击，延迟1秒

        move_and_click(561, 213)

        # 选择模式
        x, y = config["position"]
        move_and_click(x, y)

        # 两次确认点击
        move_and_click(658, 233)
        move_and_click(658, 233)

        # 选择项目
        move_and_click(555, 250 + i * 16)

        # 确定按钮位置（最后一次与其他不同）
        confirm_x, confirm_y = (518, 496) if i == n - 1 else (571, 496)
        move_and_click(confirm_x, confirm_y, delay=0.1)
        time.sleep(0.5)
        # 按下两次空格
        pyauto.KeyPressChar("space")
        time.sleep(0.5)
        pyauto.KeyPressChar("space")
        time.sleep(0.5)


# 全局变量（或类变量）
listener = None
mode = 1
fumo(0, 5, mode)  # 执行操作
fumo(1, 3, mode)  # 执行操作
fumo(2, 3, mode)  # 执行操作
#
# def on_press(key):
#     global listener, mode
#     try:
#         if key == keyboard.Key.home:
#             # 使用示例
#             fumo(0, 5, mode)  # 执行操作
#             fumo(1, 3, mode)  # 执行操作
#             fumo(2, 3, mode)  # 执行操作
#         elif key == keyboard.Key.esc:
#             # 停止监听器
#             listener.stop()
#     except AttributeError:
#         pass
#
#
# def main():
#     global listener, mode
#
#     # 主循环（可以根据需要调整）
#     while True:
#         char_ = input("请输入0或1\t强攻选择 0\t辅助选择 1\n:")
#         print(char_, type(char_))
#         mode = int(char_)
#         if char_ == "0" or char_ == "1":
#             break
#     # 创建监听器
#     listener = keyboard.Listener(on_press=on_press)
#     listener.start()
#     while True:
#         time.sleep(1)
#     # 清理（通常不会执行到这里，因为 listener.stop() 会退出）
#     listener.stop()
#     listener.join()
#     print("KeyboardListenerThread 已停止")
#
#
# if __name__ == "__main__":
#     main()
