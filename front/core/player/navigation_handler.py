import time
import random
from utils.logging_setup import logger
from core import global_variable as gv
from core.utils.image_detection import ImageDetection
from utils.coordinate_util import coordinate_util
from utils.point import Point
from utils.move_info import MoveInfo

class RoomNavigationHandler:
    def __init__(self):
        """初始化导航处理器"""
        self.player = None  # 玩家引用，在PlayerThread中设置
        self.mm = None  # 鼠标管理器引用，在PlayerThread中设置
        self.send_log = None  # 日志发送函数，在PlayerThread中设置
        self.operator_module = None  # 操作模块引用，在PlayerThread中设置
        
        # 导航状态
        self.current_room_id = 0
        self.target_room_id = 0
        self.navigation_path = []
        self.is_navigating = False
        self.last_navigation_time = 0
        
        # 导航配置
        self.navigation_config = {
            "move_speed": 1.0,  # 移动速度系数
            "click_delay": 0.1,  # 点击延迟（秒）
            "pathfinding_accuracy": 0.9,  # 寻路精度
            "navigate_timeout": 30,  # 导航超时时间（秒）
        }
        
        # 图片检测
        self.image_detection = ImageDetection()
        
        # 坐标工具
        self.coordinate_util = coordinate_util
    
    def apply_config(self, config_data):
        """应用配置数据"""
        if not config_data:
            return
        
        # 更新导航配置
        if "navigation_config" in config_data:
            self.navigation_config.update(config_data["navigation_config"])
    
    def navigate_to_room(self, room_id):
        """导航到指定房间"""
        try:
            if not self.player or not self.mm or not self.operator_module:
                logger.warning("导航组件未初始化完全，无法导航")
                return False
            
            self.target_room_id = room_id
            self.is_navigating = True
            self.last_navigation_time = time.time()
            
            # 计算导航路径
            self._calculate_navigation_path()
            
            # 执行导航
            result = self._execute_navigation()
            
            self.is_navigating = False
            return result
        except Exception as e:
            logger.error(f"导航到房间{room_id}失败: {e}")
            self.is_navigating = False
            return False
    
    def _calculate_navigation_path(self):
        """计算导航路径"""
        if not self.player.room_info_map:
            logger.warning("房间信息地图未初始化")
            return
        
        # 从当前房间到目标房间的路径规划
        # 这里可以实现A*或其他寻路算法
        logger.info(f"计算从房间{self.current_room_id}到房间{self.target_room_id}的路径")
        
        # 简化的路径规划，实际项目中可能需要更复杂的算法
        self.navigation_path = [self.target_room_id]  # 假设直接移动到目标房间
    
    def _execute_navigation(self):
        """执行导航"""
        start_time = time.time()
        
        while self.is_navigating and time.time() - start_time < self.navigation_config["navigate_timeout"]:
            try:
                # 获取当前房间ID
                self.current_room_id = self._get_current_room_id()
                
                # 检查是否到达目标房间
                if self.current_room_id == self.target_room_id:
                    logger.info(f"已到达目标房间{self.target_room_id}")
                    return True
                
                # 执行移动操作
                self._move_to_next_room()
                
                # 检查导航超时
                if time.time() - self.last_navigation_time > self.navigation_config["navigate_timeout"]:
                    logger.warning("导航超时")
                    return False
                
                time.sleep(0.1)  # 导航循环间隔
            except Exception as e:
                logger.error(f"导航执行过程中出错: {e}")
                time.sleep(0.5)
        
        logger.warning("导航失败")
        return False
    
    def _get_current_room_id(self):
        """获取当前房间ID"""
        # 实际项目中，这里应该通过图像处理或其他方式获取当前房间ID
        # 这里简单返回玩家的当前房间ID
        return self.player.player_room_id if self.player else 0
    
    def _move_to_next_room(self):
        """移动到下一个房间"""
        if not self.navigation_path:
            logger.warning("导航路径为空")
            return
        
        next_room_id = self.navigation_path[0]
        logger.info(f"移动到房间{next_room_id}")
        
        # 实际项目中，这里应该执行具体的移动操作
        # 例如，根据房间ID确定移动方向，然后发送键盘指令
        # 这里简化处理，假设通过操作模块移动到下一个房间
        if self.operator_module:
            # 这里可以添加具体的移动逻辑
            pass
    
    def move_to_monster(self):
        """向最近的怪物移动"""
        logger.info("开始向怪物移动")
        monster_direction = "right"
        
        if not self.player or self.player.player_pos.x is None or not self.player.monsters:
            return False
        
        # 清除障碍
        if hasattr(self.player, 'clearingobstacles'):
            self.player.clearingobstacles()
        
        # 计算每个怪物与玩家的距离，找到最近的怪物
        min_distance = float('inf')
        nearest_monster = None
        
        for monster in self.player.monsters:
            distance = (monster[0] - self.player.player_pos.x) ** 2 + (monster[1] - self.player.player_pos.y) ** 2
            if distance < min_distance:
                min_distance = distance
                nearest_monster = monster
        
        if not nearest_monster:
            return False
        
        # 按y坐标排序的怪物列表
        sorted_monsters_by_y = sorted(self.player.monsters, key=lambda x: x[1])
        n = len(sorted_monsters_by_y)
        median_y = sorted_monsters_by_y[n // 2][1] if n % 2 == 1 else \
                  (sorted_monsters_by_y[n // 2 - 1][1] + sorted_monsters_by_y[n // 2][1]) / 2
        
        # 使用最近的怪物作为目标点
        monster_point = Point(nearest_monster[0], median_y)
        
        if hasattr(self.player, 'is_first_attack_monster') and self.player.is_first_attack_monster:
            # 第一次攻击的位置调整逻辑
            if monster_point.x >= self.player.player_pos.x and monster_point.x - 160 > 0:
                monster_point.x = monster_point.x - 160
                monster_direction = "right"
            elif monster_point.x <= self.player.player_pos.x and monster_point.x + 160 < 1067:
                monster_point.x = monster_point.x + 160
                monster_direction = "left"
            elif monster_point.x < self.player.player_pos.x < (monster_point.x + 160):
                if self.player.player_pos.x - monster_point.x < (monster_point.x + 160) - self.player.player_pos.x:
                    monster_point.x = monster_point.x - 160
                    monster_direction = "right"
                else:
                    monster_point.x = monster_point.x + 160
                    monster_direction = "left"
        
        return True
    
    def compute_move_info(self, player_pos, target_pos, diff_x, diff_y):
        """计算移动信息"""
        # 检查无效输入
        if (player_pos.x is None or player_pos.y is None or 
            any(v <= 0 for v in [player_pos.x, player_pos.y, target_pos.x, target_pos.y])):
            return None
        
        move_info = MoveInfo("left", "up", 0, 0, False)
        # 处理X轴方向
        dx = abs(player_pos.x - target_pos.x)
        if dx > diff_x:
            delta = self.player.x_speed * 0.1 if self.player else 10
            if player_pos.x > target_pos.x and player_pos.x - target_pos.x > delta:
                target_pos.x += delta
            elif player_pos.x < target_pos.x and target_pos.x - player_pos.x > delta:
                target_pos.x -= delta
            if player_pos.x < target_pos.x:
                move_info.leftRightDirection = "right"
            if dx > 200:
                move_info.run = True
            move_info.xTime = (abs(player_pos.x - target_pos.x - diff_x) / self.player.x_speed) if self.player and self.player.x_speed > 0 else 0
        # 处理Y轴方向
        dy = abs(player_pos.y - target_pos.y)
        if dy > diff_y:
            if player_pos.y < target_pos.y:
                move_info.upDownDirection = "down"
            move_info.yTime = (abs(player_pos.y - target_pos.y - diff_y) / self.player.y_speed) if self.player and self.player.y_speed > 0 else 0
        return move_info
    
    def compute_move_info_walk(self, player_pos, target_pos, diff_x, diff_y):
        """计算行走模式下的移动信息"""
        # 检查无效输入
        if (player_pos.x is None or player_pos.y is None or 
            any(v <= 0 for v in [player_pos.x, player_pos.y, target_pos.x, target_pos.y])):
            return None
        
        move_info = MoveInfo("left", "up", 0, 0, False)
        # 处理X轴方向
        dx = abs(player_pos.x - target_pos.x)
        if dx > diff_x:
            delta = self.player.x_speed_walk * 0.1 if self.player else 5
            if player_pos.x > target_pos.x and player_pos.x - target_pos.x > delta:
                target_pos.x += delta
            elif player_pos.x < target_pos.x and target_pos.x - player_pos.x > delta:
                target_pos.x -= delta
            if player_pos.x < target_pos.x:
                move_info.leftRightDirection = "right"
            if dx > 200:
                move_info.run = True
            move_info.xTime = (abs(player_pos.x - target_pos.x - diff_x) / self.player.x_speed_walk) if self.player and self.player.x_speed_walk > 0 else 0
        # 处理Y轴方向
        dy = abs(player_pos.y - target_pos.y)
        if dy > diff_y:
            if player_pos.y < target_pos.y:
                move_info.upDownDirection = "down"
            move_info.yTime = (abs(player_pos.y - target_pos.y - diff_y) / self.player.y_speed_walk) if self.player and self.player.y_speed_walk > 0 else 0
        return move_info
    
    def _calculate_navigation_path(self, target_room_id):
        """计算导航路径"""
        try:
            # 这里应该有计算导航路径的逻辑
            # 例如基于当前地图结构、当前房间位置、目标房间位置计算最优路径
            
            # 简化版：直接设置目标房间为导航路径
            self.navigation_path = [target_room_id]
        except Exception as e:
            logger.error(f"计算导航路径异常: {str(e)}")
            self.navigation_path = []
    
    def _execute_navigation(self):
        """执行导航"""
        try:
            if not self.navigation_path:
                logger.warning("导航路径为空，无法执行导航")
                return False
            
            start_time = time.time()
            navigate_timeout = self.navigation_config["navigate_timeout"]
            
            # 遍历导航路径中的每个房间
            for room_id in self.navigation_path:
                # 检查是否超时
                if time.time() - start_time > navigate_timeout:
                    logger.warning("导航超时")
                    return False
                
                # 检查是否需要退出导航
                if not self.is_navigating or self.player.stop_flag:
                    logger.warning("导航被中断")
                    return False
                
                # 导航到房间
                if not self._navigate_to_single_room(room_id):
                    logger.warning(f"导航到房间 {room_id} 失败")
                    return False
                
            return True
        except Exception as e:
            logger.error(f"执行导航异常: {str(e)}")
            return False
    
    def _navigate_to_single_room(self, room_id):
        """导航到单个房间"""
        try:
            # 这里应该有导航到单个房间的逻辑
            # 例如找到房间入口、移动到入口、点击入口进入房间
            
            logger.info(f"导航到房间 {room_id}")
            
            # 更新导航状态
            self.target_room_id = room_id
            self.is_navigating = True
            self.last_navigation_time = time.time()
            
            # 计算导航路径
            self._calculate_navigation_path(room_id)
            
            # 执行导航
            success = self._execute_navigation()
            
            if success:
                self.current_room_id = room_id
                logger.info(f"成功导航到房间 {room_id}")
            else:
                logger.warning(f"导航到房间 {room_id} 失败")
            
            # 更新导航状态
            self.is_navigating = False
            
            return success
        except Exception as e:
            logger.error(f"导航到房间异常: {str(e)}")
            self.is_navigating = False
            return False
        #     # 模拟导航过程
        #     logger.info(f"导航到单个房间 {room_id}")
            
        #     # 等待一段时间模拟导航
        #     time.sleep(1)
            
        #     return True
        # except Exception as e:
        #     logger.error(f"导航到单个房间异常: {str(e)}")
        #     return False
    
    def move_to_position(self, x, y):
        """移动到指定位置"""
        try:
            if not self.player or not self.mm or not self.operator_module:
                logger.warning("导航组件未初始化完全，无法移动")
                return False
            
            logger.info(f"移动到位置 ({x}, {y})")
            
            # 获取当前位置
            current_x, current_y = self._get_current_position()
            
            # 计算移动路径
            move_path = self._calculate_move_path(current_x, current_y, x, y)
            
            # 执行移动
            success = self._execute_move(move_path)
            
            if success:
                logger.info(f"成功移动到位置 ({x}, {y})")
            else:
                logger.warning(f"移动到位置 ({x}, {y}) 失败")
            
            return success
        except Exception as e:
            logger.error(f"移动到位置异常: {str(e)}")
            return False
    
    def _get_current_position(self):
        """获取当前位置"""
        try:
            # 这里应该有获取当前位置的逻辑
            # 例如从游戏窗口获取玩家坐标、从内存读取等
            
            # 模拟当前位置
            return 0, 0
        except Exception as e:
            logger.error(f"获取当前位置异常: {str(e)}")
            return 0, 0
    
    def _calculate_move_path(self, start_x, start_y, end_x, end_y):
        """计算移动路径"""
        try:
            # 这里应该有计算移动路径的逻辑
            # 例如使用A*算法等寻路算法计算从起点到终点的最优路径
            
            # 简化版：直接设置终点为移动路径
            return [(end_x, end_y)]
        except Exception as e:
            logger.error(f"计算移动路径异常: {str(e)}")
            return []
    
    def _execute_move(self, move_path):
        """执行移动"""
        try:
            if not move_path:
                logger.warning("移动路径为空，无法执行移动")
                return False
            
            # 遍历移动路径中的每个点
            for point_x, point_y in move_path:
                # 检查是否需要退出移动
                if self.player.stop_flag:
                    logger.warning("移动被中断")
                    return False
                
                # 移动到点
                if not self._move_to_point(point_x, point_y):
                    logger.warning(f"移动到点 ({point_x}, {point_y}) 失败")
                    return False
                
            return True
        except Exception as e:
            logger.error(f"执行移动异常: {str(e)}")
            return False
    
    def _move_to_point(self, x, y):
        """移动到点"""
        try:
            # 这里应该有移动到点的逻辑
            # 例如控制鼠标移动、点击、使用键盘移动等
            
            # 模拟移动过程
            logger.info(f"移动到点 ({x}, {y})")
            
            # 使用鼠标管理器移动并点击
            if self.mm:
                # 移动鼠标到目标位置
                self.mm.move_to(x, y)
                
                # 点击左键
                self.mm.click(button='left')
                
                # 等待点击延迟
                time.sleep(self.navigation_config["click_delay"])
            
            return True
        except Exception as e:
            logger.error(f"移动到点异常: {str(e)}")
            return False
    
    def enter_door(self):
        """进入门"""
        try:
            if not self.player or not self.mm or not self.operator_module:
                logger.warning("导航组件未初始化完全，无法进入门")
                return False
            
            logger.info("进入门")
            
            # 检查门是否存在
            if not self._check_door_exists():
                logger.warning("门不存在")
                return False
            
            # 找到门的位置
            door_x, door_y = self._find_door_position()
            
            if door_x == 0 and door_y == 0:
                logger.warning("未找到门的位置")
                return False
            
            # 移动到门的位置
            if not self.move_to_position(door_x, door_y):
                logger.warning("移动到门的位置失败")
                return False
            
            # 点击门进入
            if not self._click_door(door_x, door_y):
                logger.warning("点击门失败")
                return False
            
            logger.info("成功进入门")
            return True
        except Exception as e:
            logger.error(f"进入门异常: {str(e)}")
            return False
    
    def _check_door_exists(self):
        """检查门是否存在"""
        try:
            # 这里应该有检查门是否存在的逻辑
            # 例如使用图像识别检测门的存在
            
            # 模拟门存在
            return True
        except Exception as e:
            logger.error(f"检查门是否存在异常: {str(e)}")
            return False
    
    def _find_door_position(self):
        """找到门的位置"""
        try:
            # 这里应该有找到门的位置的逻辑
            # 例如使用图像识别定位门的位置
            
            # 模拟门的位置
            return 500, 300
        except Exception as e:
            logger.error(f"找到门的位置异常: {str(e)}")
            return 0, 0
    
    def _click_door(self, x, y):
        """点击门"""
        try:
            # 这里应该有点击门的逻辑
            # 例如控制鼠标点击门的位置
            
            # 使用鼠标管理器点击门
            if self.mm:
                # 移动鼠标到门的位置
                self.mm.move_to(x, y)
                
                # 点击左键
                self.mm.click(button='left')
                
                # 等待点击延迟
                time.sleep(self.navigation_config["click_delay"])
            
            return True
        except Exception as e:
            logger.error(f"点击门异常: {str(e)}")
            return False
    
    def reset_navigation_state(self):
        """重置导航状态"""
        try:
            self.current_room_id = 0
            self.target_room_id = 0
            self.navigation_path = []
            self.is_navigating = False
            self.last_navigation_time = 0
        except Exception as e:
            logger.error(f"重置导航状态异常: {str(e)}")
    
    def process_navigation_message(self, message):
        """处理导航消息"""
        try:
            # 这里应该有处理导航消息的逻辑
            # 例如解析消息并执行相应的导航操作
            pass
        except Exception as e:
            logger.error(f"处理导航消息异常: {str(e)}")