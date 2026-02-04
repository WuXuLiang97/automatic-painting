import ctypes
import random
import time
import cv2
import numpy as np
import pywintypes
import win32api
import win32con
import win32gui
from core import capture
from utils.logging_setup import logger


class ScreenshotUtil:
    def __init__(self):
        self.window_hwnd = win32gui.GetDesktopWindow()
        self.game_hwnd = None
        self.game_x = 0
        self.game_y = 0
        self.screen_width = win32api.GetSystemMetrics(0)
        self.screen_height = win32api.GetSystemMetrics(1)
        self.black_image_rect = (0, 0, 300, 300)
        self.region = {}
        # self.monitor = mss()
        self.camera = None
        self.mode = 1
        self.VNC = None

    def init_game_hwnd(self, mode=1):
        self.mode = mode
        if self.game_hwnd is not None:
            return
        if self.VNC is not None:
            return
        hwnd_child_list = []
        win32gui.EnumChildWindows(self.window_hwnd, lambda hwnd, param: param.append(hwnd), hwnd_child_list)

        for h in hwnd_child_list:
            if win32gui.GetWindowText(h) == "地下城与勇士：创新世纪":
                self.game_hwnd = h
                rect = win32gui.GetWindowRect(h)
                self.game_x = rect[0]
                self.game_y = rect[1]
                self.region = {'top': self.game_y, 'left': self.game_x, 'width': self.game_y + 1067,
                               'height': self.game_x + 600}
        if self.game_hwnd is None:
            raise Exception("游戏未启动")
        if self.mode == 3:
            self.region = [self.game_x, self.game_y, self.game_x + 1067, self.game_y + 600]

    def activate_window_by_handle(self):
        """如果激活成功，已随机延迟10~20毫秒"""
        # 确保handle是整数类型
        if not isinstance(self.game_hwnd, int):
            # my_logger.info(f"窗口句柄 {handle} 必须是整数类型")

            return False

            # 检查窗口句柄是否有效
        if not win32gui.IsWindow(self.game_hwnd):
            # my_logger.info(f"窗口句柄 {handle} 无效或窗口已关闭")

            return False

        try:
            # 尝试将窗口设置为最前端并激活它
            win32gui.SetForegroundWindow(self.game_hwnd)
            win32gui.SendMessage(self.game_hwnd, win32con.WM_SETFOCUS, 0, 0)

            time.sleep(random.uniform(0.01, 0.02))
            return True
        except pywintypes.error as e:
            # 如果设置前台窗口失败，并且错误码是ERROR_ACCESS_DENIED，则尝试获取设置前台窗口的权限
            if e.winerror == 5:  # ERROR_ACCESS_DENIED
                current_process_id = ctypes.windll.kernel32.GetCurrentProcessId()
                ctypes.windll.user32.AllowSetForegroundWindow(current_process_id)
                try:
                    # 再次尝试设置窗口为最前端并激活它
                    win32gui.SetForegroundWindow(self.game_hwnd)
                    win32gui.SendMessage(self.game_hwnd, win32con.WM_SETFOCUS, 0, 0)
                    time.sleep(random.uniform(0.01, 0.02))
                    return True
                except pywintypes.error as e:
                    logger.info(f"激活窗口时出错: {e}")
            else:
                logger.info(f"激活窗口时发生未知错误: {e}")
            return False

    def get_game_screenshot(self, max_retry=30, timeout=10):

        start_time = time.time()
        retry_count = 0

        while retry_count < max_retry:
            try:
                # 检查是否超时
                if time.time() - start_time > timeout:
                    logger.info(f"截图超时（{timeout}秒），停止继续重试")
                    break

                if self.mode == 1:
                    croppedImage = self.screenshot_bgr()
                else:
                    raise Exception("mode参数错误")

                # 提取黑色矩形区域
                blackImage = croppedImage[225:377, 465:674].copy()
                # 转换为灰度图像
                blackImageGray = cv2.cvtColor(blackImage, cv2.COLOR_BGR2GRAY)

                # 计算黑色像素比例
                countBelow20 = np.count_nonzero(blackImageGray < 20)
                totalPixels = blackImageGray.shape[0] * blackImageGray.shape[1]
                ratioBelow20 = countBelow20 / totalPixels

                if ratioBelow20 > 0.97:
                    logger.info(f"截图模块--过图中 (尝试 {retry_count + 1}/{max_retry}) ratioBelow20:{ratioBelow20:.4f}")
                    retry_count += 1
                    time.sleep(0.2)  # 添加短暂延迟减少CPU占用
                    continue
                else:
                    return croppedImage

            except Exception as e:
                logger.info(f"截图错误: {e} (尝试 {retry_count + 1}/{max_retry})")
                retry_count += 1
                time.sleep(0.2)  # 错误时稍长延迟

        # 如果多次重试仍失败或超时，则返回一张空白图像，避免调用方直接崩溃
        logger.warning(f"截图最终失败（重试 {retry_count} 次，超时时间 {timeout} 秒），返回空白图像作为兜底")
        # 默认分辨率为 1067x600，BGR 三通道
        return np.zeros((600, 1067, 3), dtype=np.uint8)

    # def screenshot_by_win32(self):
    #     # 获取上下文句柄
    #     h_wnd_dc = win32gui.GetWindowDC(self.window_hwnd)
    #     # 创建设备描述表
    #     mfc_dc = win32ui.CreateDCFromHandle(h_wnd_dc)
    #     # 内存设备描述表
    #     save_dc = mfc_dc.CreateCompatibleDC()
    #     # 创建位图对象
    #     save_bit_map = win32ui.CreateBitmap()
    #     # 分配存储空间
    #     save_bit_map.CreateCompatibleBitmap(mfc_dc, self.screen_width, self.screen_height)
    #     # 将位图对象选入到内存设备描述表
    #     save_dc.SelectObject(save_bit_map)
    #     save_dc.BitBlt((0, 0), (self.screen_width, self.screen_height), mfc_dc, (0, 0), win32con.SRCCOPY)
    #
    #     # 获取位图信息
    #     signed_ints_array = save_bit_map.GetBitmapBits(True)
    #     im_opencv = np.frombuffer(signed_ints_array, dtype='uint8')
    #     im_opencv.shape = (self.screen_height, self.screen_width, 4)
    #
    #     # 内存释放
    #     win32gui.DeleteObject(save_bit_map.GetHandle())
    #     save_dc.DeleteDC()
    #     mfc_dc.DeleteDC()
    #     win32gui.ReleaseDC(self.game_hwnd, h_wnd_dc)
    #     # 裁剪截图
    #     croppedImage = im_opencv[self.game_y:self.game_y + 720, self.game_x:self.game_x + 1280]
    #     # # 转换颜色空间为RGB
    #     croppedImage = cv2.cvtColor(croppedImage, cv2.COLOR_BGRA2BGR)
    #     return croppedImage

    # def screenshot_by_mss(self):
    #     while True:
    #         try:
    #             screenshot = self.monitor.grab(self.region)
    #             img = np.array(screenshot)
    #             img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    #             return img
    #         except Exception as e:
    #             logger.info(e)
    #             continue

    # def screenshot_by_dx(self):
    #     while True:
    #         try:
    #             screenshot = self.camera._grab(self.region)
    #             if screenshot is None:
    #                 continue
    #             img = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
    #             return img
    #         except Exception as e:
    #             logger.info('screenshot_by_dx', e)
    #             raise e

    def screenshot_bgr(self):
        while True:
            try:
                # logger.info(self.game_hwnd, 0, 0, 1280,  720)
                if self.VNC is not None:
                    logger.info("VNC截图")
                    screenshot = self.VNC.capture()
                else:
                    screenshot = capture.Capture(self.game_hwnd, 0, 0, 1067, 600)
                    screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
                # screenshot = self.camera._grab(self.region)
                if screenshot is None:
                    continue

                return screenshot
            except Exception as e:
                logger.info('screenshot_by_dx', e)
                raise e

    def screenshot_rgb(self):
        while True:
            try:
                # logger.info(self.game_hwnd, 0, 0, 1280,  720)
                screenshot = capture.Capture(self.game_hwnd, 0, 0, 1067, 600)
                # screenshot = self.camera._grab(self.region)
                if screenshot is None:
                    continue
                img = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
                return img
            except Exception as e:
                raise e
                logger.info('screenshot_by_dx', e)
                continue

    def top_window(self):
        """将窗口设置为最顶层
        :return:
        """
        try:
            win32gui.SetWindowPos(self.game_hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        except Exception as e:
            logger.info("窗口取消置顶异常：{}".format(e))

    def cancel_window_topping(self):
        """取消窗口置顶
        :return:
        """
        try:
            # 将窗口从最顶层移回普通状态
            win32gui.SetWindowPos(self.game_hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        except Exception as e:
            logger.info("窗口取消置顶异常：{}".format(e))


screenshot_util = ScreenshotUtil()

if __name__ == '__main__':
    st = time.time()
    # screenshot_util.init_game_hwnd()
    # game_image = screenshot_util.get_game_screenshot()
    # logger.info("耗时：{}秒".format(time.time() - st))
    # y = YoloV8()
    # y.loadModel()
    # while True:
    #     game_image = screenshot_util.get_game_screenshot()
    #     y.detect(game_image)
    #     logger.info("================================================================================================")
    # # cv2.imshow('windows', game_image)
    # # if cv2.waitKey(0) & 0xFF == ord('q'):
    # #     cv2.destroyWindow('windows')
