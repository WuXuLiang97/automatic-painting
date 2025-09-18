from typing import Tuple, Optional, List, Dict

import cv2
import numpy as np

from utils import img_util as iu
from root_dir import root_path

SmallRoom = Tuple[int, int]

# 移动方向配置（按上、右、下、左顺序）
DIRECTIONS = ("up", "right", "down", "left")
# 小地图角色和透明掩码

SMALL_HERO_TEMPLATE, SMALL_HERO_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/small_hero.png")
# 领主和角色模板
SMALL_BOSS_TEMPLATE, SMALL_BOSS_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/small_boss.png")

# 小地图问号模板
SMALL_WEN1_TEMPLATE, SMALL_WEN1_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/small_wen1.png"
)


# 地图配置
MAP_CONFIG = {
    "幻境前殿": {
        "1阶": {
            "角色坐标": (6, 22),
            "领主坐标": (55, 20),
            "步进像素": 18,
            "地图大小": (4, 3),
            "过图顺序": ((2, 1), (2, 2), (3, 2), (2, 2), (2, 3), (1, 3), (2, 3), (2, 4))
        }
    },
    "残月宫阙": {
        "1阶": {
            "角色坐标": (6, 22),
            "领主坐标": (55, 20),
            "步进像素": 18,
            "地图大小": (4, 3),
            "过图顺序": ((2, 1), (2, 2), (3, 2), (2, 2), (2, 3), (2, 2), (1, 2), (1, 3), (1, 4), (2, 4))
        }
    },
    "未央之脊": {
        "1阶": {
            "角色坐标": (6, 22),
            "领主坐标": (73, 20),
            "步进像素": 18,
            "地图大小": (5, 3),
            "过图顺序": ((2, 1), (2, 2), (2, 3), (2, 4), (1, 4), (2, 4), (2, 5))
        }
    },
    "沧海竹林": {
        "1阶": {
            "角色坐标": (6, 22),
            "领主坐标": (55, 20),
            "步进像素": 18,
            "地图大小": (4, 3),
            "过图顺序": ((2, 1), (2, 2), (1, 2), (1, 3), (2, 3), (3, 3), (2, 3), (2, 4))
        }
    }
}
def calculate_direction(current_pos: Tuple[int, int], next_pos: Tuple[int, int]) -> str:
    """
    计算从当前位置到下一个位置的移动方向

    :param current_pos: (Tuple[int, int]): 当前房间坐标 (row, col)
    :param next_pos: (Tuple[int, int]): 下一个房间坐标 (row, col)
    :return: (str): 移动方向字符串 (如 "Up", "Right", "Down", "Left")
    :raises ValueError: 如果两个房间不相邻或方向无法确定
    """
    current_row, current_col = current_pos
    next_row, next_col = next_pos

    # 计算行和列的差值
    row_diff = next_row - current_row
    col_diff = next_col - current_col

    # 检查是否为相邻房间（只能在一个方向上移动1格）
    if abs(row_diff) + abs(col_diff) != 1:
        raise ValueError(f"房间 {current_pos} 和 {next_pos} 不相邻，无法计算移动方向")

    # 根据差值确定方向
    if row_diff == -1 and col_diff == 0:
        return DIRECTIONS[0]  # "Up"
    elif row_diff == 0 and col_diff == 1:
        return DIRECTIONS[1]  # "Right"
    elif row_diff == 1 and col_diff == 0:
        return DIRECTIONS[2]  # "Down"
    elif row_diff == 0 and col_diff == -1:
        return DIRECTIONS[3]  # "Left"
    else:
        raise ValueError(f"无法确定从 {current_pos} 到 {next_pos} 的移动方向")


class SmallMapManager:
    """
    小地图管理类，用于缓存和管理小地图相关的计算结果
    """

    def __init__(self, map_info: dict, true_position: Tuple[int, int]):
        """
        初始化小地图管理器

        :param map_info: (dict): 地图配置信息，包含步进像素、地图大小、过图顺序等参数
        :param true_position: (Tuple[int, int]): 小地图在完整原图中的左上角绝对坐标
        """
        # 地图名称
        self.dungeon_name: str | None = None
        self.dungeon_level: str | None = None

        # 从配置中获取并缓存基本参数
        self.step_pixels = map_info.get("步进像素")  # 每个房间的像素大小
        self.map_size = map_info.get("地图大小")  # (列数, 行数)
        self.path_order = map_info.get("过图顺序")  # 过图顺序

        # 计算并缓存小地图总尺寸
        self.map_width = self.map_size[0] * self.step_pixels  # 总宽度
        self.map_height = self.map_size[1] * self.step_pixels  # 总高度
        # 缓存小地图的真实坐标，相对于原图，便于以后来新图时截图用
        self.true_position = true_position

        # 初始化路径导航系统
        self._init_path_navigation(map_info.get("过图顺序", ()))

        print(f"SmallMapManager 初始化完成:")
        print(f"  步进像素: {self.step_pixels}")
        print(f"  地图大小: {self.map_size} (列数, 行数)")
        print(f"  计算出的小地图尺寸: 宽度={self.map_width}, 高度={self.map_height}")
        print(f"  路径节点数量: {len(self.path_sequence)}")
        print(f"  路径映射表大小: {len(self.next_rooms_map)}")

    def _init_path_navigation(self, path_sequence: Tuple[Tuple[int, int], ...]):
        """
        初始化路径导航系统，构建高效的查找数据结构

        :param path_sequence: (Tuple[Tuple[int, int], ...]): 过图顺序的元组序列，每个元素是(行, 列)坐标
        """
        self.path_sequence = path_sequence
        self.next_rooms_map: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
        self.valid_positions = set(path_sequence)

        # 构建位置到下一步的映射关系
        for i in range(len(path_sequence) - 1):
            current_pos = path_sequence[i]
            next_pos = path_sequence[i + 1]

            # 如果当前位置还没有在映射表中，创建一个空列表
            if current_pos not in self.next_rooms_map:
                self.next_rooms_map[current_pos] = []

            # 避免重复添加相同的下一步位置
            if next_pos not in self.next_rooms_map[current_pos]:
                self.next_rooms_map[current_pos].append(next_pos)

        # 处理终点位置（没有下一步的位置）
        if path_sequence:
            last_pos = path_sequence[-1]
            if last_pos not in self.next_rooms_map:
                self.next_rooms_map[last_pos] = []

    def get_current_room(self, small_map_img) -> Tuple[int, int] | None:
        """
        查找当前所处房间的坐标（行，列）
        :param small_map_img: (np.ndarray): 小地图图片
        :return: (Tuple[int, int]): 当前房间的坐标（行，列）,当图像中找不到当前英雄坐标，返回None
        """
        template, mask = SMALL_HERO_TEMPLATE, SMALL_HERO_TEMPLATE_MASK
        # 在小地图中进行模板匹配，找small_hero的坐标，这里找到的是左上角坐标
        confidence, small_hero_pos = iu.find_template_with_mask(small_map_img, template, mask)

        # 如果置信度小于0.8，再找一下boss模板
        if confidence < 0.8:
            template, mask = SMALL_BOSS_TEMPLATE, SMALL_BOSS_TEMPLATE_MASK
            confidence, small_hero_pos = iu.find_template_with_mask(small_map_img, template, mask)

            if confidence < 0.8:
                print("当前画面没有找到英雄、boss模板，可能已经结束了，直接返回空")
                return None
                # raise Exception(f"当前画面没有找到英雄、boss模板")
            else:
                # 如果找不到英雄，只找到了boss，说明已经到了领主房，按照原逻辑计算
                pass

        # 计算中心像素坐标
        # # 左上角坐标，加上模板边长的一半
        center_x = small_hero_pos[0] + template.shape[1] // 2
        center_y = small_hero_pos[1] + template.shape[0] // 2
        # 计算所处房间位置坐标（行，列）
        row, col = self.get_room_position(center_x, center_y)

        return row, col

    def get_next_rooms(self, current_room: Tuple[int, int]) -> List[Tuple[Tuple[int, int], str]]:
        """
        根据当前房间坐标获取下一个可到达房间的坐标和移动方向列表

        :param current_room: (Tuple[int, int]): 当前房间的坐标（行,列）
        :return: (List[Tuple[Tuple[int, int], str]]): 包含房间坐标和移动方向的元组列表。
                                                     格式：[((row, col), "direction"), ...]
                                                     如果是终点则返回空列表。
        :raises ValueError: 当前坐标不在有效路径中时抛出异常
        """
        current_pos = (current_room[0], current_room[1])

        # 验证当前位置是否在有效路径中
        if current_pos not in self.valid_positions:
            raise ValueError(f"当前坐标 {current_pos} 不在有效的过图路径中。"
                             f"有效坐标包括: {sorted(self.valid_positions)}")

        # 获取下一步可到达的房间坐标列表
        next_positions = self.next_rooms_map.get(current_pos, [])

        # 如果是终点，返回空列表
        if not next_positions:
            return []

        # 计算每个下一步位置的移动方向
        result = []
        for next_pos in next_positions:
            try:
                direction = calculate_direction(current_pos, next_pos)
                result.append((next_pos, direction))
            except ValueError as e:
                # 重新抛出异常，包含更多上下文信息
                raise ValueError(f"计算从 {current_pos} 的移动方向时出错: {str(e)}")

        return result

    def get_next_rooms_simple(self, current_room: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        根据当前房间坐标获取下一个可到达房间的坐标列表（向后兼容方法）

        :param current_room: (Tuple[int, int]): 当前房间的坐标（行,列）
        :return: (List[Tuple[int, int]]): 下一个可到达房间的坐标列表。如果是终点则返回空列表。
        :raises ValueError: 当前坐标不在有效路径中时抛出异常
        """
        current_pos = (current_room[0], current_room[1])

        # 验证当前位置是否在有效路径中
        if current_pos not in self.valid_positions:
            raise ValueError(f"当前坐标 {current_pos} 不在有效的过图路径中。"
                             f"有效坐标包括: {sorted(self.valid_positions)}")

        # 返回下一步可到达的房间列表（可能为空，表示已到达终点）
        return self.next_rooms_map.get(current_pos, []).copy()

    def is_valid_path_position(self, x: int, y: int) -> bool:
        """
        检查给定坐标是否在有效的过图路径中

        :param x: (int): 房间的X坐标（行）
        :param y: (int): 房间的Y坐标（列）
        :return: (bool): 如果坐标在有效路径中返回True，否则返回False
        """
        return (x, y) in self.valid_positions

    def get_path_info(self) -> Dict:
        """
        获取路径信息的详细统计

        :return: (Dict): 包含路径统计信息的字典，例如总节点数、分支点、终点等
        """
        branch_points = []  # 有多个下一步选择的分支点
        dead_ends = []  # 没有下一步的终点

        for pos, next_positions in self.next_rooms_map.items():
            if len(next_positions) > 1:
                branch_points.append(pos)
            elif len(next_positions) == 0:
                dead_ends.append(pos)

        return {
            "总节点数": len(self.valid_positions),
            "路径序列长度": len(self.path_sequence),
            "分支点": branch_points,
            "终点": dead_ends,
            "完整路径": self.path_sequence
        }

    def get_room_position(self, x, y) -> Optional[Tuple[int, int]]:
        """
        将小地图中的像素坐标转换为房间位置

        :param x: (int): 在截取后的小地图图像中的X坐标（相对于小地图左上角）
        :param y: (int): 在截取后的小地图图像中的Y坐标（相对于小地图左上角）
        :return: (Optional[Tuple[int, int]]): (row, col) 表示第几行第几列（从1开始计数），如果超出范围返回 None
        """
        # 边界检查
        if x < 0 or y < 0 or x >= self.map_width or y >= self.map_height:
            return None

        # 计算房间位置（从1开始计数）
        col = (x // self.step_pixels) + 1
        row = (y // self.step_pixels) + 1

        # 再次检查计算结果是否在有效范围内
        if col > self.map_size[0] or row > self.map_size[1]:
            return None

        return row, col

    def get_room_center_coordinates(self, row, col) -> Optional[Tuple[int, int]]:
        """
        根据房间位置计算房间中心的像素坐标

        :param row: (int): 房间行号（从1开始）
        :param col: (int): 房间列号（从1开始）
        :return: (Optional[Tuple[int, int]]): (x, y) 房间中心的像素坐标，如果房间位置无效返回 None
        """
        # 检查房间位置是否有效
        if row < 1 or col < 1 or row > self.map_size[1] or col > self.map_size[0]:
            return None

        # 计算房间中心坐标
        center_x = (col - 1) * self.step_pixels + self.step_pixels // 2
        center_y = (row - 1) * self.step_pixels + self.step_pixels // 2

        return center_x, center_y

    def is_valid_position(self, x: int, y: int) -> bool:
        """
        检查给定的像素坐标是否在小地图有效范围内

        :param x: (int): X坐标
        :param y: (int): Y坐标
        :return: (bool): 如果坐标在有效范围内返回 True，否则返回 False
        """
        return 0 <= x < self.map_width and 0 <= y < self.map_height

    def is_room_open(self, small_map_img: np.ndarray, current_room: Tuple[int, int],
                     threshold: float = 0.8) -> bool:
        """
        判断房间是否开放中（即是否能检测到问号模板）

        :param small_map_img: (np.ndarray): 小地图图片数组
        :param current_room: Tuple[int]: 房间坐标（行，列）
        :param threshold: (float): 置信度阈值，默认0.8
        :return: (bool): 当匹配置信度大于等于阈值时返回True，否则返回False
        :raises ValueError: 当房间坐标无效时抛出异常
        """
        # 验证房间坐标是否有效
        # 传入图片像素必须和缓存像素一致
        row, col = current_room
        height, width = small_map_img.shape[:2]
        if not self.map_height == height or not self.map_width == width:
            raise ValueError("传入图片像素必须和缓存像素一致")
        # 传入坐标必须在房间数内

        if row < 1 or col < 1 or row > self.map_size[1] or col > self.map_size[0]:
            raise ValueError(
                f"房间坐标 ({row}, {col}) 无效。有效范围: 行[1-{self.map_size[1]}], 列[1-{self.map_size[0]}]")

        # 计算传入坐标的像素左上角
        # 比如，（2，1），应该是0+1*步进，0+0*步进，加1是因为这里实际上计算的是当前格右下角坐标，所以要加1
        x = (col - 1) * self.step_pixels
        y = (row - 1) * self.step_pixels

        wh = iu.crop_image_wh(small_map_img, (x, y, self.step_pixels, self.step_pixels))
        print(f"x:{x},y:{y}")
        # iu.show0(wh)
        # cv2.imwrite(r"E:\WorkSpace\yolov8-dnf\src\common\resources\template\small_map_img.png", small_map_img)
        # cv2.imwrite(r"E:\WorkSpace\yolov8-dnf\src\common\resources\template\wh.png", wh)
        # iu.end()
        is_match = iu.match_template_with_mask(wh, SMALL_WEN1_TEMPLATE,
                                               SMALL_WEN1_TEMPLATE_MASK, threshold=threshold)

        return is_match

    def crop_small_map(self, img: np.ndarray) -> np.ndarray:
        """
        从完整的游戏画面中，截取小地图画面

        :param img: (np.ndarray): 完整画面截图
        :return: (np.ndarray): 截取下的小地图画面
        """
        return iu.crop_image_wh(img, (self.true_position[0], self.true_position[1],
                                      self.map_width, self.map_height))


def create_manager(img: np.ndarray, dungeon_name: str, dungeon_level: str) -> SmallMapManager:
    """
    通过在屏幕截图中定位角色图标，计算出小地图的准确位置，并创建SmallMapManager实例

    :param img: (np.ndarray): 完整的屏幕截图
    :param dungeon_name: (str):  当前副本名称，比如“幻境前殿”
    :param dungeon_level: (str): 当前副本阶段，比如“1阶”
    :return: (SmallMapManager): 初始化完成的SmallMapManager实例
    """
    map_info = MAP_CONFIG[dungeon_name][dungeon_level]

    # boss_xy 是相对小地图0点坐标的相对坐标
    boss_xy = map_info.get("领主坐标")

    # 先截取一小块区域，大概确定一下小地图位置，不用很精确
    region = (800, 20, 160, 100)
    map_area = iu.crop_image_wh(img, region)

    # best_match_loc 是boss图标在刚才预截图区域内中的左上角坐标
    confidence, best_match_loc = iu.find_template_with_mask(
        map_area, SMALL_BOSS_TEMPLATE, SMALL_BOSS_TEMPLATE_MASK)

    # ==================== 计算小地图的0点坐标 ====================

    # best_match_loc 是元组 (x, y)，boss_xy 也是 (x, y)
    # 小地图在预截取区域内的0点X坐标 = 角色在预截取区域内的X坐标 - 角色图标相对于小地图0点的X坐标
    origin_x_in_crop = best_match_loc[0] - boss_xy[0]
    # 小地图在预截取区域内的0点Y坐标 = 角色在预截取区域内的Y坐标 - 角色图标相对于小地图0点的Y坐标
    origin_y_in_crop = best_match_loc[1] - boss_xy[1]

    # 小地图在完整原图中的绝对坐标 = 预截取区域的原图坐标 + 小地图在预截取区域内的坐标
    true_origin_x = origin_x_in_crop + region[0]
    true_origin_y = origin_y_in_crop + region[1]

    # 创建 SmallMapManager 实例
    manager = SmallMapManager(map_info, (true_origin_x, true_origin_y))
    manager.dungeon_name = dungeon_name
    manager.dungeon_level = dungeon_level
    return manager
    # =============================================================


def find_small_map_area(small_map_img: np.ndarray, color_bounds: Tuple[np.ndarray, np.ndarray]) -> Optional[
    Tuple[int, int, int, int]]:
    """
    在一个已经裁剪好的图像中通过颜色检测定位小地图区域。
    注意：此函数会直接在传入的 `screen_crop` 图像上绘制轮廓用于调试，如果后续需要使用原始图像，请提前复制。

    :param small_map_img: (np.ndarray): 已经裁剪过的，期望包含小地图的图像区域。此图像不应为空。
    :param color_bounds: (Tuple[np.ndarray, np.ndarray]): 颜色范围的下界和上界(HSV格式)。
    :return: (Optional[Tuple[int, int, int, int]]): 如果找到小地图，则返回其在 `screen_crop` 图像中的
                                                  坐标 (x, y, width, height)；否则返回 None。
    """
    # 处理图像以检测颜色区域
    mask_processed = iu.process_image_for_color_detection(small_map_img, color_bounds)

    # 查找并筛选轮廓
    contours, _ = cv2.findContours(
        mask_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    best_contour = None
    max_area = 0
    # 筛选条件：例如，面积要足够大
    min_area_threshold = 1000
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > min_area_threshold:
            if area > max_area:
                max_area = area
                best_contour = cnt

    # 获取包围矩并返回坐标
    if best_contour is not None:
        x, y, w, h = cv2.boundingRect(best_contour)

        # 在裁剪图上绘制矩形以供可视化验证
        cv2.rectangle(small_map_img, (x, y), (x + w, y + h), (0, 255, 0), 3)

        # 返回在裁剪图像坐标系中的坐标
        return x, y, w, h

    # 如果没有找到符合条件的轮廓，返回None
    cv2.destroyAllWindows()
    return None


def is_door_open(small_map_img: np.ndarray) -> bool:
    """
    判断当前是否是开门状态（通过在小地图中寻找问号图标）

    :param small_map_img: (np.ndarray): 小地图图片
    :return: (bool): True表示开门，False表示关门
    """
    # 截取小地图
    # 从小地图中找问号模板，要求置信度大于80%
    flag = iu.match_template_with_mask(small_map_img, SMALL_WEN1_TEMPLATE,
                                       SMALL_WEN1_TEMPLATE_MASK)

    # 如果有问号，那就是开门了
    return flag


if __name__ == '__main__':
    # 读取原始屏幕截图
    full_screen_img = cv2.imread(r'/resources/dnf3_xy.png')

    if full_screen_img is None:
        print("错误：无法读取图像，请检查文件路径。")
    else:
        # 1. 定义你想要搜索小地图的自定义区域
        h, w, _ = full_screen_img.shape
        # 定义裁剪区域：(x_start, y_start, width, height)
        # custom_crop_region = (49, 26, 211, 100)
        custom_crop_region = (0, 0, 1000, 1000)

        # 2. 首先根据指定区域裁剪图像
        cropped_area = iu.crop_image_wh(full_screen_img, custom_crop_region)
        # cv2.imshow('crop area', cropped_area)
        # cv2.waitKey(0)

        # 3. 在裁剪后的图像中寻找小地图
        # 小地图
        bound1 = ((15, 71, 102), (25, 91, 232))
        lower_bound = np.array(bound1[0])
        upper_bound = np.array(bound1[1])

        # 第一次查找，定位小地图的主体区域
        map_location = find_small_map_area(cropped_area.copy(), (lower_bound, upper_bound))

        # 4. 处理并打印结果
        if not map_location:
            print("在指定的裁剪区域内未能找到小地图。")
        else:
            # 对找到的区域进行微调，去除边框干扰
            true_map_location = (map_location[0] + 3, map_location[1] + 3, map_location[2] - 6, map_location[3] - 6)

            print(f"成功在裁剪区域中检测到小地图。")
            print(f"小地图在裁剪区域内的坐标 true_map_location (x, y, w, h): {true_map_location}")

            # 小地图上面的褐色条
            bound2 = ((0, 60, 41), (21, 120, 74))
            # bound2 = ((6, 60, 38), (39, 104, 62))
            lower_bound2 = np.array(bound2[0])
            upper_bound2 = np.array(bound2[1])

            # 在已定位的小地图主体区域内裁剪，以寻找褐色信息条
            cropped_area2 = iu.crop_image_wh(cropped_area, true_map_location)
            cv2.imshow('map area', cropped_area2)
            cv2.waitKey(0)

            # 第二次查找，定位褐色条
            map_location2 = find_small_map_area(cropped_area2.copy(), (lower_bound2, upper_bound2))
            if not map_location2:
                print("在指定的裁剪区域内未能找到小地图褐色条。")
            else:
                # 对褐色条位置进行微调
                true_map_location2 = (map_location2[0], map_location2[1], map_location2[2], map_location2[3] - 3)
                print(f"成功在裁剪区域中检测到小地图褐色条。")
                print(f"小地图在裁剪区域内的坐标 true_map_location2 (x, y, w, h): {true_map_location2}")

                # 找到了褐色条，要进行计算。褐色条像素减2，认为是单元格大小，计算出原图总共有多少个

    # 等待按键后关闭所有OpenCV窗口
    cv2.destroyAllWindows()
