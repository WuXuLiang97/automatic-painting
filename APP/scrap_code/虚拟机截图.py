# -*- coding: utf-8 -*-
import ctypes
import time

import win32gui
import win32ui
import win32con
import cv2
import numpy as np
from ctypes import wintypes


# 定义必要的结构体
class DWM_THUMBNAIL_PROPERTIES(ctypes.Structure):
    _fields_ = [
        ("dwFlags", wintypes.DWORD),
        ("rcDestination", wintypes.RECT),
        ("rcSource", wintypes.RECT),
        ("opacity", wintypes.BYTE),
        ("fVisible", wintypes.BOOL),
        ("fSourceClientAreaOnly", wintypes.BOOL)
    ]


def background_capture_printwindow(hwnd):
    """
    后台截取指定窗口的内容（使用PrintWindow API）
    :param hwnd: 窗口句柄
    :return: OpenCV格式的图像
    """
    try:
        # 获取窗口位置和大小
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        # 创建设备上下文
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        # 创建位图对象
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)

        # 选择位图到设备上下文
        saveDC.SelectObject(saveBitMap)

        # 使用PrintWindow将窗口内容复制到内存DC
        result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)  # PW_CLIENTONLY=2

        if result != 1:
            # 如果PrintWindow失败，尝试其他方法
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)

        # 获取位图信息
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)

        # 转换为OpenCV格式
        img = np.frombuffer(bmpstr, dtype=np.uint8).reshape(
            bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        return img

    except Exception as e:
        print(f"后台截图失败: {str(e)}")
        return None
    finally:
        # 清理资源
        if 'saveBitMap' in locals():
            win32gui.DeleteObject(saveBitMap.GetHandle())
        if 'saveDC' in locals():
            saveDC.DeleteDC()
        if 'mfcDC' in locals():
            mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)


def background_capture_dwm(hwnd):
    """使用DWM API进行后台截图"""
    try:
        # 加载DLL
        dwmapi = ctypes.WinDLL('dwmapi')
        user32 = ctypes.WinDLL('user32')
        gdi32 = ctypes.WinDLL('gdi32')

        # 设置函数原型
        dwmapi.DwmRegisterThumbnail.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.POINTER(wintypes.HANDLE)]
        dwmapi.DwmRegisterThumbnail.restype = wintypes.HRESULT
        dwmapi.DwmQueryThumbnailSourceSize.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.POINT)]
        dwmapi.DwmQueryThumbnailSourceSize.restype = wintypes.HRESULT
        dwmapi.DwmUpdateThumbnailProperties.argtypes = [wintypes.HANDLE, ctypes.POINTER(DWM_THUMBNAIL_PROPERTIES)]
        dwmapi.DwmUpdateThumbnailProperties.restype = wintypes.HRESULT
        dwmapi.DwmUnregisterThumbnail.argtypes = [wintypes.HANDLE]
        dwmapi.DwmUnregisterThumbnail.restype = wintypes.HRESULT

        # 获取窗口尺寸
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        # 创建内存DC
        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)

        # 创建位图
        bmi = win32ui.CreateBitmap(width, height, 1, 32, None)
        hbm_old = gdi32.SelectObject(hdc_mem, bmi.GetHandle())

        # 注册缩略图
        thumbnail_handle = wintypes.HANDLE()
        hr = dwmapi.DwmRegisterThumbnail(hdc_screen, hwnd, ctypes.byref(thumbnail_handle))
        if hr != 0:
            print(f"注册缩略图失败: 0x{hr:X}")
            return None

        # 查询源尺寸
        source_size = wintypes.POINT()
        hr = dwmapi.DwmQueryThumbnailSourceSize(thumbnail_handle, ctypes.byref(source_size))
        if hr != 0:
            print(f"查询源尺寸失败: 0x{hr:X}")
            return None

        # 设置缩略图属性
        props = DWM_THUMBNAIL_PROPERTIES()
        props.dwFlags = 0x1 | 0x2 | 0x8  # DWM_TNP_RECTDESTINATION | DWM_TNP_RECTSOURCE | DWM_TNP_SOURCECLIENTAREAONLY
        props.fSourceClientAreaOnly = True
        props.fVisible = True
        props.opacity = 255

        props.rcSource = wintypes.RECT(0, 0, source_size.x, source_size.y)
        props.rcDestination = wintypes.RECT(0, 0, width, height)

        hr = dwmapi.DwmUpdateThumbnailProperties(thumbnail_handle, ctypes.byref(props))
        if hr != 0:
            print(f"更新缩略图属性失败: 0x{hr:X}")
            return None

        # 渲染缩略图到内存DC
        hr = dwmapi.DwmRenderThumbnail(thumbnail_handle, hdc_mem)
        if hr != 0:
            print(f"渲染缩略图失败: 0x{hr:X}")
            return None

        # 获取位图数据
        bmpinfo = bmi.GetInfo()
        bmpstr = bmi.GetBitmapBits(True)

        # 转换为OpenCV格式
        img = np.frombuffer(bmpstr, dtype=np.uint8).reshape(
            bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        return img

    except Exception as e:
        print(f"后台截图失败: {str(e)}")
        return None
    finally:
        # 清理资源
        if 'thumbnail_handle' in locals() and thumbnail_handle.value:
            dwmapi.DwmUnregisterThumbnail(thumbnail_handle)
        if 'bmi' in locals():
            gdi32.SelectObject(hdc_mem, hbm_old)
            bmi.DeleteObject()
        if 'hdc_mem' in locals():
            gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)


def background_capture(hwnd, method='printwindow'):
    """
    后台截图主函数
    :param hwnd: 窗口句柄
    :param method: 截图方法 ('printwindow' 或 'dwm')
    :return: OpenCV格式的图像
    """
    if method == 'dwm':
        return background_capture_dwm(hwnd)
    else:
        return background_capture_printwindow(hwnd)


def find_vm_window(window_class="VMUIFrame"):
    """
    查找虚拟机窗口
    :param window_class: 窗口类名（VMware 默认是 "VMUIFrame"）
    :return: 窗口句柄
    """

    def enum_windows_callback(hwnd, windows_list):
        class_name = win32gui.GetClassName(hwnd)
        if class_name == window_class:
            windows_list.append(hwnd)
        return True

    windows = []
    win32gui.EnumWindows(enum_windows_callback, windows)
    return windows[0] if windows else None


# 使用示例
if __name__ == "__main__":
    # 查找VMware窗口（后台查找，不激活）
    hwnd = find_vm_window()

    if hwnd:
        print(f"找到VMware窗口，句柄: 0x{hwnd:X}")

        # 尝试使用PrintWindow方法
        print("尝试使用PrintWindow方法...")
        stat_t = time.time()
        screenshot = background_capture(396082, method='printwindow')
        end_t = time.time() - stat_t
        print(end_t)
        if screenshot is None:
            print("PrintWindow方法失败，尝试DWM方法...")
            # 尝试使用DWM方法
            screenshot = background_capture(hwnd, method='dwm')

        if screenshot is not None:
            cv2.imshow("后台截图", screenshot)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            cv2.imwrite("vm_background_screenshot.png", screenshot)
            print("截图已保存为 vm_background_screenshot.png")
        else:
            print("所有后台截图方法均失败")
    else:
        print("未找到VMware窗口")
