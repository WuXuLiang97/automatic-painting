import heapq

class Node:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.g = 0
        self.h = 0
        self.f = 0
        self.parent = None
        self.is_processed = False

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __lt__(self, other):
        return self.f < other.f

    def __repr__(self):  # 用于日志输出节点信息
        return f"Node({self.x},{self.y}, g={self.g}, h={self.h}, f={self.f}, processed={self.is_processed})"


def manhattan_distance(node, end):
    return abs(node.x - end.x) + abs(node.y - end.y)


def get_neighbors(node, map_data, unlocked):
    neighbors = []
    rows = len(map_data)
    cols = len(map_data[0])
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # 上下左右

    for dx, dy in directions:
        x = node.x + dx
        y = node.y + dy
        if 0 <= x < rows and 0 <= y < cols and unlocked[x][y]:
            neighbors.append(Node(x, y))
    return neighbors


def process_room(node, map_data, unlocked):
    rows = len(map_data)
    cols = len(map_data[0])
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    unlocked_before = [row.copy() for row in unlocked]  # 记录处理前的解锁状态

    for dx, dy in directions:
        x = node.x + dx
        y = node.y + dy
        if 0 <= x < rows and 0 <= y < cols:
            if map_data[x][y] == 1 and not unlocked[x][y]:
                unlocked[x][y] = True  # 解锁相邻房间

    # 输出解锁变化
    unlocked_new = []
    for i in range(rows):
        for j in range(cols):
            if unlocked[i][j] and not unlocked_before[i][j]:
                unlocked_new.append((i, j))
    if unlocked_new:
        print(f"  处理房间({node.x},{node.y})后，解锁了新房间：{unlocked_new}")
    else:
        print(f"  处理房间({node.x},{node.y})后，无新房间可解锁")
    node.is_processed = True


def print_unlocked(unlocked):
    """打印当前解锁状态矩阵（T=已解锁，F=未解锁）"""
    print("  当前解锁状态：")
    for row in unlocked:
        print("  " + " ".join(["T" if c else "F" for c in row]))


def a_star_search(map_data, start, end):
    rows = len(map_data)
    cols = len(map_data[0])
    unlocked = [[False for _ in range(cols)] for _ in range(rows)]
    for i in range(rows):
        for j in range(cols):
            if map_data[i][j] == 0:
                unlocked[i][j] = True  # 初始已解锁房间：(0,0)、(1,0)、(2,6)
    print("初始解锁房间：" + str([(i,j) for i in range(rows) for j in range(cols) if unlocked[i][j]]))
    print_unlocked(unlocked)

    start_node = Node(start[0], start[1])
    end_node = Node(end[0], end[1])
    print(f"\n起点：{start}，终点：{end}")

    open_heap = []
    closed_list = []
    heapq.heappush(open_heap, start_node)
    print(f"初始开放列表：{open_heap}")

    step = 0  # 记录算法迭代步骤
    while open_heap:
        step += 1
        print(f"\n===== 迭代步骤 {step} =====")
        current_node = heapq.heappop(open_heap)
        print(f"弹出开放列表中f值最小的节点：{current_node}")

        # 检查是否到达终点
        if current_node == end_node:
            print(f"已到达终点({end_node.x},{end_node.y})，开始回溯路径...")
            path = []
            while current_node:
                path.append((current_node.x, current_node.y))
                current_node = current_node.parent
            return path[::-1]

        # 将当前节点加入闭合列表
        closed_list.append(current_node)
        print(f"闭合列表新增节点：{current_node}，当前闭合列表：{closed_list}")

        # 处理当前房间（若未处理）
        if not current_node.is_processed:
            print(f"处理未打怪的房间({current_node.x},{current_node.y})，增加打怪代价3")
            current_node.g += 3  # 打怪代价
            process_room(current_node, map_data, unlocked)  # 解锁相邻房间
            print_unlocked(unlocked)  # 打印解锁状态变化

        # 获取邻居节点
        neighbors = get_neighbors(current_node, map_data, unlocked)
        print(f"当前节点({current_node.x},{current_node.y})的邻居（已解锁房间）：{neighbors}")

        for neighbor in neighbors:
            # 跳过已在闭合列表的邻居
            if neighbor in closed_list:
                print(f"  邻居{neighbor}已在闭合列表，跳过")
                continue

            # 计算邻居代价
            neighbor.g = current_node.g + 1  # 移动代价1
            neighbor.h = manhattan_distance(neighbor, end_node)
            neighbor.f = neighbor.g + neighbor.h
            neighbor.parent = current_node
            print(f"  计算邻居{neighbor}的代价：g={neighbor.g}, h={neighbor.h}, f={neighbor.f}")

            # 加入开放列表（若不在列表中）
            if neighbor not in open_heap:
                heapq.heappush(open_heap, neighbor)
                print(f"  将邻居{neighbor}加入开放列表，当前开放列表：{open_heap}")
            else:
                print(f"  邻居{neighbor}已在开放列表，不重复加入")

    return None


if __name__ == "__main__":
    map_data = [
        [0, 1, 1, 1, 1, 1, 1],
        [0, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 0]
    ]
    start = (0, 0)
    end = (2, 6)

    path = a_star_search(map_data, start, end)

    if path:
        print("\n===== 最终路径 =====")
        for step, (x, y) in enumerate(path):
            print(f"步骤{step}：({x}, {y})")
    else:
        print("\n无法找到路径")