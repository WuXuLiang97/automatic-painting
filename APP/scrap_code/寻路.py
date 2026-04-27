import heapq
import numpy as np
from collections import defaultdict


class DNFRoom:
    def __init__(self, room_id, grid, room_type='normal'):
        """
        副本房间类

        :param room_id: 房间唯一标识
        :param grid: 房间网格地图(2D数组)
        :param room_type: 房间类型(normal, boss, question, start)
        """
        self.id = room_id
        self.grid = grid
        self.type = room_type
        self.doors = {}  # 门的位置及连接房间: {(x, y): target_room_id}
        self.explored = False  # 是否已探索

    def add_door(self, position, target_room_id):
        """添加门及连接房间"""
        self.doors[position] = target_room_id

    def get_unexplored_doors(self, dungeon):
        """获取未探索的门"""
        unexplored = []
        for door_pos, target_room_id in self.doors.items():
            if not dungeon.rooms[target_room_id].explored:
                unexplored.append(door_pos)
        return unexplored


class DNFDungeon:
    """DNF副本类，管理所有房间及连接关系"""

    def __init__(self):
        self.rooms = {}  # {room_id: DNFRoom}
        self.current_room_id = None
        self.player_position = None
        self.boss_room_id = None
        self.question_room_id = None
        self.room_connections = defaultdict(list)  # 房间连接关系

    def add_room(self, room):
        """添加房间到副本"""
        self.rooms[room.id] = room
        if room.type == 'boss':
            self.boss_room_id = room.id
        elif room.type == 'question':
            self.question_room_id = room.id

    def connect_rooms(self, room_id1, door_pos1, room_id2, door_pos2):
        """连接两个房间"""
        self.rooms[room_id1].add_door(door_pos1, room_id2)
        self.rooms[room_id2].add_door(door_pos2, room_id1)
        self.room_connections[room_id1].append(room_id2)
        self.room_connections[room_id2].append(room_id1)

    def set_current_room(self, room_id, player_position):
        """设置当前房间和玩家位置"""
        self.current_room_id = room_id
        self.player_position = player_position
        self.rooms[room_id].explored = True

    def predict_path_to_target(self, target_room_id):
        """
        预测到目标房间的最可能路径（房间序列）

        :param target_room_id: 目标房间ID
        :return: 预测的房间ID列表，或None（如果无法预测）
        """
        # 如果目标房间已在连接图中，使用BFS查找路径
        if self.current_room_id in self.room_connections and target_room_id in self.room_connections:
            return self.find_room_path(self.current_room_id, target_room_id)

        # 否则使用启发式方法预测
        return self.heuristic_path_prediction(target_room_id)

    def find_room_path(self, start_room_id, end_room_id):
        """在已知连接中查找房间路径（BFS）"""
        queue = [(start_room_id, [start_room_id])]
        visited = set([start_room_id])

        while queue:
            current_id, path = queue.pop(0)
            if current_id == end_room_id:
                return path

            for neighbor in self.room_connections.get(current_id, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def heuristic_path_prediction(self, target_room_id):
        """
        启发式路径预测 - 基于DNF副本常见布局模式
        """
        # 获取目标房间类型
        target_type = self.rooms[target_room_id].type

        # 基于目标类型的预测策略
        if target_type == 'boss':
            # Boss房间通常在副本末端
            return self.predict_end_path()
        elif target_type == 'question':
            # 问号房间通常在分支路径上
            return self.predict_branch_path()
        else:
            # 默认预测直线路径
            return self.predict_straight_path()

    def predict_end_path(self):
        """预测到副本末端的路径"""
        # 简单实现：尝试向远离起点的方向移动
        # 在实际应用中可结合副本类型使用更复杂的预测模型
        current_path = [self.current_room_id]

        # 尝试找到远离当前房间的方向
        for _ in range(5):  # 最多预测5个房间
            last_room = self.rooms[current_path[-1]]
            unexplored_doors = last_room.get_unexplored_doors(self)

            if not unexplored_doors:
                break

            # 选择"最可能"通向末端的门 - 这里简单选择第一个
            next_door = unexplored_doors[0]
            next_room_id = last_room.doors[next_door]
            current_path.append(next_room_id)

        return current_path

    def predict_branch_path(self):
        """预测到分支房间的路径"""
        # 类似上面的实现，但优先选择分支方向
        # 在实际应用中可标记特殊房间类型
        return self.predict_end_path()  # 简化实现

    def predict_straight_path(self):
        """预测直线路径"""
        return self.predict_end_path()  # 简化实现


class DNFNavigator:
    """DNF副本导航器"""

    def __init__(self, dungeon):
        self.dungeon = dungeon
        self.current_path = []  # 当前路径（坐标序列）
        self.room_path = []  # 房间路径（房间ID序列）
        self.current_target_door = None  # 当前目标门位置

    def navigate_to_target(self, target_type='boss'):
        """
        导航到指定目标

        :param target_type: 目标类型(boss/question)
        :return: 下一步动作
        """
        # 确定目标房间
        target_room_id = None
        if target_type == 'boss' and self.dungeon.boss_room_id:
            target_room_id = self.dungeon.boss_room_id
        elif target_type == 'question' and self.dungeon.question_room_id:
            target_room_id = self.dungeon.question_room_id

        # 如果就在目标房间
        if target_room_id == self.dungeon.current_room_id:
            return self.navigate_in_room(target_room_id)

        # 预测到目标房间的路径
        self.room_path = self.dungeon.predict_path_to_target(target_room_id)

        if not self.room_path:
            # 无法预测路径，探索最近未探索的门
            return self.explore_nearest_unexplored_door()

        # 导航到下一个房间的门
        next_room_id = self.room_path[1] if len(self.room_path) > 1 else self.room_path[0]
        door_position = self.get_door_to_room(next_room_id)

        if not door_position:
            return self.explore_nearest_unexplored_door()

        # 导航到门的位置
        self.current_target_door = door_position
        return self.navigate_to_position(door_position)

    def navigate_in_room(self, room_id):
        """在房间内导航到目标位置"""
        room = self.dungeon.rooms[room_id]
        player_pos = self.dungeon.player_position

        # 根据房间类型确定目标位置
        if room.type == 'boss':
            # 寻找Boss位置（通常房间中心）
            target_pos = self.find_boss_position(room)
        elif room.type == 'question':
            # 问号通常在地图特定位置
            target_pos = self.find_question_position(room)
        else:
            # 其他房间，导航到出口
            target_pos = self.find_best_exit(room)

        return self.navigate_to_position(target_pos)

    def get_door_to_room(self, target_room_id):
        """获取通往目标房间的门位置"""
        current_room = self.dungeon.rooms[self.dungeon.current_room_id]
        for door_pos, connected_room_id in current_room.doors.items():
            if connected_room_id == target_room_id:
                return door_pos
        return None

    def explore_nearest_unexplored_door(self):
        """探索最近的未探索门"""
        current_room = self.dungeon.rooms[self.dungeon.current_room_id]
        unexplored_doors = current_room.get_unexplored_doors(self.dungeon)

        if not unexplored_doors:
            # 没有未探索的门，可能是死胡同
            return self.explore_any_door()

        # 找到最近的门
        player_pos = self.dungeon.player_position
        nearest_door = min(unexplored_doors,
                           key=lambda pos: self.calculate_distance(player_pos, pos))

        self.current_target_door = nearest_door
        return self.navigate_to_position(nearest_door)

    def explore_any_door(self):
        """探索任意门（当没有未探索门时）"""
        current_room = self.dungeon.rooms[self.dungeon.current_room_id]
        if not current_room.doors:
            return None  # 没有门，可能是错误状态

        # 选择第一个门
        first_door = next(iter(current_room.doors.keys()))
        self.current_target_door = first_door
        return self.navigate_to_position(first_door)

    def navigate_to_position(self, target_position):
        """导航到指定位置（使用A*算法）"""
        if not self.current_path or self.current_path[-1] != target_position:
            # 需要重新计算路径
            current_room = self.dungeon.rooms[self.dungeon.current_room_id]
            self.current_path = self.a_star_pathfinding(
                self.dungeon.player_position,
                target_position,
                current_room.grid
            )

        if not self.current_path:
            return None  # 无法找到路径

        # 获取下一步位置
        if len(self.current_path) > 1:
            next_pos = self.current_path[1]  # 当前位置是路径的第一个点
        else:
            next_pos = self.current_path[0]

        # 更新当前路径
        self.current_path = self.current_path[1:]

        # 返回移动方向
        return self.get_direction(self.dungeon.player_position, next_pos)

    def a_star_pathfinding(self, start, end, grid):
        """A*寻路算法实现"""
        # 实现代码与之前类似，这里省略详细实现
        # 返回从起点到终点的路径（坐标列表）
        pass

    def get_direction(self, start, end):
        """计算移动方向"""
        dx = end[0] - start[0]
        dy = end[1] - start[1]

        if dx > 0:
            return "right"
        elif dx < 0:
            return "left"
        elif dy > 0:
            return "down"
        elif dy < 0:
            return "up"
        else:
            return None  # 已在目标位置

    def calculate_distance(self, pos1, pos2):
        """计算两点之间的曼哈顿距离"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def find_boss_position(self, room):
        """在Boss房间中找到Boss位置（启发式方法）"""
        # 简单实现：返回房间中心
        rows, cols = len(room.grid), len(room.grid[0])
        return (cols // 2, rows // 2)

    def find_question_position(self, room):
        """在问号房间中找到问号位置（启发式方法）"""
        # 简单实现：返回房间右上角
        rows, cols = len(room.grid), len(room.grid[0])
        return (cols - 2, 1)  # 避开角落

    def find_best_exit(self, room):
        """在普通房间中找到最佳出口"""
        # 如果有未探索的门，优先选择
        unexplored_doors = room.get_unexplored_doors(self.dungeon)
        if unexplored_doors:
            return min(unexplored_doors,
                       key=lambda pos: self.calculate_distance(self.dungeon.player_position, pos))

        # 否则选择任意门
        if room.doors:
            return next(iter(room.doors.keys()))

        # 没有门，返回玩家位置（不应该发生）
        return self.dungeon.player_position


# 使用示例
if __name__ == "__main__":
    # 创建副本
    dungeon = DNFDungeon()

    # 创建房间
    start_room = DNFRoom(1, np.zeros((10, 10)), 'start')
    room2 = DNFRoom(2, np.zeros((10, 10)))
    boss_room = DNFRoom(3, np.zeros((10, 10)), 'boss')

    # 添加房间到副本
    dungeon.add_room(start_room)
    dungeon.add_room(room2)
    dungeon.add_room(boss_room)

    # 连接房间
    dungeon.connect_rooms(1, (9, 5), 2, (0, 5))
    dungeon.connect_rooms(2, (9, 5), 3, (0, 5))

    # 设置当前房间
    dungeon.set_current_room(1, (5, 5))

    print(dungeon.room_connections)

    # 创建导航器
    navigator = DNFNavigator(dungeon)

    # 导航到Boss
    next_action = navigator.navigate_to_target('boss')
    print("下一步动作:", next_action)
