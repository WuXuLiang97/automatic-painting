# -*- coding: utf-8 -*-
import ctypes
import os
import time
from ctypes import wintypes
from root_dir import root_path
import win32api

code_dict = {
    "1": 49,

    "2": 50,

    "3": 51,

    "4": 52,

    "5": 53,

    "6": 54,

    "7": 55,

    "8": 56,

    "9": 57,

    "0": 48,

    "-": 189,

    "=": 187,

    "back": 8,

    "a": 65,

    "b": 66,

    "c": 67,

    "d": 68,

    "e": 69,

    "f": 70,

    "g": 71,

    "h": 72,

    "i": 73,

    "j": 74,

    "k": 75,

    "l": 76,

    "m": 77,

    "n": 78,

    "o": 79,

    "p": 80,

    "q": 81,

    "r": 82,

    "s": 83,

    "t": 84,

    "u": 85,

    "v": 86,

    "w": 87,

    "x": 88,

    "y": 89,

    "z": 90,

    "ctrl": 17,

    "alt": 18,

    "shift": 16,

    "win": 91,

    "space": 32,

    "cap": 20,

    "tab": 9,

    "~": 192,

    "esc": 27,

    "enter": 13,

    "up": 38,

    "down": 40,

    "left": 37,

    "right": 39,

    "option": 93,

    "print": 44,

    "delete": 46,

    "home": 36,

    "end": 35,

    "pgup": 33,
    "pgdn": 34,

    "f1": 112,

    "f2": 113,

    "f3": 114,

    "f4": 115,

    "f5": 116,

    "f6": 117,

    "f7": 118,

    "f8": 119,

    "f9": 120,

    "f10": 121,

    "f11": 122,

    "f12": 123,

    "[": 219,

    "]": 221,

    "\\": 220,

    ";": 186,

    "'": 222,

    ",": 188,

    ".": 190,

    "/": 191,

}


class YJS():
    def __init__(self):
        self.w, self.h = None, None
        self.move_flag = 1
        self.KeyDelay = None
        self.objdll = None
        self.hdl = None

    def init(self, w, h, vid, pid, move_flag=1, KeyDelay=None):
        # 初始化参数
        self.w, self.h = w, h
        self.move_flag = move_flag
        self.KeyDelay = KeyDelay

        # 初始化易建鼠dll
        VID, PID = vid, pid
        __path = os.path.join(root_path, "utils/msdk.dll")
        # __path = os.getcwd() + os.path.sep + "msdk.dll"
        self.objdll = ctypes.windll.LoadLibrary(__path)  # 注册dll
        self.objdll.M_Open_VidPid.restype = wintypes.LPHANDLE
        self.hdl = self.objdll.M_Open_VidPid(int(VID, 16),int(PID, 16))  # 获取usb键鼠
        self.__ResolutionUsed()
        if self.hdl == -1:
            raise "打开失败"
        # 设置鼠标轨迹
        self.__EnableRealMouse(self.move_flag)
        # 设置键盘点击延迟随机
        self.__EnableRealKeypad(KeyDelay)
        # 设置随机延迟
        # self.__ResolutionUsed()

    def __del__(self):
        self.objdll.M_ReleaseAllKey(self.hdl)

    def __ResolutionUsed(self):
        # 如果使用绝对移动,则需要初始化分辨率
        if self.move_flag == 1:
            # hdl = ctypes.c_int(self.hdl)
            self.objdll.M_ResolutionUsed(self.hdl, self.w, self.h)

    def GetSn(self):
        len_ = wintypes.DWORD()
        buf = wintypes.CHAR()
        self.objdll.M_GetDevSn(self.hdl, ctypes.byref(len_), ctypes.byref(buf))
        print(len_.value)

    def __EnableRealMouse(self, move_flag: int):
        # 默认每次移动100-127个像素,时间间隔10-20ms
        self.move_flag = move_flag

    def __EnableRealKeypad(self, KeyDelay):
        # 默认50-80ms
        if KeyDelay is None:
            return

        # 上下延迟50%
        self.__SetKeypadDelay(0, KeyDelay * 0.5, KeyDelay * 1.5)

    def __SetKeypadDelay(self, __type, mix_delay, max_delay):
        self.objdll.M_SetParam(self.hdl, __type, mix_delay, max_delay)

    def KeyPress(self, code):
        self.objdll.M_KeyPress2(self.hdl, code, 1)

    def KeyPressChar(self, __str):
        self.KeyPress(code_dict[__str])

    def KeyDown(self, code):
        self.objdll.M_KeyDown2(self.hdl, code, 1)

    def KeyUp(self, code):
        self.objdll.M_KeyUp2(self.hdl, code, 1)

    def KeyDownChar(self, __str):
        self.KeyDown(code_dict[__str])

    def KeyUpChar(self, __str):
        self.KeyUp(code_dict[__str])

    def KeyState(self, code):
        self.objdll.M_KeyState2(self.hdl, code)

    def KeyStateChar(self, __str):
        self.KeyState(code_dict[__str])

    def MoveTo(self, x: int, y: int):
        # 瞬间移动
        if self.move_flag == 0:
            # hdl = ctypes.c_char_p(self.hdl)
            self.objdll.M_MoveTo3_D(self.hdl, x, y)

        # 模拟移动
        elif self.move_flag == 1:
            self.objdll.M_MoveTo3(self.hdl, x, y)

    def LeftClick(self):
        self.objdll.M_LeftClick(self.hdl, 1)

    def RightClick(self):
        self.objdll.M_RightClick(self.hdl, 1)

    def LeftDown(self):
        self.objdll.M_LeftDown(self.hdl)

    def LeftUp(self):
        self.objdll.M_LeftUp(self.hdl)

    def RightDown(self):
        self.objdll.M_RightDown(self.hdl)

    def RightUp(self):
        self.objdll.M_RightUp(self.hdl)

    def LeftDoubleClick(self):
        self.objdll.M_LeftDoubleClick(self.hdl, 1)

    def KeyPressStr(self, str_: str):
        bt_str = str_.encode(encoding="gbk")
        len_ = len(bt_str)
        p_str = ctypes.c_char_p(bt_str)
        self.objdll.M_KeyInputStringGBK(self.hdl, p_str, len_)

    def Close(self):
        self.objdll.M_Close(self.hdl)

    def ReleaseAllKey(self):
        self.objdll.M_ReleaseAllKey(self.hdl)


# # 获取屏幕的宽度和高度
# screen_width = win32api.GetSystemMetrics(0)
# screen_height = win32api.GetSystemMetrics(1)
# yjs = YJS(screen_width, screen_height, 1)

if __name__ == '__main__':
    time.sleep(1)
    # yjs.KeyDown('esc')
    # yjs.KeyUp('esc')
    # yj11111s.LeftDoubleClick()
    # yjs.GetSn()
    # yjs.MoveTo(500, 500)
    # yjs.KeyPressStr("11111")
    # yjs.KeyPressChar("left")
    # yjs.KeyDownChar("left")
    # time.sleep(1)
    # yjs.MoveTo(1027, 728)
