import math

class Point:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
    
    def __str__(self):
        return f"Point({self.x}, {self.y})"
    
    def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        return self.x == other.x and self.y == other.y
    
    def distance_to(self, other):
        """计算到另一个点的距离"""
        if not isinstance(other, Point):
            raise TypeError("Can only calculate distance to another Point")
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
    
    def add(self, dx, dy):
        """添加偏移量"""
        return Point(self.x + dx, self.y + dy)
    
    def to_tuple(self):
        """转换为元组格式"""
        return (self.x, self.y)

# 创建默认实例供全局使用
point = Point()