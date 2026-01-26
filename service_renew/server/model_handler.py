import os
import numpy as np
from paddleocr import PaddleOCR
from yolo.yolo_main import YoloV8
from root_dir import root_path

# 模型路径
DET_MODEL_DIR = os.path.join(root_path, "PP-OCRv5_mobile_det")
REC_MODEL_DIR = os.path.join(root_path, "PP-OCRv5_mobile_rec")
MODEL_WARMUP = True


class ModelHandler:
    """负责初始化和处理 YOLO 和 OCR 模型的类"""

    def __init__(self, use_yolo_gpu: bool = True):
        # 传入 use_yolo_gpu 控制 YOLO 是否用 GPU
        self.yolo = YoloV8(use_gpu=use_yolo_gpu)
        self.yolo.loadModel()

        self.ocr_engine = PaddleOCR(
            text_detection_model_dir=DET_MODEL_DIR,
            text_recognition_model_dir=REC_MODEL_DIR,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            return_word_box=False,
            text_rec_score_thresh=0.85,
            use_gpu=False,  # 强制 OCR 仅使用 CPU
        )

        if MODEL_WARMUP:
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            self.yolo.detect(dummy)
            self.ocr_engine.predict(dummy)

    def process_yolo(self, image):
        return self.yolo.detect(image)

    def process_ocr(self, image):
        return self.ocr_engine.predict(image)[0]["rec_texts"]