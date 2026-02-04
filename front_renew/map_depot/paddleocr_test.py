# -*- coding: utf-8 -*-
import os
import cv2
from paddleocr import PaddleOCR
from root_dir import root_path

det_model_dir = os.path.join(root_path, 'ch_PP-OCRv4_det_infer')
rec_model_dir = os.path.join(root_path, 'ch_PP-OCRv4_rec_infer')
ocr = PaddleOCR(
    lang='ch',
    det_model_dir=det_model_dir,  # 检测模型路径
    rec_model_dir=rec_model_dir,  # 识别模型路径
)  # need to run only once to load model into memory


def ocr_get_text(img_numpy):
    """
    从BGR格式图像中提取并拼接所有OCR识别结果

    该函数执行以下操作：
    1. 将输入的BGR图像转换为灰度图（增强OCR引擎兼容性）
    2. 使用预配置的OCR引擎进行文本检测与识别
    3. 拼接所有识别到的文本行，按检测顺序返回完整字符串

    参数:
        img_numpy (numpy.ndarray):
            输入图像数组，需为OpenCV标准的BGR格式（shape: [H, W, 3]）

    返回:
        str: 所有识别结果的拼接字符串。若无有效结果，返回空字符串。

    实现细节:
        - 使用灰度转换提升处理效率（COLOR_BGR2GRAY）
        - 禁用方向检测(det=False)和分类(cls=False)以提升速度
        - 按检测顺序拼接文本行（保留原始顺序）

    注意事项:
        * 不同文本行之间无额外分隔符，如需分隔可手动添加
        * 灰度转换可能影响彩色文本的识别准确率
        * 依赖外部OCR引擎的实现（需提前初始化ocr对象）
    """
    # 初始化结果容器
    full_text = []

    # 颜色空间转换
    _image_gray = cv2.cvtColor(img_numpy, cv2.COLOR_BGR2GRAY)

    # 执行OCR识别
    ocr_results = ocr.ocr(_image_gray, det=False, cls=False)
    print(ocr_results)
    # 遍历所有检测结果
    for page_results in ocr_results:
        for line_info in page_results:
            # 提取文本内容并添加到结果集
            if line_info:
                full_text.append(line_info[0])

    # 返回拼接后的完整文本
    return ''.join(full_text)


if __name__ == "__main__":
    img_path = r""
    img = cv2.imread(img_path)
    ocr_get_text(img)
