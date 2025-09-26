# -*- coding: utf-8 -*-
"""
OCR识别模块
负责图像文字识别功能
"""
import cv2
import numpy as np
from utils.logging_setup import logger

class OCRModule:
    def __init__(self):
        """初始化OCR模块"""
        self.initialized = False
        self.ocr_engine = None
        self._init_ocr_engine()
    
    def _init_ocr_engine(self):
        """初始化OCR引擎"""
        try:
            # 尝试导入paddleocr库
            try:
                from paddleocr import PaddleOCR
                # 初始化PaddleOCR引擎（不使用方向检测和分类）
                self.ocr_engine = PaddleOCR(use_angle_cls=False, lang='ch', show_log=False)
                self.initialized = True
                logger.info("PaddleOCR引擎初始化成功")
            except ImportError:
                logger.warning("未安装paddleocr库，使用简易OCR模式")
                self.initialized = True  # 即使没有paddleocr也标记为初始化成功，使用备用方案
        except Exception as e:
            logger.error(f"初始化OCR引擎时发生异常: {str(e)}")
            self.initialized = False
    
    def recognize_text(self, image, region=None):
        """
        识别图像中的文本
        :param image: 输入图像（BGR格式）
        :param region: 可选的感兴趣区域 (x, y, w, h)
        :return: 识别到的文本字符串
        """
        try:
            if not self.initialized:
                logger.warning("OCR引擎未初始化，无法进行文本识别")
                return ""
            
            # 如果指定了区域，裁剪图像
            if region:
                x, y, w, h = region
                # 确保区域在图像范围内
                h, w_img = image.shape[:2]
                x = max(0, min(x, w_img - 1))
                y = max(0, min(y, h - 1))
                w = min(w, w_img - x)
                h = min(h, h - y)
                crop_img = image[y:y+h, x:x+w]
            else:
                crop_img = image.copy()
            
            # 使用PaddleOCR进行识别（如果可用）
            if hasattr(self, 'ocr_engine') and self.ocr_engine is not None:
                result = self.ocr_engine.ocr(crop_img, det=True, rec=True, cls=False)
                
                # 提取文本
                full_text = []
                if result and isinstance(result, list) and len(result) > 0:
                    for line_info in result[0]:
                        if line_info and len(line_info) > 1:
                            full_text.append(line_info[1][0])  # line_info[1][0]是识别到的文本
                
                return ' '.join(full_text)
            else:
                # 简易OCR模式（基于颜色阈值）
                # 这里只是一个示例实现，实际应用中可能需要更复杂的处理
                gray = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
                _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
                
                # 这里返回空字符串，实际应用中可以根据需要实现简单的字符识别
                logger.warning("使用简易OCR模式，无法提取实际文本")
                return ""
        except Exception as e:
            logger.error(f"OCR文本识别时发生异常: {str(e)}")
            return ""
    
    def detect_text_region(self, image):
        """
        检测图像中的文本区域
        :param image: 输入图像
        :return: 文本区域列表 [(x, y, w, h), ...]
        """
        try:
            if not self.initialized:
                logger.warning("OCR引擎未初始化，无法进行文本区域检测")
                return []
            
            # 使用PaddleOCR进行文本区域检测
            if hasattr(self, 'ocr_engine') and self.ocr_engine is not None:
                result = self.ocr_engine.ocr(image, det=True, rec=False, cls=False)
                
                # 提取文本区域
                regions = []
                if result and isinstance(result, list) and len(result) > 0:
                    for line_info in result[0]:
                        if line_info and len(line_info) > 0:
                            # line_info[0]是文本框的四个角点坐标
                            pts = np.array(line_info[0], dtype=int)
                            x, y = np.min(pts, axis=0)[:2]
                            w, h = np.max(pts, axis=0)[:2] - [x, y]
                            regions.append((x, y, w, h))
                
                return regions
            else:
                # 简易模式：返回空列表
                return []
        except Exception as e:
            logger.error(f"文本区域检测时发生异常: {str(e)}")
            return []

# 提供一个默认的实例
ocr_module = OCRModule()