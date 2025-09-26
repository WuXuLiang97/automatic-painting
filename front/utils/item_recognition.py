import cv2
import numpy as np
from utils.logging_setup import logger

class ItemRecognition:
    def __init__(self):
        """初始化物品识别类"""
        self.item_templates = {}
        self.load_item_templates()
        
    def load_item_templates(self):
        """加载物品模板图片"""
        # 在实际应用中，这里应该从配置文件或数据库加载物品模板
        # 这里只是简单示例
        logger.info("加载物品模板")
        
    def recognize_item_from_image(self, image, roi=None):
        """从图像中识别物品
        Args:
            image: 输入图像
            roi: 感兴趣区域 (x, y, w, h)
        Returns:
            list: 识别到的物品列表 [{'name': 物品名, 'confidence': 置信度, 'position': (x, y)}]
        """
        try:
            # 如果指定了ROI，裁剪图像
            if roi:
                x, y, w, h = roi
                image = image[y:y+h, x:x+w]
                
            # 简单的物品识别逻辑
            # 在实际应用中，这里应该使用更复杂的识别算法，如模板匹配、深度学习等
            items = []
            
            # 这里返回空列表，在实际应用中应该返回真实识别结果
            return items
        except Exception as e:
            logger.error(f"物品识别异常: {str(e)}")
            return []
    
    def classify_item(self, item_features):
        """根据物品特征分类物品
        Args:
            item_features: 物品特征
        Returns:
            str: 物品类型
        """
        # 简单的物品分类逻辑
        # 在实际应用中，这里应该使用更复杂的分类算法
        return "普通物品"
    
    def get_item_value(self, item_name):
        """获取物品价值
        Args:
            item_name: 物品名称
        Returns:
            float: 物品价值
        """
        # 简单的物品价值评估逻辑
        # 在实际应用中，这里应该从配置文件或数据库获取物品价值
        value_map = {
            "金绿柱石": 100, 
            "深渊票": 50, 
            "史诗装备": 1000, 
            "传说装备": 500,
            "稀有材料": 30,
            "金币袋": 20,
            "邀请函": 40,
            "挑战书": 45,
            "精炼的时空石": 60,
            "红玉髓": 5,
            "强烈的气息": 25
        }
        
        return value_map.get(item_name, 1)
    
    def filter_valuable_items(self, items, min_value=10):
        """过滤有价值的物品
        Args:
            items: 物品列表
            min_value: 最小价值阈值
        Returns:
            list: 过滤后的物品列表
        """
        valuable_items = []
        for item in items:
            item_value = self.get_item_value(item.get('name', ''))
            if item_value >= min_value:
                item_copy = item.copy()
                item_copy['value'] = item_value
                valuable_items.append(item_copy)
        
        # 按价值排序
        valuable_items.sort(key=lambda x: x.get('value', 0), reverse=True)
        
        return valuable_items
    
    def match_item_template(self, image, template_name):
        """使用模板匹配识别特定物品
        Args:
            image: 输入图像
            template_name: 模板名称
        Returns:
            dict: 匹配结果 {'found': 是否找到, 'position': 位置, 'confidence': 置信度}
        """
        try:
            # 检查是否加载了该模板
            if template_name not in self.item_templates:
                logger.warning(f"未找到模板: {template_name}")
                return {'found': False}
            
            template = self.item_templates[template_name]
            
            # 执行模板匹配
            result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 设定阈值，判断是否匹配成功
            threshold = 0.7
            if max_val >= threshold:
                h, w = template.shape[:2]
                return {
                    'found': True,
                    'position': (max_loc[0], max_loc[1], w, h),
                    'confidence': max_val
                }
            else:
                return {'found': False}
        except Exception as e:
            logger.error(f"模板匹配异常: {str(e)}")
            return {'found': False}

# 创建默认实例供全局使用
item_recognition = ItemRecognition()