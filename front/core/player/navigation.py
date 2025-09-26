import time
import random
from utils.logging_setup import logger
from core import global_variable as gv
from core.utils.image_detection import ImageDetection
from core.utils.socket_client import SocketClient
import pyautogui as pyauto

class NavigationHandler:
    def __init__(self):
        """初始化导航处理器"""
        self.player = None  # 玩家引用，在PlayerThread中设置
        self.mm = None  # 鼠标管理器引用，在PlayerThread中设置
        self.send_log = None  # 日志发送函数，在PlayerThread中设置
        self.movement_recorder = None  # 移动记录器引用，在PlayerThread中设置
        self.operator_module = None  # 操作模块引用，在PlayerThread中设置
        self.ocr_module = None  # OCR模块引用，在PlayerThread中设置
        self.get_min_map_yolo_res = None  # 小地图识别函数，在PlayerThread中设置
        
        # 导航相关配置
        self.nav_config = {
            "move_speed": 100,  # 默认移动速度
            "pathfinding_interval": 0.5,  # 寻路间隔
            "door_direction_timeout": 5.0,  # 门方向寻找超时时间
            "movement_timeout": 10.0  # 移动超时时间
        }
        
        # 房间信息
        self.room_info_map = None
        self.player_room_id = None
        self.boss_room_id = None
        self.query_room_id = None
        self.elite_room_id = None
        
        # 检测信息
        self.player_pos = None
        self.monsters = []
        self.goods = []
        self.doors = []
        self.box = []
        self.boss = None
        self.query = None
        self.elite = None
        
        # 状态信息
        self.brush_running = True
        self.last_door_direction = None
        self.last_pathfinding_time = 0
        
        # 门方向缓存
        self.door_direction_cache = {}
        
        # 地图最小房间要求配置
        self.map_min_rooms = {
            "风暴逆鳞普通": 2,
            "德洛斯矿山外围": 2,
            "风暴幽城": 2,
            "深渊：终末崇拜者": 3,
            "流雨瀑布": 2,
            "海伯伦的预言所": 2,
            "红矿村": 2,
            "跌宕群岛": 2
        }
    
    def apply_config(self, config_data):
        """应用配置数据"""
        if not config_data:
            return
        
        # 更新导航配置
        if "nav_config" in config_data:
            self.nav_config.update(config_data["nav_config"])
    
    def get_move_speed(self):
        """获取移动速度"""
        return self.nav_config["move_speed"]
    
    def find_path_to_boss_room(self):
        """寻找BOSS房间路径（A*算法实现）"""
        try:
            if not self.room_info_map or not self.player_room_id or not self.boss_room_id:
                return None
            
            # 这里实现A*算法寻找BOSS房间路径
            # 返回从当前房间到BOSS房间的路径方向列表
            
            # 简化实现：检查当前房间是否与BOSS房间相邻
            if abs(self.player_room_id[0] - self.boss_room_id[0]) <= 1 and abs(self.player_room_id[1] - self.boss_room_id[1]) <= 1:
                # 计算方向
                if self.boss_room_id[0] > self.player_room_id[0]:
                    return "right"
                elif self.boss_room_id[0] < self.player_room_id[0]:
                    return "left"
                elif self.boss_room_id[1] > self.player_room_id[1]:
                    return "up"
                elif self.boss_room_id[1] < self.player_room_id[1]:
                    return "down"
            
            # 默认返回None表示需要更复杂的寻路
            return None
        except Exception as e:
            logger.info(f"寻找BOSS房间路径异常: {str(e)}")
            return None
    
    def find_path_to_query_room(self):
        """寻找问号房间路径（A*算法实现）"""
        try:
            if not self.room_info_map or not self.player_room_id or not self.query_room_id:
                return None
            
            # 这里实现A*算法寻找问号房间路径
            # 返回从当前房间到问号房间的路径方向列表
            
            # 简化实现：检查当前房间是否与问号房间相邻
            if abs(self.player_room_id[0] - self.query_room_id[0]) <= 1 and abs(self.player_room_id[1] - self.query_room_id[1]) <= 1:
                # 计算方向
                if self.query_room_id[0] > self.player_room_id[0]:
                    return "right"
                elif self.query_room_id[0] < self.player_room_id[0]:
                    return "left"
                elif self.query_room_id[1] > self.player_room_id[1]:
                    return "up"
                elif self.query_room_id[1] < self.player_room_id[1]:
                    return "down"
            
            # 默认返回None表示需要更复杂的寻路
            return None
        except Exception as e:
            logger.info(f"寻找问号房间路径异常: {str(e)}")
            return None
    
    def find_path_to_elite_room(self):
        """寻找精英房间路径（A*算法实现）"""
        try:
            if not self.room_info_map or not self.player_room_id or not self.elite_room_id:
                return None
            
            # 这里实现A*算法寻找精英房间路径
            # 返回从当前房间到精英房间的路径方向列表
            
            # 简化实现：检查当前房间是否与精英房间相邻
            if abs(self.player_room_id[0] - self.elite_room_id[0]) <= 1 and abs(self.player_room_id[1] - self.elite_room_id[1]) <= 1:
                # 计算方向
                if self.elite_room_id[0] > self.player_room_id[0]:
                    return "right"
                elif self.elite_room_id[0] < self.player_room_id[0]:
                    return "left"
                elif self.elite_room_id[1] > self.player_room_id[1]:
                    return "up"
                elif self.elite_room_id[1] < self.player_room_id[1]:
                    return "down"
            
            # 默认返回None表示需要更复杂的寻路
            return None
        except Exception as e:
            logger.info(f"寻找精英房间路径异常: {str(e)}")
            return None
    
    def find_path_to_nearest_room_to_boss(self):
        """寻找离BOSS房间最近的房间路径"""
        try:
            if not self.room_info_map or not self.player_room_id or not self.boss_room_id:
                return None
            
            # 简化实现：找到离BOSS房间最近的已探索房间
            min_distance = float('inf')
            nearest_room = None
            
            # 遍历所有已探索的房间
            for room_id in self.room_info_map:
                if self.room_info_map[room_id] == 0:  # 0表示已探索
                    distance = abs(room_id[0] - self.boss_room_id[0]) + abs(room_id[1] - self.boss_room_id[1])
                    if distance < min_distance and room_id != self.boss_room_id:
                        min_distance = distance
                        nearest_room = room_id
            
            # 如果找到最近房间，计算方向
            if nearest_room:
                if abs(nearest_room[0] - self.player_room_id[0]) <= 1 and abs(nearest_room[1] - self.player_room_id[1]) <= 1:
                    if nearest_room[0] > self.player_room_id[0]:
                        return "right"
                    elif nearest_room[0] < self.player_room_id[0]:
                        return "left"
                    elif nearest_room[1] > self.player_room_id[1]:
                        return "up"
                    elif nearest_room[1] < self.player_room_id[1]:
                        return "down"
            
            return None
        except Exception as e:
            logger.info(f"寻找离BOSS房间最近的房间路径异常: {str(e)}")
            return None
    
    def find_door_direction(self):
        """寻找门方向（优先问号房、其次精英房、最后BOSS房）"""
        try:
            # 检查是否应该进行新的寻路
            current_time = time.time()
            if current_time - self.last_pathfinding_time < self.nav_config["pathfinding_interval"]:
                return self.last_door_direction
            
            # 记录开始时间，用于超时控制
            start_time = time.time()
            
            # 门方向缓存键
            cache_key = f"{self.player_room_id}_{self.boss_room_id}_{self.query_room_id}_{self.elite_room_id}"
            
            # 检查缓存
            if cache_key in self.door_direction_cache:
                cache_time, cached_direction = self.door_direction_cache[cache_key]
                if time.time() - cache_time < 2.0:  # 缓存有效期2秒
                    return cached_direction
            
            # 优先寻找问号房间
            query_direction = self.find_path_to_query_room()
            if query_direction and self.query:
                self.last_door_direction = query_direction
                self.door_direction_cache[cache_key] = (time.time(), query_direction)
                return query_direction
            
            # 其次寻找精英房间
            elite_direction = self.find_path_to_elite_room()
            if elite_direction and self.elite:
                self.last_door_direction = elite_direction
                self.door_direction_cache[cache_key] = (time.time(), elite_direction)
                return elite_direction
            
            # 最后寻找BOSS房间
            boss_direction = self.find_path_to_boss_room()
            if boss_direction and self.boss:
                self.last_door_direction = boss_direction
                self.door_direction_cache[cache_key] = (time.time(), boss_direction)
                return boss_direction
            
            # 如果都没有找到，寻找离BOSS房间最近的房间
            nearest_direction = self.find_path_to_nearest_room_to_boss()
            if nearest_direction:
                self.last_door_direction = nearest_direction
                self.door_direction_cache[cache_key] = (time.time(), nearest_direction)
                return nearest_direction
            
            # 检查是否超时
            if time.time() - start_time > self.nav_config["door_direction_timeout"]:
                logger.info("寻找门方向超时")
                return None
            
            # 清除过期缓存（超过5秒）
            self._cleanup_cache()
            
            self.last_door_direction = None
            return None
        except Exception as e:
            logger.info(f"寻找门方向异常: {str(e)}")
            return None
    
    def _cleanup_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []
        for key, (cache_time, _) in self.door_direction_cache.items():
            if current_time - cache_time > 5.0:  # 缓存有效期5秒
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.door_direction_cache[key]
    
    def compute_move_info(self, player_pos, target_pos, offset_x, offset_y):
        """计算移动信息（跑步模式）"""
        try:
            # 计算相对坐标
            dx = target_pos[0] - player_pos[0]
            dy = target_pos[1] - player_pos[1]
            
            # 计算距离
            distance = (dx**2 + dy** 2)** 0.5
            
            # 如果距离太小，不需要移动
            if distance < 10:
                return None
            
            # 计算移动方向
            direction = {}
            if abs(dx) > 10:
                if dx > 0:
                    direction["right"] = True
                else:
                    direction["left"] = True
            
            if abs(dy) > 10:
                if dy > 0:
                    direction["down"] = True
                else:
                    direction["up"] = True
            
            # 添加偏移
            if offset_x != 0:
                if offset_x > 0:
                    direction["right"] = True
                else:
                    direction["left"] = True
            
            if offset_y != 0:
                if offset_y > 0:
                    direction["down"] = True
                else:
                    direction["up"] = True
            
            # 跑步模式：添加shift键
            direction["shift"] = True
            
            return direction
        except Exception as e:
            logger.info(f"计算移动信息异常: {str(e)}")
            return None
    
    def compute_move_info_walk(self, player_pos, target_pos, offset_x, offset_y):
        """计算移动信息（步行模式）"""
        try:
            # 计算相对坐标
            dx = target_pos[0] - player_pos[0]
            dy = target_pos[1] - player_pos[1]
            
            # 计算距离
            distance = (dx**2 + dy** 2)** 0.5
            
            # 如果距离太小，不需要移动
            if distance < 5:
                return None
            
            # 计算移动方向
            direction = {}
            if abs(dx) > 5:
                if dx > 0:
                    direction["right"] = True
                else:
                    direction["left"] = True
            
            if abs(dy) > 5:
                if dy > 0:
                    direction["down"] = True
                else:
                    direction["up"] = True
            
            # 添加偏移
            if offset_x != 0:
                if offset_x > 0:
                    direction["right"] = True
                else:
                    direction["left"] = True
            
            if offset_y != 0:
                if offset_y > 0:
                    direction["down"] = True
                else:
                    direction["up"] = True
            
            # 步行模式：不添加shift键
            return direction
        except Exception as e:
            logger.info(f"计算步行移动信息异常: {str(e)}")
            return None
    
    def move_to_monster(self):
        """向怪物移动"""
        try:
            if not self.monsters or not self.player_pos:
                return False
            
            # 找到最近的怪物
            min_distance = float('inf')
            nearest_monster = None
            
            for monster in self.monsters:
                dx = monster[0] - self.player_pos[0]
                dy = monster[1] - self.player_pos[1]
                distance = (dx**2 + dy** 2)** 0.5
                if distance < min_distance:
                    min_distance = distance
                    nearest_monster = monster
            
            if nearest_monster and min_distance > 50:  # 如果距离足够远，需要移动
                # 计算移动信息
                move_info = self.compute_move_info(self.player_pos, nearest_monster, 0, 0)
                
                if move_info:
                    # 执行移动
                    self._execute_move(move_info)
                    return True
            
            return False
        except Exception as e:
            logger.info(f"向怪物移动异常: {str(e)}")
            return False
    
    def _execute_move(self, move_info):
        """执行移动"""
        try:
            # 释放所有按键
            pyauto.releaseallkey()
            
            # 按下方向键
            if "shift" in move_info and move_info["shift"]:
                pyauto.keyDown('shift')
            
            if "left" in move_info and move_info["left"]:
                pyauto.keyDown('left')
            
            if "right" in move_info and move_info["right"]:
                pyauto.keyDown('right')
            
            if "up" in move_info and move_info["up"]:
                pyauto.keyDown('up')
            
            if "down" in move_info and move_info["down"]:
                pyauto.keyDown('down')
            
            # 保持按键一段时间
            time.sleep(0.1)
            
            # 释放所有按键
            pyauto.releaseallkey()
        except Exception as e:
            logger.info(f"执行移动异常: {str(e)}")
            pyauto.releaseallkey()
    
    def process_detect_message(self, message):
        """处理检测消息"""
        try:
            # 解析检测消息
            # 这里应该根据实际的消息格式进行解析
            # 以下是示例代码
            
            # 更新检测信息
            # self.player_pos = message.get("player_pos")
            # self.monsters = message.get("monsters", [])
            # self.goods = message.get("goods", [])
            # self.doors = message.get("doors", [])
            # self.box = message.get("box", [])
            # self.boss = message.get("boss")
            # self.query = message.get("query")
            # self.elite = message.get("elite")
            pass
        except Exception as e:
            logger.info(f"处理检测消息异常: {str(e)}")
    
    def find_nearest_zero_to_target(self, matrix, target):
        """找到离目标最近的0值"""
        try:
            if not matrix or not target:
                return None
            
            min_distance = float('inf')
            nearest_pos = None
            
            # 遍历矩阵
            for i in range(len(matrix)):
                for j in range(len(matrix[i])):
                    if matrix[i][j] == 0:
                        dx = j - target[0]
                        dy = i - target[1]
                        distance = (dx**2 + dy** 2)** 0.5
                        if distance < min_distance:
                            min_distance = distance
                            nearest_pos = (j, i)
            
            return nearest_pos
        except Exception as e:
            logger.info(f"找到离目标最近的0值异常: {str(e)}")
            return None
    
    def find_door_pos(self):
        """找到门的位置"""
        try:
            if not self.doors:
                return None
            
            # 简化实现：返回第一个门的位置
            return self.doors[0]
        except Exception as e:
            logger.info(f"找到门的位置异常: {str(e)}")
            return None
    
    def enter_door(self):
        """进入门"""
        try:
            if not self.doors or not self.last_door_direction:
                return False
            
            # 找到门的位置
            door_pos = self.find_door_pos()
            if not door_pos:
                return False
            
            # 移动到门前
            if self.player_pos:
                # 计算移动信息（步行模式）
                move_info = self.compute_move_info_walk(self.player_pos, door_pos, 0, 0)
                
                if move_info:
                    # 执行移动
                    self._execute_move(move_info)
                    
                    # 等待一段时间让角色走到门前
                    time.sleep(0.5)
            
            # 根据门方向使用方向键
            if self.last_door_direction == "left":
                pyauto.keyDown('left')
                time.sleep(0.2)
                pyauto.keyUp('left')
            elif self.last_door_direction == "right":
                pyauto.keyDown('right')
                time.sleep(0.2)
                pyauto.keyUp('right')
            elif self.last_door_direction == "up":
                pyauto.keyDown('up')
                time.sleep(0.2)
                pyauto.keyUp('up')
            elif self.last_door_direction == "down":
                pyauto.keyDown('down')
                time.sleep(0.2)
                pyauto.keyUp('down')
            
            # 等待门打开
            time.sleep(1.0)
            
            return True
        except Exception as e:
            logger.info(f"进入门异常: {str(e)}")
            return False
    
    def test_move(self):
        """测试移动（卡点移动处理）"""
        try:
            # 检查是否需要测试移动（例如，当角色卡住时）
            # 这里实现特定的坐标移动逻辑来解决卡点问题
            
            # 随机移动一小段距离
            directions = ['left', 'right', 'up', 'down']
            direction = random.choice(directions)
            
            pyauto.keyDown(direction)
            time.sleep(0.1)
            pyauto.keyUp(direction)
            
            logger.info(f"执行测试移动: {direction}")
            
            return True
        except Exception as e:
            logger.info(f"测试移动异常: {str(e)}")
            return False
    
    def player_left_right_move(self):
        """玩家左右移动切换"""
        try:
            # 随机左右移动
            for _ in range(3):  # 移动3次
                direction = 'left' if random.random() > 0.5 else 'right'
                pyauto.keyDown(direction)
                time.sleep(0.1)
                pyauto.keyUp(direction)
                time.sleep(0.1)
            
            logger.info("执行玩家左右移动切换")
            
            return True
        except Exception as e:
            logger.info(f"玩家左右移动切换异常: {str(e)}")
            return False
    
    def reset_navigation_state(self):
        """重置导航状态"""
        self.last_door_direction = None
        self.last_pathfinding_time = 0
        self.door_direction_cache.clear()
        
        # 重置检测信息
        self.player_pos = None
        self.monsters = []
        self.goods = []
        self.doors = []
        self.box = []
        self.boss = None
        self.query = None
        self.elite = None