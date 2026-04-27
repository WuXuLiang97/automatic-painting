# from paddleocr import PaddleOCR, draw_ocr
from paddleocr import PaddleOCR, draw_ocr
from core import capture
import time
import cv2
import os
from core.get_hwnd import hwnd
import sys
from os import path

try:
    # 检查是否运行在打包后的可执行文件中
    if getattr(sys, 'frozen', False):
        # 如果运行在打包后的可执行文件中，使用 sys._MEIPASS
        root_path = sys._MEIPASS
    else:
        # 如果直接运行脚本，使用脚本的当前目录
        root_path = path.dirname(__file__)
except Exception as e:
    # 捕捉其他所有类型的异常
    print(f"发生了一个错误: {e}")


class PaddleOCRWrapper:
    def __init__(self, model_dir=None, cls_model_dir=None, use_angle_cls=False, lang='ch'):
        """
        初始化PaddleOCR包装类

        Args:
            model_dir (str, optional): 模型目录路径. 如果为None，则使用默认模型. 默认为None.
            cls_model_dir (str, optional): 方向分类模型目录路径. 如果为None，则不使用方向分类模型. 默认为None.
            use_angle_cls (bool, optional): 是否使用方向分类器. 默认为False.
            lang (str, optional): 使用的语言. 默认为'ch'（中文）.
        """
        print("OCR模型加载中")
        self.padd_ocr = PaddleOCR(use_angle_cls=use_angle_cls, lang=lang, model_dir=model_dir, cls_model_dir=cls_model_dir)
        print("OCR模型加载完毕")

    def recognize_text(self, x1, y1, x2, y2):
        """

        :param x1:
        :param y1:
        :param x2:
        :param y2:
        :return: str
        """
        # screenshot_np = screenshot_util.get_game_screenshot()
        # image_bgr = screenshot_np[y1:y2, x1, x2]
        image_bgr = capture.Capture(hwnd, x1, y1, x2, y2)
        # 将BGR图像转换为RGB图像
        _image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        det = None
        result = self.padd_ocr.ocr(_image_rgb, cls=True)  # 通常应该启用cls以获取更好的结果
        for idx in range(len(result)):
            res = result[idx]
            for line in res:
                det = line[1]
        return det

    # 假设你已经导入了numpy
    def draw_result(self, image_path, result, font_path='./simfang.ttf'):
        """
        在图片上绘制识别结果

        Args:
            image_path (str): 原始图片路径
            result (list): 识别结果列表
            font_path (str, optional): 字体文件路径. 默认为'./simfang.ttf'.

        Returns:
            PIL.Image: 绘制了识别结果的图片对象
        """
        image = draw_ocr(image_path, result, font_path=font_path)
        return image


# 拼接文件路径
model_dir_path = os.path.join(root_path, "ocr", 'ch_PP-OCRv4_rec_infer')
# 拼接文件路径
cls_model_dir_path = os.path.join(root_path, "ocr", 'ch_ppocr_mobile_v2.0_cls_infer')
# 实例化
ocr_wrapper = PaddleOCRWrapper(model_dir=model_dir_path, cls_model_dir=cls_model_dir_path)
if __name__ == "__main__":
    try:
        # 初始化PaddleOCR包装类
        # ocr_wrapper = PaddleOCRWrapper(model_dir=r'D:\dnf-ai-master-fengbao\ocr\ch_PP-OCRv4_rec_infer', cls_model_dir=r"D:\dnf-ai-master-fengbao\ocr\ch_ppocr_mobile_v2.0_cls_infer")
        st = time.time()
        # # 将BGR图像转换为RGB图像
        # image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        # cv2.imshow('123', image_bgr)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        # 对图片进行文字识别
        import re

        results = ocr_wrapper.recognize_text(433, 512, 485, 527)
        match = int(re.search(r'\d+', results[0]).group(0))
        if match:
            plain_move_speed = float(match) / 100
            print(match)
        else:
            print("没有识别到移速")
        # pl = (str(results).split("/")[0]
        #       .replace("疲", "")
        #       .replace("劳", "")
        #       .replace("值", "")
        #       .replace("：", ""))
        # pl_int = int(pl)
        # print("当前疲劳值：", pl)
        print(f"耗时：{time.time() - st}秒")
        # 提示用户按任意键后回车退出
        input("请按任意键后回车退出...")
        print("程序已退出。")

    except Exception as e:
        print(e)
