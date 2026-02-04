import cv2
import re
import traceback
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from utils.logging_setup import logger
from core.common import Point
from utils.minimap_util import miniMapUtil
from core import global_variable as gv

# 常量定义
SIMILARITY_THRESHOLD = 0.6

@dataclass
class YoloProcessResult:
    """YOLO检测结果处理后的数据结构"""
    attack_boss_sy: List[Tuple[float, float]] = field(default_factory=list)
    goods: List[Tuple[int, int, str]] = field(default_factory=list)
    doors: List[Point] = field(default_factory=list)
    monsters: List[Tuple[float, float]] = field(default_factory=list)
    box: List[Point] = field(default_factory=list)
    player_pos: Point = field(default_factory=lambda: Point(None, None))
    has_rewards: bool = False
    has_continue: bool = False
    forward: bool = False
    is_boss: bool = False
    # 以下字段用于在 apply_to_context 中更新上下文状态（而不是在解析阶段直接修改）
    should_process_loot: bool = False
    door_open_room_id: Optional[Tuple[int, int]] = None

@dataclass
class MinMapProcessResult:
    """小地图检测结果处理后的数据结构"""
    player_room_id: Optional[Tuple[int, int]] = None
    query_room_id: Optional[Tuple[int, int]] = None
    elite_room_id: Optional[Tuple[int, int]] = None
    boss_room_id: Optional[Tuple[int, int]] = None
    special_room_id: Optional[Tuple[int, int]] = None
    room_info_map: Optional[dict] = None

class YoloHandler:
    """
    YOLO检测结果处理类，封装了YOLO目标检测结果的解析和处理逻辑
    包括玩家位置、物品、怪物、门等游戏元素的识别和处理
    """
    def __init__(self):
        """
        初始化YoloHandler实例
        """
        pass
    
    def process_detect_message(self, context, cls, game_image):
        """
        处理检测到的消息，返回处理后的游戏状态结果

        Args:
            context: 上下文对象，提供必要的配置信息
            cls (list): 包含多个元组的列表，每个元组代表一个检测到的游戏元素
            game_image: 游戏图像（numpy数组）

        Returns:
            YoloProcessResult: 处理后的游戏状态结果对象

        每个元组的结构通常为 [元素类型, x坐标, y坐标, 宽度, 高度, 置信度]
        """
        # 创建结果对象
        result = YoloProcessResult()
        
        # 初始化玩家位置
        result.player_pos = Point(None, None)

        # 遍历检测到的每个元素
        goods = []
        for data in cls:
            logger.info(f"data:{data}")
            # 处理玩家位置
            if data[0] == "player":
                if data[4] + context.player.player_height < 620:
                    result.player_pos.x = (data[1] + data[3]) / 2  # 玩家x坐标取边界中点
                    result.player_pos.y = data[4] + context.player.player_height  # 玩家y坐标考虑玩家高度
                else:
                    logger.info(f"玩家位置识别错误！！！")
            # 处理物品
            elif data[0].startswith("attack_boss_sy"):
                # 如果物品位置在特定区域外，也跳过
                if 5 < data[1] < 22 and 408 < data[2] < 425:
                    continue
                x = (data[1] + data[3]) / 2  # 门x坐标取边界中点
                y = data[4]
                result.attack_boss_sy.append((x, y))  # 将attack_boss_sy添加到列表中

            # 处理继续游戏的选项
            elif data[0] == "continue":
                x = (data[1] + data[3]) / 2  # 门x坐标取边界中点
                y = (data[2] + data[4]) / 2  # 门x坐标取边界中点
                box = (871, 29, 1013, 79)  # 矩形框的坐标：(左, 上, 右, 下)
                if box[0] < x < box[2] and box[1] < y < box[3]:
                    result.has_continue = True  # 标记有继续游戏的选项
                    result.is_boss = True  # 假设遇到继续即视为Boss关
                logger.info(f"{data}")
                continue
            elif data[0].startswith("goods") and data[5] > 0.5:
                if not result.is_boss and context.player.map_name == "深渊：终末崇拜者":
                    logger.info(f"刷深渊中，当前不是boss房不捡物品")
                    continue
                # 如果物品位置在特定区域外，也跳过
                if 5 < data[1] < 22 and 340 < data[2] < 354:
                    continue
                goods.append((int(data[1]), int(data[2]), int(data[3]), int(data[4])))  # 将物品添加到列表中

            # 处理怪物和Boss
            elif data[0].startswith(("monster", "boss")):
                logger.info(data)

                # 计算怪物x坐标（所有怪物类型通用）
                x = (data[1] + data[3]) / 2

                # 计算怪物y坐标（根据不同怪物类型进行调整）
                y = data[4]  # 默认值

                if data[0].startswith("boss") and data[5] > 0.5:
                    # 从地图BOSS信息中获取高度数据
                    boss_info = context.map_boss_info.get(context.player.map_name, "").get(data[0])
                    if boss_info:
                        y += boss_info.get('height', 0)  # 使用height值，如果没有则默认为0
                        min_rooms = context.MAP_MIN_ROOMS.get(context.player.map_name, 2)
                        logger.info(f"yolo处理 最少房间要求为：{min_rooms}")
                        if context.getOpenedRoomsCount() >= min_rooms:
                            logger.info(f"yolo处理 当前房间是boss房")
                            if context.player.map_name == "深渊：终末崇拜者":
                                result.is_boss = True
                            else:
                                ocr_text = context.get_text(int(data[1]), int(data[2]), int(data[3]), int(data[4]),
                                                         game_image).strip()
                                pattern = r'[\u4e00-\u9fa5]+'
                                # 使用 re.findall() 找出所有匹配的内容
                                matches = re.findall(pattern, ocr_text)
                                t = "".join(matches)
                                logger.info(f"识别领主：{ocr_text}")
                                if "领主" in t:
                                    result.is_boss = True
                    else:
                        logger.info(
                            f"当前地图：{context.player.map_name},识别的数据：{data}，不是本地图的怪物，应该是识别错误已跳过本条信息处理")
                        continue

                elif data[0] == "monster_frost":
                    # 冰霜怪物不需要额外调整
                    pass
                elif data[0].startswith("monster_115"):
                    # 从地图BOSS信息中获取高度数据
                    monster_info = context.map_boss_info.get(context.player.map_name, "").get(data[0])
                    if monster_info:
                        y += monster_info.get('height', 0)  # 使用height值，如果没有则默认为0
                else:
                    # 其他怪物类型的默认调整
                    y += 120

                # 将怪物添加到列表中
                result.monsters.append((x, y))
                if data[0].startswith("boss_sy") and context.player.map_name == "深渊：终末崇拜者" and context.to_door_count >= 3:
                    logger.info(f"当前过门次数context.to_door_count：{context.to_door_count}")
                    result.is_boss = True  # 假设遇到继续即视为Boss关
                    continue

            # 处理门
            elif data[0].startswith("door"):
                x = (data[1] + data[3]) / 2  # 门x坐标取边界中点
                y = data[4] - 17.5  # 门y坐标调整
                if context.player.map_name == "风暴逆鳞普通":
                    if 291 < x < 824 and 474 < y < 600:
                        y = 600
                else:
                    # 直接使用导入的a_DictInfo，而不是通过context对象访问
                    from core.common import a_DictInfo
                    room_info = a_DictInfo.get(context.player.map_name).get("down")
                    if room_info['min_x'] < x < room_info['max_x'] and y > 480:
                        if context.player.map_name == "德洛斯矿山外围":
                            y = 600
                        else:
                            y = 560
                result.doors.append(Point(x, y))  # 将门添加到列表中
            elif data[0].startswith("forward") and context.player.map_name == "深渊：终末崇拜者":
                result.forward = True
                if data[1] > 1067 / 2:
                    result.doors.append(Point(random.randint(1350, 1467), random.randint(400, 450)))  # 将门添加到列表中
                else:
                    continue

            # 处理奖励
            elif data[0] == "reward":
                # 判断是否在这个区域，不然可能误判
                x = (data[1] + data[3]) / 2  # 门x坐标取边界中点
                y = (data[2] + data[4]) / 2  # 门x坐标取边界中点
                box = (398, 0, 566, 72)  # 矩形框的坐标：(左, 上, 右, 下)
                if box[0] < x < box[2] and box[1] < y < box[3]:
                    result.has_rewards = True  # 标记有奖励
                    result.is_boss = True  # 假设遇到奖励即视为Boss关

            # 处理障碍
            elif data[0] == "box_lypb":
                x = (data[1] + data[3]) / 2  # 障碍x坐标取边界中点
                y = (data[4] + 90)  # 障碍y坐标取边界中点
                result.box.append(Point(x, y))  # 将障碍添加到列表中
        
        room_id = context.player.player_room_id
        if gv.banzhuan == 0:
            should_process = (len(result.doors) > 0 or result.has_continue or result.has_rewards)
            if should_process:
                result.monsters.clear()
                # 记录需要在 apply_to_context 中将该房间标记为“已开门”
                result.door_open_room_id = room_id
        else:
            should_process = (not result.monsters or result.has_continue or result.has_rewards)

        result.should_process_loot = should_process

        current_room_id = context.player.player_room_id
        pickup_count = context.room_item_pickup_counts.get(current_room_id, 0)
        # 调试输出：打印两个条件的值
        logger.info(f"\n拾取物品的条件：\n\tshould_process : {should_process}"
                    f"\n\tcontext.doorOpenState.get(room_id) : {context.doorOpenState.get(room_id)}"
                    f"\n\tpickup_count : {pickup_count}")

        if (should_process or context.doorOpenState.get(room_id)) and pickup_count < 10:
            # 公共的商品处理逻辑
            filtered_goods = []
            for dx, dy, dx1, dy1 in goods:
                text = context.get_text(dx, dy, dx1, dy1, game_image)
                logger.info(f"识别物品：{text}")
                cleaned_text = re.sub(r'[^\u4e00-\u9fa5]', '', text)

                # 检查是否需要过滤此物品
                should_filter = any(
                    self.similarity(cleaned_text, item) >= SIMILARITY_THRESHOLD
                    for item in context.target_items
                )

                if should_filter:
                    logger.info(f"已筛选掉：{text}")
                else:
                    filtered_goods.append((dx, dy, dx1, dy1, cleaned_text))

            # 计算商品中心点坐标
            result.goods = [(int((dx + dx1) / 2), dy1 + 20, text) for dx, dy, dx1, dy1, text in filtered_goods]
            logger.info(f"result.goods:{result.goods}")
        
        return result
    
    def apply_to_context(self, context, result):
        """
        将YoloProcessResult应用到上下文对象
        
        Args:
            context: 上下文对象
            result: YoloProcessResult对象
        """
        # 更新游戏元素信息
        context.attack_boss_sy.clear()
        context.attack_boss_sy.extend(result.attack_boss_sy)
        
        context.goods.clear()
        context.goods.extend(result.goods)
        
        context.doors.clear()
        context.doors.extend(result.doors)
        
        context.monsters.clear()
        context.monsters.extend(result.monsters)
        
        context.box.clear()
        context.box.extend(result.box)
        
        # 更新其他状态标志
        context.forward = result.forward
        context.has_rewards = result.has_rewards
        context.has_continue = result.has_continue
        context.is_boss = result.is_boss
        context.player_pos = result.player_pos

        # 在解析阶段记录的“开门房间”和拾取条件，这里统一更新上下文状态
        room_id = context.player.player_room_id
        if gv.banzhuan == 0 and result.door_open_room_id is not None:
            if result.door_open_room_id not in context.doorOpenState:
                context.doorOpenState[result.door_open_room_id] = True  # 记录已开门

        # 更新当前房间的拾取次数（避免无限捡东西）
        current_room_id = context.player.player_room_id
        if result.goods:
            context.room_item_pickup_counts[current_room_id] = context.room_item_pickup_counts.get(current_room_id, 0) + 1
    
    def similarity(self, s1, s2):
        """计算字符串相似度（0-1）"""
        # 计算编辑距离
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            for j in range(n + 1):
                if i == 0:
                    dp[i][j] = j
                elif j == 0:
                    dp[i][j] = i
                else:
                    cost = 0 if s1[i - 1] == s2[j - 1] else 1
                    dp[i][j] = min(dp[i - 1][j] + 1,  # 删除
                                   dp[i][j - 1] + 1,  # 插入
                                   dp[i - 1][j - 1] + cost)  # 替换

        distance = dp[m][n]
        max_len = max(m, n)
        return 1 - distance / max_len if max_len > 0 else 1.0
    
    def min_map_process_detect_message(self, context, cls):
        """
        处理小地图检测结果，返回处理后的地图信息结果
        
        Args:
            context: 上下文对象
            cls: 检测结果列表
        
        Returns:
            MinMapProcessResult: 处理后的地图信息结果对象
        """
        # 创建结果对象
        result = MinMapProcessResult()
        
        # 初始化数据
        query_room_id_list = []
        elite_room_id_list = []
        screen_out = []
        
        for data in cls:
            # 处理玩家位置
            if data[0] == "map_hero":
                x = int((data[1] + data[3]) / 2)
                y = int((data[2] + data[4]) / 2)
                result.player_room_id = miniMapUtil.compute_room_id(x, y)
                logger.info(f"{data[0]}_room_id:{result.player_room_id}")
                # 注意：房间信息地图仍然需要更新context
                if result.player_room_id:
                    x, y = result.player_room_id
                    context.room_info_map[x][y] = 0
            if data[0] == "map_boss":
                x = int((data[1] + data[3]) / 2)
                y = int((data[2] + data[4]) / 2)
                result.boss_room_id = miniMapUtil.compute_room_id(x, y)
                logger.info(f"{data[0]}_room_id:{result.boss_room_id}")
                # 注意：房间信息地图仍然需要更新context
                if result.boss_room_id:
                    x, y = result.boss_room_id
                    context.room_info_map[x][y] = 0
            if data[0].startswith("map_query"):
                x = int((data[1] + data[3]) / 2)
                y = int((data[2] + data[4]) / 2)
                xy = miniMapUtil.compute_room_id(x, y)
                logger.info(f"{data[0]}_room_id:{xy}")
                query_room_id_list.append(xy)
            if data[0] == "map_elite":
                x = int((data[1] + data[3]) / 2)
                y = int((data[2] + data[4]) / 2)
                # 计算房间位置
                xy = miniMapUtil.compute_room_id(x, y)
                logger.info(f"{data[0]}_room_id:{xy}")
                elite_room_id_list.append(xy)
            if data[0] == "map_special":
                x = int((data[1] + data[3]) / 2)
                y = int((data[2] + data[4]) / 2)
                # 计算房间位置
                result.special_room_id = miniMapUtil.compute_room_id(x, y)
                logger.info(f"{data[0]}_room_id:{result.special_room_id}")
                elite_room_id_list.append(result.special_room_id)

        # 针对特定地图的特殊处理
        if context.player.map_name == "德洛斯矿山外围" and result.player_room_id == (1, 4):
            logger.info("矿山这里向上")
            query_room_id_list.append((0, 4))
        if context.player.map_name == "德洛斯矿山外围" and result.player_room_id == (1, 5):
            logger.info("矿山这里向左")
            query_room_id_list.append((1, 4))
        
        # 如果问号房间和boss房间不为空，找到最接近boss房间的问号房间
        if query_room_id_list and result.boss_room_id:
            if context.player.map_name == "德洛斯矿山外围" and len(query_room_id_list) > 1:
                result.query_room_id = max(query_room_id_list, key=lambda x: x[0])
            else:
                # 初始化最小距离为无穷大，以及最近的坐标
                min_distance = float('inf')
                # 遍历坐标列表
                for coord in query_room_id_list:
                    # 计算当前坐标与target的距离的平方（避免使用sqrt以提高效率）
                    distance_squared = (coord[0] - result.player_room_id[0]) ** 2 + (coord[1] - result.player_room_id[1]) ** 2
                    # 如果当前距离的平方小于已知的最小距离的平方，则更新最小距离和最近的坐标
                    if distance_squared < min_distance:
                        min_distance = distance_squared
                        result.query_room_id = coord
                        screen_out.append(coord)
        
        # 如果精英房间和人物房间不为空，找到最接近人物房间的精英房间
        if elite_room_id_list and result.player_room_id:
            logger.info(f"精英房间和人物房间不为空,elite_room_id_list:{elite_room_id_list}")
            # 初始化最小距离为无穷大，以及最近的坐标
            min_distance = float('inf')
            # 遍历坐标列表
            for coord in elite_room_id_list:
                # 计算当前坐标与target的距离的平方（避免使用sqrt以提高效率）
                distance_squared = (coord[0] - result.player_room_id[0]) ** 2 + (coord[1] - result.player_room_id[1]) ** 2
                # 如果当前距离的平方小于已知的最小距离的平方，则更新最小距离和最近的坐标
                if distance_squared < min_distance:
                    min_distance = distance_squared
                    if min_distance == 1:
                        result.elite_room_id = coord
                        screen_out.append(coord)
                        logger.info(f"筛选出精英房间：{coord}")
        
        # 针对流雨瀑布地图的特殊处理
        if context.player.map_name == "流雨瀑布":
            # 如果精英房间和人物房间不为空，找到最接近人物房间的精英房间
            if screen_out and result.boss_room_id:
                logger.info(f"精英房间或问号房间不为空:{screen_out},取最接近boss房的房间设置为问号房间，因为问号房间优先")
                # 初始化最小距离为无穷大，以及最近的坐标
                min_distance = float('inf')
                # 遍历坐标列表
                for coord in screen_out:
                    # 计算当前坐标与target的距离的平方（避免使用sqrt以提高效率）
                    distance_squared = (coord[0] - result.boss_room_id[0]) ** 2 + (coord[1] - result.boss_room_id[1]) ** 2
                    # 如果当前距离的平方小于已知的最小距离的平方，则更新最小距离和最近的坐标
                    if distance_squared < min_distance:
                        min_distance = distance_squared
                        result.query_room_id = coord
                        logger.info(f"取最接近boss房的房间设置为问号房间：{coord}")
        
        # 当无法获取玩家房间ID时的特殊处理
        if result.player_room_id is None and result.boss_room_id and result.special_room_id:
            priority_direction = 'right'
            # 查找终点房间的路径
            end_direction = context.a_star(context.room_info_map, result.special_room_id, result.boss_room_id, priority_direction)
            if end_direction is not None:
                logger.info(f"special_room_id到boss_room_id路径:{end_direction}")
                logger.info(f"获取不到玩家所在房间时，特殊房间到boss房间路径能走通，玩家应该在boss房，不做特殊处理")
            else:
                result.player_room_id = result.special_room_id
                logger.info(f"获取不到玩家所在房间时，特殊房间到boss房间路径走不通，则玩家当前在特殊房间{result.player_room_id}")
                if elite_room_id_list and result.player_room_id:
                    logger.info(f"精英房间和人物房间不为空,elite_room_id_list:{elite_room_id_list}")
                    # 初始化最小距离为无穷大，以及最近的坐标
                    min_distance = float('inf')
                    # 遍历坐标列表
                    for coord in elite_room_id_list:
                        # 计算当前坐标与target的距离的平方（避免使用sqrt以提高效率）
                        distance_squared = (coord[0] - result.player_room_id[0]) ** 2 + (coord[1] - result.player_room_id[1]) ** 2
                        # 如果当前距离的平方小于已知的最小距离的平方，则更新最小距离和最近的坐标
                        if distance_squared < min_distance:
                            min_distance = distance_squared
                            if min_distance == 1:
                                result.elite_room_id = coord
                                screen_out.append(coord)
                                logger.info(f"筛选出精英房间：{coord}")
        
        return result
    
    def min_map_apply_to_context(self, context, result):
        """
        将MinMapProcessResult应用到上下文对象
        
        Args:
            context: 上下文对象
            result: MinMapProcessResult对象
        """
        # 更新房间信息
        context.player.player_room_id = result.player_room_id
        context.query_room_id = result.query_room_id
        context.elite_room_id = result.elite_room_id
        context.boss_room_id = result.boss_room_id
        context.special_room_id = result.special_room_id

# 注意：不再提供全局实例，请在需要的地方创建YoloHandler实例