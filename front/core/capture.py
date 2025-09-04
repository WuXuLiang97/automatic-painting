import time
from ctypes import windll, byref, c_ubyte
from ctypes.wintypes import RECT
import cv2
import numpy as np
from global_fields import Capture_lock

def Capture(handle, x1=0, y1=0, x2=None, y2=None):
    '''
    后台截图
    :param handle: 句柄
    :param x1:
    :param y1:
    :param x2:
    :param y2:
    :return:
    '''
    with Capture_lock:
        GetDC = windll.user32.GetDC
        CreateCompatibleDC = windll.gdi32.CreateCompatibleDC
        GetClientRect = windll.user32.GetClientRect
        CreateCompatibleBitmap = windll.gdi32.CreateCompatibleBitmap
        SelectObject = windll.gdi32.SelectObject
        BitBlt = windll.gdi32.BitBlt
        SRCCOPY = 0x00CC0020
        GetBitmapBits = windll.gdi32.GetBitmapBits
        DeleteObject = windll.gdi32.DeleteObject
        ReleaseDC = windll.user32.ReleaseDC
        windll.user32.SetProcessDPIAware()
        r = RECT()
        GetClientRect(handle, byref(r))
        width, height = r.right, r.bottom
        if x2 is None:
            x2 = width
        if y2 is None:
            y2 = height
        dc = GetDC(handle)
        cdc = CreateCompatibleDC(dc)
        bitmap = CreateCompatibleBitmap(dc, x2 - x1, y2 - y1)
        SelectObject(cdc, bitmap)
        BitBlt(cdc, 0, 0, x2 - x1, y2 - y1, dc, x1, y1, SRCCOPY)
        total_bytes = (x2 - x1) * (y2 - y1) * 4
        buffer = bytearray(total_bytes)
        byte_array = c_ubyte * total_bytes
        GetBitmapBits(bitmap, total_bytes, byte_array.from_buffer(buffer))
        DeleteObject(bitmap)
        DeleteObject(cdc)
        ReleaseDC(handle, dc)
    # 原始的返回语句
    # return np.frombuffer(buffer, dtype=np.uint8).reshape(y2 - y1, x2 - x1, 4)

    # 修改后的返回语句，去除alpha通道
    return np.frombuffer(buffer, dtype=np.uint8).reshape(y2 - y1, x2 - x1, 4)[:, :, :3]


if __name__ == '__main__':
    st = time.time()
    pic = Capture(722676, 0, 0, 1067, 600)
    print(f'耗时:{time.time() - st}')
    cv2.imshow('123', pic)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
