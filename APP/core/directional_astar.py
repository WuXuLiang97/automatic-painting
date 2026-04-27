import heapq


class Node:
    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position
        self.g = 0  # 从起点到该节点的代价
        self.h = 0  # 从该节点到终点的启发式代价
        self.f = 0  # 总代价

    def __eq__(self, other):
        return self.position == other.position

    def __hash__(self):
        return hash(self.position)

    def __lt__(self, other):
        return self.f < other.f


def heuristic(a, b):
    """曼哈顿距离作为启发式函数"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_neighbors(position, maze, priority):
    """根据优先级获取邻居节点的方向"""
    x, y = position
    directions = {
        "right": [(0, 1), (1, 0), (0, -1), (-1, 0)],
        "down": [(1, 0), (0, 1), (0, -1), (-1, 0)],
        "up": [(-1, 0), (0, -1), (0, 1), (1, 0)],
        "left": [(0, -1), (-1, 0), (0, 1), (1, 0)],
        "rightDown": [(1, 1), (0, 1), (1, 0), (0, -1), (-1, 0), (-1, -1)],
        "default": [(0, 1), (1, 0), (0, -1), (-1, 0)]
    }

    valid_directions = directions.get(priority, directions["default"])
    neighbors = [(x + d[0], y + d[1]) for d in valid_directions]

    valid_neighbors = []
    for nx, ny in neighbors:
        if 0 <= nx < len(maze) and 0 <= ny < len(maze[0]) and maze[nx][ny] == 0:
            valid_neighbors.append((nx, ny))

    return valid_neighbors


def a_star(maze, start, end, priority):
    """A* 寻路算法"""
    start_node = Node(None, tuple(start))
    end_node = Node(None, tuple(end))
    open_list = []
    closed_list = set()

    heapq.heappush(open_list, (start_node.f, start_node))

    while open_list:
        _, current_node = heapq.heappop(open_list)
        closed_list.add(current_node)

        if current_node == end_node:
            path = []
            while current_node:
                path.append(current_node.position)
                current_node = current_node.parent
            return path[::-1]  # 返回反转后的路径

        (x, y) = current_node.position

        # 获取邻居节点，根据优先级顺序
        neighbors = get_neighbors(current_node.position, maze, priority)

        for next in neighbors:
            neighbor = Node(current_node, next)

            if neighbor in closed_list:
                continue

            neighbor.g = current_node.g + 1
            neighbor.h = heuristic(neighbor.position, end_node.position)
            neighbor.f = neighbor.g + neighbor.h

            if add_to_open(open_list, neighbor):
                heapq.heappush(open_list, (neighbor.f, neighbor))


def add_to_open(open_list, neighbor):
    for index, item in enumerate(open_list):
        if neighbor == item[1] and neighbor.g > item[1].g:
            return False
    return True


def judge_direction(starting_point, end_point):
    x1, y1 = starting_point
    x2, y2 = end_point
    if x2 > x1:
        return "down"
    elif x2 < x1:
        return "up"
    elif y2 > y1:
        # 假设y增加时向下移动（网格的直观理解）
        return "right"
    else:  # y2 < y1
        return "left"


if __name__ == '__main__':
    # 创建地图数据
    海伯伦的预言所2 = [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 1, 1, 1]
    ]

    # 定义起点和终点
    起点2 = (4, 1)
    终点2 = (1, 4)

    # 创建地图数据
    海伯伦的预言所 = [
        [1, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1]
    ]
    # 定义起点和终点
    起点 = (1, 0)
    终点 = (0, 6)

    # 定义优先方向
    优先方向 = "right"  # 可以是 "right", "down", "up", "left", "rightDown"
    yc = [[1, 1, 0, 0, 0, 1],
          [1, 0, 0, 0, 0, 1],
          [1, 0, 0, 0, 0, 0], ]
    # 调用 A* 算法
    map_path = a_star(yc, (1, 4), (2, 5), 优先方向)
    print(map_path)
    # print(map_path[0][0], map_path[0][1], map_path[1][0], map_path[1][1])
    print(judge_direction(map_path[0], map_path[1]))
