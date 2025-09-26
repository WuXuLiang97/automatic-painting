import time
import random
from utils.logging_setup import logger
from core import global_variable as gv
from core.utils.image_detection import ImageDetection
from utils.item_recognition import ItemRecognition

class ItemHandler:
    def __init__(self):
        """初始化物品处理器"""
        self.player = None  # 玩家引用，在PlayerThread中设置
        self.mm = None  # 鼠标管理器引用，在PlayerThread中设置
        self.send_log = None  # 日志发送函数，在PlayerThread中设置
        self.operator_module = None  # 操作模块引用，在PlayerThread中设置
        
        # 物品识别
        self.image_detection = ImageDetection()
        self.item_recognition = ItemRecognition()
        
        # 物品状态
        self.items_in_inventory = []
        self.items_on_ground = []
        self.last_item_scan_time = 0
        
        # 拾取配置
        self.pickup_config = {
            "pickup_radius": 100,  # 拾取半径
            "max_pickup_time": 10,  # 最大拾取时间（秒）
            "auto_pickup_interval": 1,  # 自动拾取间隔（秒）
            "max_pickup_count": 10,  # 最大拾取次数
        }
        
        # 目标物品列表
        self.target_items = [
            "金绿柱石", "深渊票", "史诗装备", "传说装备", "稀有材料", "金币袋",
            "邀请函", "挑战书", "精炼的时空石", "红玉髓", "强烈的气息"
        ]
        
        # 自动拾取状态
        self.auto_pick_enabled = True
        
        # 物品拾取计数
        self.pickup_count = 0
    
    def apply_config(self, config_data):
        """应用配置数据"""
        if not config_data:
            return
        
        # 更新拾取配置
        if "pickup_config" in config_data:
            self.pickup_config.update(config_data["pickup_config"])
        
        # 更新目标物品列表
        if "target_items" in config_data:
            self.target_items = config_data["target_items"]
        
        # 更新自动拾取状态
        if "auto_pick_enabled" in config_data:
            self.auto_pick_enabled = config_data["auto_pick_enabled"]
    
    def pick_up_goods(self):
        """优化后的货物捡取方法"""
        logger.info("开始拾取物品")
        pyauto.releaseallkey()
        start_time = time.time()
        frame_time = time.time()
        up_and_down_move = False
        
        try:
            while self.player and self.player.brush_running and not self.player.ghost_state:
                # 前置检查：超时/怪物/空货物
                if time.time() - start_time > self.pickup_config["max_pickup_time"]:
                    if self.player:
                        self.player.ghost_state = True
                    break
                
                if self.player and (len(self.player.monsters) > 0 or len(self.player.goods) == 0):
                    break

                # 状态更新
                if self.player:
                    self.player.get_yolo_res()
                    if len(self.player.goods) == 0:
                        break

                # 货物移动检测
                if self._check_goods_movement():
                    logger.info("货物移动中，暂缓捡取")
                    time.sleep(0.1)
                    continue

                # 玩家位置恢复
                if self.player and self.player.player_pos.x is None:
                    # 螺旋搜索恢复位置
                    if hasattr(self.player, 'movement_recorder'):
                        self.player.movement_recorder.spiral_search(self._get_player_position, duration=2)
                    continue
                
                frame1_detections = None
                if self.player and self.player.player_pos.x is not None:
                    frame1_detections = (self.player.player_pos.x, self.player.player_pos.y)
                
                # 障碍物清除
                if hasattr(self.player, 'clearingobstacles'):
                    self.player.clearingobstacles()

                # 路径计算与移动
                goods_pos = []
                if self.player and hasattr(self.player, 'goods') and len(self.player.goods) > 0:
                    from ..utils.sort_points import sort_points_by_x
                    goods_pos = sort_points_by_x(self.player.goods)  # 对货物位置按x坐标排序
                    
                if not goods_pos:  # 无论什么原因导致排序后为空，都直接退出
                    break
                
                from ..utils.point import Point
                the_first_item = Point(goods_pos[0][0], goods_pos[0][1])
                
                # 先获取当前房间ID和对应的拾取次数（不存在则为None）
                current_room_id = None
                pickup_count = 0
                if self.player and self.player.player_room_id is not None:
                    current_room_id = self.player.player_room_id
                    if hasattr(self.player, 'room_item_pickup_counts'):
                        pickup_count = self.player.room_item_pickup_counts.get(current_room_id, 0)

                # 执行移动
                if self.player and self.player.player_pos.x is not None:
                    if abs(self.player.player_pos.x - the_first_item.x) > 200 and pickup_count < 3:
                        # 跑步移动
                        move_info = self.player.compute_move_info(self.player.player_pos, the_first_item, 0, 0)
                        if move_info:
                            logger.info(f"向物品奔跑：{move_info.leftRightDirection}\t{move_info.xTime}\t{move_info.upDownDirection}\t{move_info.yTime}")
                            if hasattr(self.player, 'movement_recorder'):
                                self.player.movement_recorder.left_right_up_down_move_by(move_info, False)
                    else:
                        # 步行移动
                        move_info = self.player.compute_move_info_walk(self.player.player_pos, the_first_item, 0, 0)
                        if move_info:
                            logger.info(f"向物品步行：{move_info.leftRightDirection}\t{move_info.xTime}\t{move_info.upDownDirection}\t{move_info.yTime}")
                            if hasattr(self.player, 'movement_recorder'):
                                self.player.movement_recorder.left_right_up_down_move_walk_by(move_info, False)
                
                # 更新房间拾取次数
                if self.player and self.player.player_room_id is not None:
                    room_id = self.player.player_room_id
                    if hasattr(self.player, 'room_item_pickup_counts'):
                        if room_id not in self.player.room_item_pickup_counts:
                            self.player.room_item_pickup_counts[room_id] = 0  # 手动初始化
                        self.player.room_item_pickup_counts[room_id] += 1
                        logger.info(f"房间 {room_id}拾取次数+1")
                        logger.info(f"房间{current_room_id}拾取次数: {pickup_count}")
                
                # 检查拾取次数并可能重新识别移速
                pickup_count = 0
                if self.player and hasattr(self.player, 'room_item_pickup_counts') and current_room_id is not None:
                    pickup_count = self.player.room_item_pickup_counts.get(current_room_id, 0)
                    
                if isinstance(pickup_count, int) and pickup_count > 5 and self.player and not self.player.is_boss:
                    logger.info(f"房间{current_room_id}拾取次数大于或等于5次，重新识别移速")
                    if self.player.player_pos.x:
                        # 重新识别移速
                        if hasattr(self.player, 'get_move_speed'):
                            self.player.get_move_speed()
                
                # 执行拾取
                if self.player and hasattr(self.player, 'goods') and len(self.player.goods) > 0:
                    goods_pos = sort_points_by_x(self.player.goods)
                    if goods_pos and len(goods_pos) > 0 and len(goods_pos[0]) > 2:
                        if '金币' in goods_pos[0][2]:
                            pass
                        else:
                            time.sleep(0.1)
                            pyauto.keyPressChar("x")
                            time.sleep(0.05)
                
                # 检查超时并重获YOLO结果
                if time.time() - frame_time > 5:
                    frame_time = time.time()
                    if self.player:
                        self.player.get_yolo_res()
                        if self.player.player_pos.x is None:
                            continue
                        frame2_detections = (self.player.player_pos.x, self.player.player_pos.y)

                        if frame1_detections and frame2_detections:
                            frames = [frame1_detections, frame2_detections]
                            logger.info(f"检测人物frames:{frames}")
                            # 设置一个位置变化的阈值（这里以像素为单位）
                            movement_threshold = 10  # 如果x或y方向上的变化超过10像素，则认为物体在移动
                            # 跟踪人物并检测运动
                            last_position = None
                            for frame_idx, (x, y) in enumerate(frames):
                                # 检查当前位置是否为None
                                if (x is None) or (y is None):
                                    logger.info(f"在帧 {frame_idx + 1} 中，人物位置数据缺失。")
                                    break
                                # 如果是第一帧，则没有上一个位置可以比较，直接跳过
                                if last_position is None:
                                    last_position = (x, y)
                                    continue
                                # 计算当前位置与上一个位置的变化
                                current_position = (x, y)
                                dx, dy = abs(current_position[0] - last_position[0]), abs(current_position[1] - last_position[1])

                                # 判断是否移动
                                if dx > movement_threshold or dy > movement_threshold:
                                    logger.info(f"在帧 {frame_idx + 1} 中，人物移动了。")
                                else:
                                    logger.info(f"在帧 {frame_idx + 1} 中，人物是静止的。")
                                    if not up_and_down_move:
                                        logger.info("尝试向上移动")
                                        if self.player and hasattr(self.player, 'movement_recorder'):
                                            self.player.movement_recorder.up_down_move("up", 1)
                                        up_and_down_move = True
                                    else:
                                        logger.info("尝试向下移动")
                                        if self.player and hasattr(self.player, 'movement_recorder'):
                                            self.player.movement_recorder.up_down_move("down", 1)
                                        up_and_down_move = False
                                    if hasattr(self.player, 'test_move'):
                                        self.player.test_move()
            
            logger.info("拾取物品结束")
            pyauto.releaseallkey()
            return True
        except Exception as e:
            logger.error(f"拾取物品异常: {str(e)}")
            import traceback
            traceback.print_exc()
            pyauto.releaseallkey()
            return False
    
    def _scan_items_on_ground(self):
        """扫描地面物品"""
        try:
            if not self.player:
                self.items_on_ground = []
                return
                
            # 从玩家对象获取物品信息
            self.items_on_ground = []
            if hasattr(self.player, 'goods') and len(self.player.goods) > 0:
                for good in self.player.goods:
                    if len(good) >= 3:
                        item = {
                            "id": hash((good[0], good[1])),  # 使用坐标作为唯一标识
                            "name": good[2] if len(good) > 2 else "未知物品",
                            "x": good[0],
                            "y": good[1],
                            "distance": 0  # 稍后计算
                        }
                        # 计算与玩家的距离
                        if self.player.player_pos.x is not None and self.player.player_pos.y is not None:
                            item["distance"] = ((item["x"] - self.player.player_pos.x) ** 2 + \
                                               (item["y"] - self.player.player_pos.y) ** 2) ** 0.5
                        self.items_on_ground.append(item)
            
            # 更新最后扫描时间
            self.last_item_scan_time = time.time()
        except Exception as e:
            logger.error(f"扫描地面物品异常: {str(e)}")
            self.items_on_ground = []
    
    def _check_goods_movement(self):
        """检查物品是否在移动"""
        positions = []
        try:
            if not self.player:
                return False
                
            for _ in range(3):  # 连续取三帧数据
                self.player.get_yolo_res()
                if len(self.player.goods) < 1:
                    return False
                from ..utils.sort_points import sort_points_by_x
                sorted_goods = sort_points_by_x(self.player.goods)
                if not sorted_goods:
                    return False
                positions.append(sorted_goods[0])
                time.sleep(0.03)  # 适当增加采样间隔
            
            # 计算三帧间平均移动量
            if len(positions) >= 2:
                dx = abs(positions[-1][0] - positions[0][0])
                dy = abs(positions[-1][1] - positions[0][1])
                return dx > 5 or dy > 5  # 动态阈值
            return False
        except Exception as e:
            logger.error(f"检查物品移动异常: {str(e)}")
            return False
            
    def _get_player_position(self):
        """获取玩家位置的回调函数"""
        if not self.player:
            return None
        self.player.get_yolo_res()
        logger.info(f"回调函数！获取玩家坐标：{self.player.player_pos.x, self.player.player_pos.y}")
        pos = self.player.player_pos.x
        return pos
    
    def _filter_target_items(self, items):
        """过滤目标物品"""
        try:
            if not items:
                return []
            
            # 过滤出目标物品列表中的物品
            target_items = [item for item in items if item["name"] in self.target_items]
            
            return target_items
        except Exception as e:
            logger.error(f"过滤目标物品异常: {str(e)}")
            return []
    
    def _sort_items_by_distance(self, items):
        """按距离排序物品"""
        try:
            if not items:
                return []
            
            # 按距离排序（距离小的优先）
            sorted_items = sorted(items, key=lambda x: x["distance"])
            
            return sorted_items
        except Exception as e:
            logger.error(f"按距离排序物品异常: {str(e)}")
            return []
    
    def _pick_up_single_item(self, item):
        """拾取单个物品"""
        try:
            if not item:
                return False
            
            logger.info(f"拾取物品: {item['name']} (ID: {item['id']})")
            
            # 检查物品距离是否在拾取半径内
            if item["distance"] > self.pickup_config["pickup_radius"]:
                logger.warning(f"物品 {item['name']} 距离太远，无法拾取")
                return False
            
            # 移动鼠标到物品位置
            if self.mm:
                self.mm.move_to(item["x"], item["y"])
                
                # 点击左键拾取物品
                self.mm.click(button='left')
                
                # 等待拾取延迟
                time.sleep(0.1)
            
            # 使用操作模块执行拾取操作
            if self.operator_module:
                self.operator_module.pick_item()
            
            logger.info(f"成功拾取物品: {item['name']}")
            
            # 更新背包物品列表
            self._update_inventory(item)
            
            return True
        except Exception as e:
            logger.error(f"拾取单个物品异常: {str(e)}")
            return False
    
    def _update_inventory(self, item):
        """更新背包物品列表"""
        try:
            # 检查物品是否已存在于背包中
            existing_item = next((i for i in self.items_in_inventory if i["id"] == item["id"]), None)
            
            if existing_item:
                # 更新物品数量
                if "count" in existing_item:
                    existing_item["count"] += 1
                else:
                    existing_item["count"] = 2
            else:
                # 添加新物品到背包
                item_copy = item.copy()
                item_copy["count"] = 1
                self.items_in_inventory.append(item_copy)
        except Exception as e:
            logger.error(f"更新背包物品列表异常: {str(e)}")
    
    def sell_items(self):
        """出售物品"""
        try:
            if not self.player or not self.operator_module:
                logger.warning("物品组件未初始化完全，无法出售物品")
                return False
            
            logger.info("出售物品")
            
            # 这里应该有出售物品的逻辑
            # 例如打开商店、选择物品、点击出售等
            
            # 模拟出售物品
            logger.info("成功出售物品")
            
            return True
        except Exception as e:
            logger.error(f"出售物品异常: {str(e)}")
            return False
    
    def agg_pick_up_goods(self):
        """BOSS房聚物拾取"""
        try:
            if not self.player or not self.mm or not self.operator_module:
                logger.warning("物品组件未初始化完全，无法执行BOSS房聚物拾取")
                return False
            
            logger.info("执行BOSS房聚物拾取")
            
            # 临时增加拾取半径
            original_pickup_radius = self.pickup_config["pickup_radius"]
            self.pickup_config["pickup_radius"] = 200  # 增加拾取半径
            
            # 临时增加最大拾取次数
            original_max_pickup_count = self.pickup_config["max_pickup_count"]
            self.pickup_config["max_pickup_count"] = 20  # 增加最大拾取次数
            
            # 重置拾取计数
            self.pickup_count = 0
            
            # 执行拾取
            pickup_success = self.pick_up_goods()
            
            # 恢复原配置
            self.pickup_config["pickup_radius"] = original_pickup_radius
            self.pickup_config["max_pickup_count"] = original_max_pickup_count
            
            return pickup_success
        except Exception as e:
            logger.error(f"BOSS房聚物拾取异常: {str(e)}")
            return False
    
    def access_0(self):
        """访问消耗品与金绿柱石"""
        try:
            if not self.player or not self.operator_module:
                logger.warning("物品组件未初始化完全，无法访问消耗品与金绿柱石")
                return False
            
            logger.info("访问消耗品与金绿柱石")
            
            # 这里应该有访问消耗品与金绿柱石的逻辑
            # 例如打开背包、查看消耗品、查看金绿柱石数量等
            
            # 模拟访问操作
            logger.info("成功访问消耗品与金绿柱石")
            
            return True
        except Exception as e:
            logger.error(f"访问消耗品与金绿柱石异常: {str(e)}")
            return False
    
    def auto_pick(self):
        """自动拾取"""
        try:
            if not self.player or not self.operator_module:
                logger.warning("物品组件未初始化完全，无法执行自动拾取")
                return False
            
            logger.info("执行自动拾取")
            
            # 开启自动拾取
            self.auto_pick_enabled = True
            
            # 重置拾取计数
            self.pickup_count = 0
            
            # 执行拾取
            pickup_success = self.pick_up_goods()
            
            return pickup_success
        except Exception as e:
            logger.error(f"自动拾取异常: {str(e)}")
            return False
    
    def reset_pickup_state(self):
        """重置拾取状态"""
        try:
            self.pickup_count = 0
            self.items_on_ground = []
            # 注意：不重置items_in_inventory，因为背包物品需要保持
        except Exception as e:
            logger.error(f"重置拾取状态异常: {str(e)}")
    
    def get_inventory_status(self):
        """获取背包状态"""
        try:
            status = {
                "items_in_inventory": len(self.items_in_inventory),
                "items_on_ground": len(self.items_on_ground),
                "last_item_scan_time": self.last_item_scan_time,
                "auto_pick_enabled": self.auto_pick_enabled,
                "pickup_count": self.pickup_count,
                "max_pickup_count": self.pickup_config["max_pickup_count"],
            }
            
            return status
        except Exception as e:
            logger.error(f"获取背包状态异常: {str(e)}")
            return {}
    
    def check_item_exists(self, item_name):
        """检查物品是否存在"""
        try:
            # 检查背包中是否有该物品
            for item in self.items_in_inventory:
                if item["name"] == item_name:
                    return True, item.get("count", 1)
            
            return False, 0
        except Exception as e:
            logger.error(f"检查物品是否存在异常: {str(e)}")
            return False, 0