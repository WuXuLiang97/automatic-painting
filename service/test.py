
import os
import cv2
from paddleocr import PaddleOCR  # 百度PaddleOCR库（文字识别）
from root_dir import root_path  # 项目根路径配置

# 模型路径（OCR的检测/识别模型）
det_model_dir = os.path.join(
    root_path, "PP-OCRv5_server_det"
)  # OCR检测模型（定位文字区域）
rec_model_dir = os.path.join(
    root_path, "PP-OCRv5_server_rec"
)  # OCR识别模型（识别文字内容）

print(rec_model_dir)

# 初始化OCR模型（文字识别）
ocr_engine = PaddleOCR(
    text_detection_model_dir=det_model_dir,  # 文字检测模型路径
    text_recognition_model_dir=rec_model_dir,  # 文字识别模型路径
    use_doc_orientation_classify=False,  # 不使用方向分类
    use_doc_unwarping=False,  # 不使用文档矫正
    use_textline_orientation=False,  # 不使用文字方向分类
    return_word_box=False,  # 不返回单字位置
    text_rec_score_thresh=0.85,  # 文字检测置信度阈值
    device="GPU",  # 是否使用GPU
)

image = cv2.imread("ocr_temp.png")  # 读取测试图像

rec_texts = ocr_engine.predict(image)[0]["rec_texts"]
joined_text = "".join(rec_texts)  # 拼接所有文字为字符串
print(joined_text)  # 打印识别结果