import ctypes
from static_fields import KEY_CODE_DICT, MSDK_DLL_PATH
from ctypes import wintypes

class DeviceMouseKeyboard():
    def __init__(self, w, h, move_flag=1, KeyDelay=None):
        # 初始化参数
        self.w, self.h = w, h
        self.move_flag = move_flag
        self.KeyDelay = KeyDelay

        # 初始化易建鼠dll
        VID, PID = 0xC216, 0x0301
        self.objdll = ctypes.windll.LoadLibrary(MSDK_DLL_PATH)  # 注册dll
        self.objdll.M_Open_VidPid.restype = wintypes.LPHANDLE
        self.hdl = self.objdll.M_Open_VidPid(VID, PID)  # 获取usb键鼠
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
        self.KeyPress(KEY_CODE_DICT[__str])

    def KeyDown(self, code):
        self.objdll.M_KeyDown2(self.hdl, code, 1)

    def KeyUp(self, code):
        self.objdll.M_KeyUp2(self.hdl, code, 1)

    def KeyDownChar(self, __str):
        self.KeyDown(KEY_CODE_DICT[__str])

    def KeyUpChar(self, __str):
        self.KeyUp(KEY_CODE_DICT[__str])

    def KeyState(self, code):
        self.objdll.M_KeyState2(self.hdl, code)

    def KeyStateChar(self, __str):
        self.KeyState(KEY_CODE_DICT[__str])

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
