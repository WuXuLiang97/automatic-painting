import time

import cv2
from rapidocr_onnxruntime import RapidOCR

from core import capture
from core.get_hwnd import hwnd

engine = RapidOCR()


def recognize_text(x1, y1, x2, y2, img_numpy=None):
    """

    :param x1:
    :param y1:
    :param x2:
    :param y2:
    :return: str
    """
    det = None
    if img_numpy is not None:
        image_bgr = img_numpy
    else:
        image_bgr = capture.Capture(hwnd, 0, 0, 1067, 600)
    image_bgr = image_bgr[y1:y2, x1:x2]
    # 将BGR图像转换为RGB图像
    # _image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    _image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    result, elapse = engine(_image_rgb)
    if result:
        det = result[0][1]
        print(f"ocr识别结果为：{det}")

    return det


if __name__ == "__main__":
    import re

    results = recognize_text(433, 512, 485, 527)
    match = int(re.search(r'\d+', results).group(0))
    print(match)
    # try:
    #     # 初始化PaddleOCR包装类
    #     # ocr_wrapper = PaddleOCRWrapper(model_dir=r'D:\dnf-ai-master-fengbao\ocr\ch_PP-OCRv4_rec_infer', cls_model_dir=r"D:\dnf-ai-master-fengbao\ocr\ch_ppocr_mobile_v2.0_cls_infer")
    #     st = time.time()
    #     # # 将BGR图像转换为RGB图像
    #     # image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    #     # cv2.imshow('123', image_bgr)
    #     # cv2.waitKey(0)
    #     # cv2.destroyAllWindows()
    #     # 对图片进行文字识别
    #
    #
    #     #
    #     # time.sleep(3)
    #     # results = recognize_text(933, 690, 1033, 709)
    #     # pl_int = re.search(r'(\d+)/', results).group(1)
    #     # if pl_int:
    #     #     pl_int = int(pl_int)
    #     #     print("当前疲劳值：", pl_int)
    #     # else:
    #     #     print("ocr疲劳没有找到匹配项")
    #     # print(f"耗时：{time.time() - st}秒")
    #     # # 提示用户按任意键后回车退出
    #     # input("请按任意键后回车退出...")
    #     # print("程序已退出。")
    #
    # except Exception as e:
    #     print(e)
