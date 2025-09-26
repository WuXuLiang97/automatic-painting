import math
from utils.point import Point

class CoordinateUtil:
    def __init__(self):
        """初始化坐标工具类"""
        pass
    
    def distance(self, point1, point2):
        """计算两点之间的距离"""
        if isinstance(point1, Point) and isinstance(point2, Point):
            return point1.distance_to(point2)
        elif isinstance(point1, tuple) and isinstance(point2, tuple):
            return math.sqrt((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2)
        else:
            raise TypeError("Points must be Point objects or tuples")
    
    def midpoint(self, point1, point2):
        """计算两点之间的中点"""
        if isinstance(point1, Point) and isinstance(point2, Point):
            return Point((point1.x + point2.x) / 2, (point1.y + point2.y) / 2)
        elif isinstance(point1, tuple) and isinstance(point2, tuple):
            return ((point1[0] + point2[0]) / 2, (point1[1] + point2[1]) / 2)
        else:
            raise TypeError("Points must be Point objects or tuples")
    
    def normalize(self, point):
        """将点坐标归一化"""
        if isinstance(point, Point):
            magnitude = math.sqrt(point.x ** 2 + point.y ** 2)
            if magnitude > 0:
                return Point(point.x / magnitude, point.y / magnitude)
            return Point(0, 0)
        elif isinstance(point, tuple):
            magnitude = math.sqrt(point[0] ** 2 + point[1] ** 2)
            if magnitude > 0:
                return (point[0] / magnitude, point[1] / magnitude)
            return (0, 0)
        else:
            raise TypeError("Point must be Point object or tuple")
    
    def rotate(self, point, angle):
        """将点绕原点旋转指定角度（弧度）"""
        if isinstance(point, Point):
            x = point.x * math.cos(angle) - point.y * math.sin(angle)
            y = point.x * math.sin(angle) + point.y * math.cos(angle)
            return Point(x, y)
        elif isinstance(point, tuple):
            x = point[0] * math.cos(angle) - point[1] * math.sin(angle)
            y = point[0] * math.sin(angle) + point[1] * math.cos(angle)
            return (x, y)
        else:
            raise TypeError("Point must be Point object or tuple")
    
    def is_point_in_rectangle(self, point, rect_top_left, rect_bottom_right):
        """检查点是否在矩形内"""
        if isinstance(point, Point):
            x, y = point.x, point.y
        elif isinstance(point, tuple):
            x, y = point
        else:
            raise TypeError("Point must be Point object or tuple")
        
        if isinstance(rect_top_left, Point) and isinstance(rect_bottom_right, Point):
            return (rect_top_left.x <= x <= rect_bottom_right.x and 
                    rect_top_left.y <= y <= rect_bottom_right.y)
        elif isinstance(rect_top_left, tuple) and isinstance(rect_bottom_right, tuple):
            return (rect_top_left[0] <= x <= rect_bottom_right[0] and 
                    rect_top_left[1] <= y <= rect_bottom_right[1])
        else:
            raise TypeError("Rectangle corners must be Point objects or tuples")
    
    def get_relative_position(self, absolute_pos, origin_pos):
        """获取相对于原点的坐标"""
        if isinstance(absolute_pos, Point) and isinstance(origin_pos, Point):
            return Point(absolute_pos.x - origin_pos.x, absolute_pos.y - origin_pos.y)
        elif isinstance(absolute_pos, tuple) and isinstance(origin_pos, tuple):
            return (absolute_pos[0] - origin_pos[0], absolute_pos[1] - origin_pos[1])
        else:
            raise TypeError("Positions must be Point objects or tuples")

# 创建默认实例供全局使用
coordinate_util = CoordinateUtil()