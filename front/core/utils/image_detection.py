# -*- coding: utf-8 -*-
"""
图像检测模块
负责图像相似性比较、模板匹配等功能
"""
import cv2
import numpy as np
from utils.logging_setup import logger

class ImageDetection:
    def __init__(self):
        """初始化图像检测模块"""
        self.template_cache = {}
    
    def get_similarity(self, img1, img2):
        """计算两张图像的相似度"""
        try:
            # 确保图像大小相同
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
            # 转换为灰度图
            if len(img1.shape) == 3:
                gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            else:
                gray1 = img1
            
            if len(img2.shape) == 3:
                gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            else:
                gray2 = img2
            
            # 使用结构相似性指数(SSIM)计算相似度
            from skimage.metrics import structural_similarity as ssim
            similarity = ssim(gray1, gray2)
            return similarity
        except Exception as e:
            logger.error(f"计算图像相似度时发生异常: {str(e)}")
            return 0.0
    
    def template_match(self, source_img, template_img, threshold=0.8):
        """模板匹配"""
        try:
            # 转换为灰度图
            if len(source_img.shape) == 3:
                source_gray = cv2.cvtColor(source_img, cv2.COLOR_BGR2GRAY)
            else:
                source_gray = source_img
            
            if len(template_img.shape) == 3:
                template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
            else:
                template_gray = template_img
            
            # 进行模板匹配
            result = cv2.matchTemplate(source_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            
            # 获取匹配结果
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                return {
                    'found': True,
                    'location': max_loc,
                    'similarity': max_val,
                    'width': template_gray.shape[1],
                    'height': template_gray.shape[0]
                }
            else:
                return {'found': False}
        except Exception as e:
            logger.error(f"模板匹配时发生异常: {str(e)}")
            return {'found': False}
    
    def load_template(self, template_path):
        """加载模板图像到缓存"""
        try:
            if template_path not in self.template_cache:
                img = cv2.imread(template_path)
                if img is not None:
                    self.template_cache[template_path] = img
                    return img
                else:
                    logger.warning(f"无法加载模板图像: {template_path}")
                    return None
            return self.template_cache[template_path]
        except Exception as e:
            logger.error(f"加载模板图像时发生异常: {str(e)}")
            return None

# 提供一个默认的实例
image_detection = ImageDetection()

# 提供一个独立的get_similarity函数供外部直接调用
def get_similarity(img1, img2):
    return image_detection.get_similarity(img1, img2)