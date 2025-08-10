import cv2


class OcrUtil:
    def __init__(self):
        self.ppocr = None
        self.load_model_status = False

    def load_model(self):
        from paddleocr import PaddleOCR
        self.ppocr = PaddleOCR(use_angle_cls=False, lang="ch", rec_model_dir="res/ocr/rec/ch_PP-OCRv4_rec_infer", cls_model_dir="res/ocr/rec/ch_ppocr_mobile_v2.0_cls_infer")
        self.load_model_status = True

    def get_load_model_status(self):
        return self.load_model_status

    def ocr(self, image):
        result = self.ppocr.ocr(image, cls=False, det=False)
        for idx in range(len(result)):
            res = result[idx]
            for line in res:
                return line[0]

    def ocr_by_rect(self, image, x1, y1, x2, y2):
        ocr_image = image[y1:y2, x1:x2]
        return self.ocr(ocr_image)

    def find_text(self, image, text, trait_pos=None):
        if trait_pos is not None:
            image = image[trait_pos[1]:trait_pos[3], trait_pos[0]:trait_pos[2]]
        ocr_text = self.ocr(image)
        if ocr_text is None or len(ocr_text) == 0:
            return False
        char_list = list(text)
        for char in char_list:
            if char in ocr_text:
                return True
        return False


ocr_util = OcrUtil()
