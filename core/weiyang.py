import itertools
import random
import time
from typing import Tuple, List, Optional

import cv2
import numpy as np

from core import small_map, skill
from core.small_map import SmallMapManager, SmallRoom
from utils import img_util as iu
from root_dir import root_path
from utils.cross_control import PYAUTO
from utils.screenshot_util import screenshot_util
from view import key_config_run
MatchResult = Tuple[float, Tuple[int, int]]
Area = Tuple[int, int, int, int]


DIRECTION_UP_TEMPLATE, DIRECTION_UP_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/direction_up.png")
DIRECTION_RIGHT_TEMPLATE, DIRECTION_RIGHT_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/direction_right.png")
DIRECTION_DOWN_TEMPLATE, DIRECTION_DOWN_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/direction_down.png")
DIRECTION_LEFT_TEMPLATE, DIRECTION_LEFT_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/direction_left.png")
FORWARD_TEMPLATE, FORWARD_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/forward.png")
# 定义四个范围，用于匹配“方向”，按顺序是上、右、下、左
DIRECTION_TEMPLATE_AREAS = ((0, 0, 960, 300), (660, 0, 300, 600), (0, 300, 960, 300), (0, 0, 300, 600))
# 移动方向配置（按上、右、下、左顺序）
DIRECTIONS = ("up", "right", "down", "left")
# 异常日志文件夹
LOG_DIR = root_path+"\logs"
# 未央门票
TICKET_1D_TEMPLATE, TICKET_1D_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/1D.png")
TICKET_2D_TEMPLATE, TICKET_2D_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/2D.png")
TICKET_3D_TEMPLATE, TICKET_3D_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/3D.png")
TICKET_4D_TEMPLATE, TICKET_4D_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/4D.png")
TICKET_5D_TEMPLATE, TICKET_5D_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/5D.png")
TICKET_6D_TEMPLATE, TICKET_6D_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/6D.png")
TICKET_ALL = ((TICKET_1D_TEMPLATE, TICKET_1D_TEMPLATE_MASK),
              (TICKET_2D_TEMPLATE, TICKET_2D_TEMPLATE_MASK),
              (TICKET_3D_TEMPLATE, TICKET_3D_TEMPLATE_MASK),
              (TICKET_4D_TEMPLATE, TICKET_4D_TEMPLATE_MASK),
              # (TICKET_5D_TEMPLATE, TICKET_5D_TEMPLATE_MASK),
              # (TICKET_6D_TEMPLATE, TICKET_6D_TEMPLATE_MASK)
              )
# 未央幻境入场
BUTTON_WEIYANGRUCHANG_TEMPLATE, BUTTON_WEIYANGRUCHANG_TEMPLATE_MASK = iu.load_template_with_mask(
    root_path + "/template/未央幻境入场.png")
# 未央幻境入场标题
TITLE_WEIYANGRUCHANG_TEMPLATE = cv2.imdecode(
    np.fromfile(root_path + "/template/未央幻境入场_窗口标题.png", dtype=np.uint8),
    cv2.IMREAD_COLOR)


# 未央地图范围
WEIYANG_MAP_HJQD = cv2.imdecode(
    np.fromfile(root_path + "/template/幻境前殿.png", dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
WEIYANG_MAP_CYGQ = cv2.imdecode(
    np.fromfile(root_path + "/template/残月宫阙.png", dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
WEIYANG_MAP_WYZJ = cv2.imdecode(
    np.fromfile(root_path + "/template/未央之脊.png", dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
WEIYANG_MAP_CHZL = cv2.imdecode(
    np.fromfile(root_path + "/template/沧海竹林.png", dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
def find_unique_match_in_area(matches: List[MatchResult], area: Area) -> Optional[MatchResult]:
    """
    从匹配结果列表中筛选出位于指定区域内的唯一匹配项。

    此函数检查每个匹配项的左上角坐标(x, y)是否落在定义的`area`内部。

    :param matches: `find_all_template_with_mask`返回的匹配结果列表。
                    格式为 [(置信度, (x, y)), ...]
    :param area: 一个元组(x, y, w, h)，定义了搜索的矩形区域。
                 匹配点的左上角坐标(match_x, match_y)必须满足 x <= match_x < x + w 且 y <= match_y < y + h。
    :return: 如果在区域内找到唯一的匹配项，则返回该匹配项 `(置信度, (x, y))`。
             如果在区域内没有找到匹配项，则返回 `None`。
    :raises ValueError: 如果在区域内找到多个（大于1个）匹配项，则引发此异常。
    """
    x, y, w, h = area

    # 使用列表推导式高效地筛选出所有在指定区域内的匹配项
    # match[1] 是坐标元组 (x, y)
    # match[1][0] 是 x, match[1][1] 是 y
    matches_in_area = [
        match for match in matches
        if x <= match[1][0] < x + w and y <= match[1][1] < y + h
    ]

    # 根据筛选后的列表长度进行判断
    if len(matches_in_area) == 0:
        # 情况1: 区域内没有找到任何匹配项
        return None
    elif len(matches_in_area) == 1:
        # 情况2: 区域内找到了唯一的匹配项，正是我们想要的
        return matches_in_area[0]
    else:
        # 情况3: 区域内找到了多个匹配项，根据要求报错
        raise ValueError(
            f"错误：在区域 {area} 内找到了 {len(matches_in_area)} 个匹配项，预期为1个或0个。"
            f" 找到的匹配项为: {matches_in_area}"
        )


def find_unique_match_by_direction(matches: List[MatchResult], direction: int) -> Optional[MatchResult] | None:
    """
    根据指定方向，从匹配结果列表中智能筛选出唯一匹配项。

    此函数根据`direction`参数执行不同的逻辑：
    - 对于左(3)或右(1)方向，它在预定义的侧边区域内查找唯一匹配。
    - 对于上(0)或下(2)方向，它首先排除侧边区域的匹配项，
      然后在剩余的匹配项中根据方向（最上或最下）选择一个。

    :param matches: `find_all_template_with_mask`返回的匹配结果列表。
                    格式为 [(置信度, (x, y)), ...]
    :param direction: 一个整数，定义了搜索方向。
                      0=上, 1=右, 2=下, 3=左。
    :return: 如果找到符合条件的唯一匹配项，则返回该匹配项 `(置信度, (x, y))`。
             如果没有找到匹配项，则返回 `None`。
    :raises ValueError: 如果方向值无效，或者找到的匹配项数量不符合预期（例如，多于一个或需要决策时多于两个）。
    """
    # 1. 验证方向参数
    if direction not in [0, 1, 2, 3]:
        raise ValueError(f"错误：无效的方向值 '{direction}'。只接受 0(上), 1(右), 2(下), 3(左)。")

    # 2. 如果方向是右(1)或左(3)，使用简单的区域筛选逻辑
    if direction in [1, 3]:
        area = DIRECTION_TEMPLATE_AREAS[direction]
        x, y, w, h = area

        matches_in_area = [
            match for match in matches
            if x <= match[1][0] < x + w and y <= match[1][1] < y + h
        ]

        if len(matches_in_area) == 0:
            return None
        elif len(matches_in_area) == 1:
            return matches_in_area[0]
        else:
            raise ValueError(
                f"错误：在方向 '{direction}' 的区域 {area} 内找到了 {len(matches_in_area)} 个匹配项，预期为1个或0个。"
                f" 找到的匹配项为: {matches_in_area}"
            )

    # 3. 如果方向是上(0)或下(2)，执行排除和决策逻辑
    elif direction in [0, 2]:
        # 定义左右侧边区域，用于排除
        # 右侧区域索引为 1, 左侧区域索引为 3
        right_area = DIRECTION_TEMPLATE_AREAS[1]
        left_area = DIRECTION_TEMPLATE_AREAS[3]

        # 辅助函数，用于判断一个点是否在某个区域内
        def is_in_area(point: Tuple[int, int], area_to_check: Area) -> bool:
            px, py = point
            ax, ay, aw, ah = area_to_check
            return ax <= px < ax + aw and ay <= py < ay + ah

        # 筛选出所有不在左侧也不在右侧区域的匹配项
        central_matches = [
            match for match in matches
            if not is_in_area(match[1], left_area) and not is_in_area(match[1], right_area)
        ]

        # 根据筛选后的中央区域匹配项数量进行决策
        if len(central_matches) == 0:
            # 在中央区域没有找到任何匹配
            return None
        elif len(central_matches) == 1:
            # 刚好剩下一个，就是它
            return central_matches[0]
        elif len(central_matches) == 2:
            # 剩下两个，需要根据“上”或“下”来选择
            # 按 y 坐标排序 (match[1][1] 是 y)，y值越小越靠上
            central_matches.sort(key=lambda m: m[1][1])
            if direction == 0:  # 0 代表“上”
                return central_matches[0]  # 返回y坐标最小的
            else:  # direction == 2，代表“下”
                return central_matches[1]  # 返回y坐标最大的
        else:
            # 剩余的候选项超过两个，无法决策
            raise ValueError(
                f"错误：在排除了左右侧边区域后，仍找到 {len(central_matches)} 个候选项，无法决策。"
                f" 候选项为: {central_matches}"
            )
    return None


# 通用逻辑
def move_direction(controller: PYAUTO,
                   image: np.ndarray,
                   hero_foot: Tuple[int, int],
                   directions_index):
    """
    向指定方向移动

    :param controller: PYAUTO对象
    :param image: 画面
    :param hero_foot: 英雄脚底的像素坐标
    :param directions_index: 移动方向，0123分别对应上右下左，也对应DIRECTIONS的索引
    """

    # # 先根据方向尝试找对应的箭头
    # template = None
    # mask = None
    # # x轴偏移量
    # x_offset = None
    # # y轴偏移量
    # y_offset = None

    # 由于模板匹配到的是模板的左上角。所以要找真正的门，需要从左上角加一个偏移量
    if 0 == directions_index:
        template = DIRECTION_UP_TEMPLATE
        mask = DIRECTION_UP_TEMPLATE_MASK
        # 上，向右（x）偏移1/2模板的宽度，向上（y）偏移固定值50
        x_offset, y_offset = int(template.shape[1] / 2), -150
    elif 1 == directions_index:
        template = DIRECTION_RIGHT_TEMPLATE
        mask = DIRECTION_RIGHT_TEMPLATE_MASK
        # 右，向右（x）偏移整个模板的宽度+固定值50，向下（y）偏移1/2模板的高度
        x_offset, y_offset = template.shape[1] + 150, int(template.shape[0] / 2)
    elif 2 == directions_index:
        template = DIRECTION_DOWN_TEMPLATE
        mask = DIRECTION_DOWN_TEMPLATE_MASK
        # 下，向右（x）偏移1/2模板的宽度，向下（y）偏移1整个模板的高度+固定值50
        x_offset, y_offset = int(template.shape[1] / 2), template.shape[0] + 150
    elif 3 == directions_index:
        template = DIRECTION_LEFT_TEMPLATE
        mask = DIRECTION_LEFT_TEMPLATE_MASK
        # 左，向左（x）偏移固定值50，向下（y）偏移1/2模板的高度
        x_offset, y_offset = -150, int(template.shape[0] / 2)

    else:
        # 报错，DIRECTIONS没配置对
        raise Exception(f"请检查DIRECTIONS配置:{DIRECTIONS}")

    # 先直接找上下左右方向的模板，如果找到了就用这个
    confidence, template_pos = iu.find_template_with_mask(image, template, mask)

    if confidence < 0.8:
        # 如果不能直接找到箭头，就再找“前进”模板
        matches = iu.find_template_all_with_mask(image, FORWARD_TEMPLATE,
                                                 FORWARD_TEMPLATE_MASK, 0.8)
        # 判断是否处于对应的区域内 DIRECTION_TEMPLATE_AREA
        match = find_unique_match_by_direction(matches, directions_index)

        if match:
            print("找到了前进模板")
            _, template_pos = match
            # todo: 由于“前进”模板离门更远，所以需要再往这个方向移动一个偏移量
        else:
            # 如果没有找到“前进”模板，就返回
            print("没有找到模板，向对应方向移动1秒")
            # hero.move_right_pixels(controller, 400, True)
            # controller.keyPressChar(, 1)
            move_second(controller, 1, directions_index, True)

            return
            # todo: 应该进行卡图情况处理
            # raise Exception(f"请检查DIRECTIONS配置:{DIRECTIONS}")
    else:
        print("找到了方向模板")

    # 计算中心像素坐标
    target_x = template_pos[0] + x_offset
    target_y = template_pos[1] + y_offset

    # 向目标移动
    move_to_target_once(controller, hero_foot, (target_x, target_y))
    # 移动完等0.3秒
    time.sleep(0.3)


# 独立逻辑
def go_to_next_room(controller: PYAUTO,
                    manager: SmallMapManager,
                    current_room: SmallRoom, next_room: SmallRoom
                    ) -> None:
    """
    写死过图逻辑，可能更快，但是不通用
    :param controller: vnc控制器
    :param manager: 小地图管理器
    :param current_room: 当前房间
    :param next_room: 下个房间
    :return: 无返回值
    """
    path_order = manager.path_order
    if current_room == path_order[0] and next_room == path_order[1]:
        # 第一张地图
        # 直接往右，400px
        move_pixels(controller, 1400, 2, True)
        pass
    elif current_room == path_order[1] and next_room == path_order[2]:
        # 第二张地图
        pass
    elif current_room == path_order[2] and next_room == path_order[3]:
        # 第三张地图
        pass
    elif current_room == path_order[3] and next_room == path_order[4]:
        # 第四张地图
        pass
    elif current_room == path_order[4] and next_room == path_order[5]:
        # 第五张地图
        pass
    elif current_room == path_order[5] and next_room == path_order[6]:
        # 第六张地图
        pass
    else:
        print(f"当前地图{current_room}，下一张地图{next_room}，找不到匹配的过图逻辑")
        raise Exception(f"请检查DIRECTIONS配置:{DIRECTIONS}")
    pass


def handle_stuck_in_room(controller: PYAUTO, manager: SmallMapManager, current_room: SmallRoom,
                         room_recorder: dict):
    """
    处理在房间内卡住的特殊情况。

    修订后逻辑：
    1. 优先检查是否有针对当前房间的特殊处理逻辑。
    2. 如果有，则执行特殊处理。特殊处理函数内部自行判断异常次数。
    3. 如果没有特殊处理逻辑，则检查通用处理的异常次数。
    4. 如果是第一次遇到（对于无特殊逻辑的房间），执行通用的 back_jump()。
    5. 如果是第二次遇到，则直接报错。
    6. 每次执行完处理后，增加异常计数。

    :param controller: VNC控制器
    :param manager: 小地图控制器
    :param current_room: 当前所在的房间
    :param room_recorder: 房间记录器
    """

    def save_log():
        new_image = screenshot_util.get_game_screenshot()
        log_dir = LOG_DIR
        import os
        os.makedirs(log_dir, exist_ok=True)
        cv2.imwrite(os.path.join(log_dir, f"error_{current_room}.png"), new_image)
        raise Exception(f"未央过图异常：在房间 {current_room} 卡住，已达到最大尝试次数。已保存截图。")

    # --- 特殊处理逻辑 ---
    # 每个特殊处理函数现在接收 room_recorder 作为参数，以便内部判断异常次数
    def handle_wyzj1_1_4(recorder):
        if recorder['exception_count'] >= 1:  # 此房间只允许处理1次
            save_log()
        else:
            move_pixels(controller, 100, 0)
            move_pixels(controller, 800, 1)
            back_jump(controller)

    def handle_wyzj1_2_4(recorder):
        if recorder['exception_count'] >= 1:  # 此房间只允许处理1次
            save_log()
        else:
            move_pixels(controller, 50, 2)

    def handle_wyzj1_2_2_or_2_3(recorder):
        if recorder['exception_count'] >= 1:  # 此房间只允许处理1次
            save_log()
        else:
            move_pixels(controller, 100, 0)

    def handle_cygq1_2_1(recorder):
        if recorder['exception_count'] >= 1:  # 此房间只允许处理1次
            save_log()
        else:
            move_pixels(controller, 400, 3)
            move_pixels(controller, 100, 2)

    special_handlers = {
        ("未央之脊", "1阶", (1, 4)): handle_wyzj1_1_4,
        ("未央之脊", "1阶", (2, 4)): handle_wyzj1_2_4,
        ("未央之脊", "1阶", (2, 2)): handle_wyzj1_2_2_or_2_3,
        ("未央之脊", "1阶", (2, 3)): handle_wyzj1_2_2_or_2_3,
        ("残月宫阙", "1阶", (2, 1)): handle_cygq1_2_1,
    }

    handler_key = (manager.dungeon_name, manager.dungeon_level, current_room)

    # 检查是否存在特殊处理
    if handler_key in special_handlers:
        print(f"房间 {current_room} 存在特殊脱困逻辑，正在执行...")
        special_handlers[handler_key](room_recorder)
    else:
        # --- 通用处理逻辑 ---
        print(f"房间 {current_room} 没有特殊脱困逻辑，执行通用处理。")
        if room_recorder['exception_count'] >= 1:
            # 对于没有特殊逻辑的房间，通用逻辑只尝试1次
            save_log()
        else:
            # 第一次遇到，执行默认的后跳
            print("执行默认的后跳。")
            back_jump(controller)

    # 统一在最后增加异常计数
    room_recorder['exception_count'] += 1


def select_vote(controller: PYAUTO, image):
    """
    未央选票
    """
    # 选择单人的，12阶以下的
    # 找1D-6D
    i = 1
    for ticket in TICKET_ALL:
        i += 1
        # print(ticket)

        # 票都在右边，这里的960，600超出截图，所以截的只有右半部分
        confidence, best_match_loc = iu.find_template_with_mask(image, ticket[0], ticket[1],
                                                                region=(450, 0, 960, 600))

        if confidence < 0.97:
            # 没找到这一层的票，继续找下一层
            continue

        print(f"找到了票,第{i}阶")
        # 计算票的中心点，等会点这个地方
        center_x = best_match_loc[0] + int(ticket[0].shape[1] / 2)
        center_y = best_match_loc[1] + int(ticket[0].shape[0] / 2)

        # controller.human_like_move_and_click(center_x, center_y, 0.7, button_mask=4)
        controller.moveTo(center_x, center_y)
        controller.click('left')

        time.sleep(1)

        # 再找一下“未央幻境入场”的按钮
        
        new_image = screenshot_util.get_game_screenshot()
        confidence1, best_match_loc1 = iu.find_template_with_mask(
            new_image, BUTTON_WEIYANGRUCHANG_TEMPLATE, BUTTON_WEIYANGRUCHANG_TEMPLATE_MASK)

        if confidence1 < 0.8:
            # 没找到可能卡了，再按一下鼠标右键，等三秒，再重试一下
            controller.mouse_press(center_x, center_y, button_mask=4)

            time.sleep(3)

        new_image = screenshot_util.get_game_screenshot()
        confidence1, best_match_loc1 = iu.find_template_with_mask(
            new_image, BUTTON_WEIYANGRUCHANG_TEMPLATE, BUTTON_WEIYANGRUCHANG_TEMPLATE_MASK)

        if confidence1 < 0.9:
            print("找到了票，但用票失败，可能是安全模式或者60s等待")
            return

        center_x1 = best_match_loc1[0] + int(BUTTON_WEIYANGRUCHANG_TEMPLATE.shape[1] / 2)
        center_y1 = best_match_loc1[1] + int(BUTTON_WEIYANGRUCHANG_TEMPLATE.shape[0] / 2)

        controller.human_like_move_and_click(center_x1, center_y1, 0.3, button_mask=1)

        time.sleep(0.5)
        # 选完票等待5秒，按一下esc关闭右上角的门票属性
        controller.keyPressChar("space")
        time.sleep(5)
        controller.keyPressChar("Escape")
        print("选票完成")
        return
    print("没找到票")


def main(controller: PYAUTO):
    directions = ("Up", "Right", "Down", "Left")
    direction_cycler = itertools.cycle(directions)

    # 房间记录器，用于检测是否在同一个房间卡住
    # 格式: {'room': SmallRoom, 'count': int,'exception_count':int}
    room_recorder = {}

    # 初始地址位置为(2,1)
    # current_room = map_info['过图顺序'][0]
    while True:
        print("=======开启一次循环=========")

        # 尽量尝试在一次循环中直接过图

        new_image = screenshot_util.get_game_screenshot()

        # 找一下“未央幻境入场”窗口的标题字样，大概位置(760,0,200,100)的位置
        corp = iu.crop_image_wh(new_image, (175, 0, 185, 100))
        title_flag = iu.match_template(corp, TITLE_WEIYANGRUCHANG_TEMPLATE, 0.85)

        if title_flag:
            # 如果找到了“未央开始选票”的标题，就开始选票方法
            select_vote(controller, new_image)
            continue

        # ===判断是哪个图，比如幻境前殿===
        dungeon_name = identity_dungeon_name(new_image)
        if not dungeon_name:
            # 如果没找到地图名称，直接报错
            print("未找到地图名称")
            continue
        # todo: 暂时写死1阶
        img = screenshot_util.get_game_screenshot()
        manager = small_map.create_manager(img, dungeon_name, "1阶")

        # ====判断当前状态
        # 这里找一下结算时的目标，比如评分、获得经验之类的标签，如果找到了任何一个，就说明已经通关了
        find_result = hero.find_title(new_image)

        # 找角色的脚坐标
        if find_result:
            hero_foot = (find_result[0] + 37, find_result[1] + 170)
        else:
            key = next(direction_cycler)
            print(f"英雄不存在，行动半秒{key}")
            controller.keyPressChar(key, 0.5)
            time.sleep(1)
            continue
        # ====yolo8识别目标，把打怪的优先级放到找门优先级之前

        output = yolo8.detect_object_r(new_image, SESSION, MODEL_INPUTS, INPUT_WIDTH, INPUT_HEIGHT)
        # 模型位置、模型得分、模型类别名称
        postprocess_r = yolo8.postprocess_r(output, 640, 640, 960, 600)
        door_target = None
        if postprocess_r is not None and len(postprocess_r):
            print("找到怪了，打怪")
            # 如果找到的对象不为空

            # 有boss先打boss，找到boss列表
            if "boss_hundun" in postprocess_r \
                    or "boss_qiongqi" in postprocess_r \
                    or "boss_taowu" in postprocess_r \
                    or "boss_taotie" in postprocess_r:
                # todo: 专门按一个键
                boss_det_list = []
                for target_r in postprocess_r:
                    if target_r.startswith("boss_"):
                        boss_det_list.extend(postprocess_r[target_r])

                # 找最近的boss
                boss_foot = find_nearest_target(hero_foot, boss_det_list)
                # boss_foot的y轴向下60像素
                boss_foot = (boss_foot[0], boss_foot[1])
                # 攻击这个目标
                attack_target(controller, hero_foot, boss_foot, new_image)
                continue
            # 如果没有boss，但有怪
            elif "mon_shou" in postprocess_r \
                    or "mon_pang" in postprocess_r \
                    or "mon_bing" in postprocess_r:
                target_det_list = []
                for target_r in postprocess_r:
                    if target_r.startswith("mon_"):
                        target_det_list.extend(postprocess_r[target_r])
                # 找最近的单位
                target_foot = find_nearest_target(hero_foot, target_det_list)
                # 攻击最近的目标
                attack_target(controller, hero_foot, target_foot, new_image)
                continue
            elif "door_boss" in postprocess_r:
                # 如果找到了门，直接往门走，把门取出
                door_list = postprocess_r.get("door_boss")
                x, y = find_nearest_target(hero_foot, door_list)
                # 向右、下各偏移50
                door_target = (x + 50, y + 50)
                # hero.move_to_target_once(controller, hero_foot, (x + 50, y + 50))

        else:
            print("没有找到怪")

        # ====获取当前房间号
        small_map_image = manager.crop_small_map(new_image)
        # cv2.imshow("small_map", small_map_image)
        # cv2.waitKey(0)
        current_room = manager.get_current_room(small_map_image.copy())
        if not current_room:
            print("未找到当前房间，很可能已经结束了，等3秒再看看")
            time.sleep(3)
            continue

        # ====找下个门方向
        next_room = manager.get_next_rooms(current_room)

        # 判断是否在同一个房间卡住
        if 'room' not in room_recorder or room_recorder['room'] != current_room:
            # 如果记录器是空的，或者当前房间不是记录中的房间，则重置记录器
            room_recorder = {'room': current_room, 'count': 1, 'exception_count': 0}
            print(f"进入新房间 {current_room}, 已记录, 次数 1")
        else:
            # 如果当前房间与记录中的房间相同，增加计数
            if room_recorder['count'] < (room_recorder['exception_count'] + 1) * 3:
                room_recorder['count'] += 1
                print(f"仍在房间 {current_room}, 已记录, 次数 {room_recorder['count']}")
            else:
                # 如果计数达到或超过(n+1)*3次，则认为卡住，执行特殊处理。n是异常处理次数
                print(f"在房间 {current_room} 卡住超过3次，执行第{room_recorder['exception_count'] + 1}次特殊处理")
                handle_stuck_in_room(controller, manager, current_room, room_recorder)
                # 执行特殊处理后，跳过本次循环的常规移动逻辑
                continue

        # ====如果有一个下个门，那就处理
        # ====如果有两个下个门，先找第一个方向，看能不能在对应方向找到问号模板

        num_next_rooms = len(next_room)
        if num_next_rooms == 0:
            print(f"角色当前房间{current_room}，找不到下个房间")
            time.sleep(1)
            attack_target(controller, hero_foot, hero_foot, new_image)
            continue
        else:
            target_room_info = None
            # 遍历除最后一个之外的所有房间
            for i in range(num_next_rooms - 1):
                room_info = next_room[i]
                # is_room_open 检查房间是否是开放的（即没有问号）
                if manager.is_room_open(small_map_image.copy(), room_info[0]):
                    print(f"房间 {room_info[0]} 是开放的，选为目标")
                    target_room_info = room_info
                    break  # 找到开放房间，跳出循环

            # 如果循环结束后没有找到开放的房间，或者只有一个出口，则选择最后一个房间
            if target_room_info is None:
                target_room_info = next_room[-1]
                print(f"未找到开放房间或这是最后一个选项，选为目标: {target_room_info[0]}")

            # 如果有多个房间的情况下，前面的房间都已经走过了，也判断一下是否下个房间有领主门，有的话先走领主门
            if door_target:
                move_to_target_once(controller, hero_foot, door_target)
                continue

            # 向选定的目标房间移动
            direction = target_room_info[1]
            print(f"角色当前房间{current_room}，最终选择的下个房间{target_room_info[0]}，方向为{direction}")
            index = DIRECTIONS.index(direction)
            move_direction(controller, new_image, hero_foot, index)


def identity_dungeon_name(img: np.ndarray) -> None | str:
    """
    判断当前进行的副本名称
    :param img: 游戏截图
    :return: 副本名称，如果匹配不到，就返回None
    """
    # 加载模板
    # 裁剪原图区域名称
    wh = iu.crop_image_wh(img, (820, 5, 102, 25))
    results = iu.find_all_template_binary(wh, [
        (WEIYANG_MAP_HJQD, 0.8), (WEIYANG_MAP_CYGQ, 0.8),
        (WEIYANG_MAP_WYZJ, 0.8), (WEIYANG_MAP_CHZL, 0.8)
    ])

    if results[0]:
        return "幻境前殿"
    elif results[1]:
        return "残月宫阙"
    elif results[2]:
        return "未央之脊"
    elif results[3]:
        return "沧海竹林"

    print("没匹配到地图名称")
    return None


def move_second(controller:PYAUTO, seconds: float, direction_index: int, run_mode: bool = True):
    """
    向指定方向移动指定秒数
    :param controller: PYAUTO对象
    :param seconds: 要移动的秒数
    :param direction_index: 方向索引 (0:上, 1:右, 2:下, 3:左)
    :param run_mode: 是否为奔跑模式（仅对水平移动有效）
    """
    if not (0 <= direction_index < 4):
        print(f"错误的方向索引: {direction_index}")
        return
    if seconds <= 0:
        print("移动秒数必须大于0")
        return

    key_to_press = DIRECTIONS[direction_index]
    is_horizontal = direction_index in [1, 3]

    if is_horizontal:
        press_type = 1
        mode_str = '跑' if run_mode else '走'
        print(f"向{key_to_press}移动 {seconds:.2f} 秒，{mode_str}模式")
    else:  # 垂直移动
        press_type = 0
        print(f"向{key_to_press}移动 {seconds:.2f} 秒")

    handle_key_real_down(controller, key_to_press, seconds, press_type)


def handle_key_real_down(controller: PYAUTO, ikey, delay, press_type=0):
    """
    移动，x轴会双击移动。y轴单击。如果
    :param controller: PYAUTO对象
    :param ikey: 待按下的键
    :param delay: 按键持续时间,可以传小数，1代表1秒
    :param press_type: x轴还是y轴，1是x轴双击+长按，0是y轴长按
    :return:
    """
    if press_type == 1:
        if delay > 0.2:
            print("x轴" + str(delay - 0.15))
            # x轴，需要双击方向键
            controller.keyPressChar(ikey, 0.1)
            delay = delay - 0.15
            time.sleep(0.05)
        else:
            print("x轴短按" + str(delay))
    else:
        print("y轴" + str(delay))
    # v.key_down(ikey)
    # time.sleep(float(delay))
    # v.key_up(ikey)
    controller.keyPressChar(ikey, float(delay))



def move_to_target_once(controller: PYAUTO, hero_foot, target_foot):
    """
    一次性走到对应位置
    :param controller:
    :param hero_foot:
    :param target_foot:
    :return:
    """
    # 需求1: 直接定义成列表，省去转换步骤
    key_times = []

    # 假设 tx 和 ty 的定义
    tx = 50
    ty = 50

    # 判断英雄在目标的左边还是右边
    rr_1 = hero_foot[0] - target_foot[0]
    print("rr_1:", rr_1)
    if abs(rr_1) > tx:
        if rr_1 > 0:
            ikey = "Left"
        else:
            ikey = "Right"
        # print(f"ikey:{ikey}")
        x_time = abs(rr_1 / status.speed_run) * 0.25
        # print("x_time:", x_time)
        # 直接添加到列表中
        key_times.append((ikey, float(x_time)))

    # 判断英雄在怪物的上边还是下边
    rr_2 = hero_foot[1] - target_foot[1]
    print("rr_2:", rr_2)
    if abs(rr_2) > ty:
        if rr_2 > 0:
            ikey = "Up"
        else:
            ikey = "Down"
        # print(f"ikey:{ikey}")
        y_time = abs(rr_2 / status.speed_y) * 0.25
        # print("y_time:", y_time)
        # 直接添加到列表中
        key_times.append((ikey, float(y_time)))

    # 处理键
    if not key_times:
        return

    # 如果只有一个键，直接调用现有逻辑
    if len(key_times) == 1:
        ikey, delay = key_times[0]
        # 判断是x轴还是y轴来传递 attack_type
        is_x_axis = 1 if ikey in ["Left", "Right"] else 0
        handle_key_real_down(controller, ikey, delay, is_x_axis)

    # 需求2: 当有两个键时（必然是一个X轴一个Y轴），实现新的复杂按键逻辑
    elif len(key_times) == 2:
        # 1. 分离出x和y的按键与时间
        x_key, y_key = None, None
        x_time, y_time = 0.0, 0.0
        for key, delay in key_times:
            if key in ["Left", "Right"]:
                x_key, x_time = key, delay
            else:
                y_key, y_time = key, delay

        # 2. X轴预操作的总耗时是 0.05s(按) + 0.05s(停) = 0.1s
        #    如果总时间 x_time 小于这个值，则特殊处理或不执行长按
        stutter_step_total_time = 0.05
        if x_time < stutter_step_total_time:
            # 如果X轴移动时间非常短，可能只够完成预操作
            # 这里简单处理为只执行预操作，你可以根据实际需求调整
            # print(f"X轴时间 {x_time:.2f}s 过短，仅执行短按。")
            controller.keyPressChar(x_key, 0.05)
            # 在这种情况下，Y轴移动仍然需要执行
            controller.keyPressChar(y_key, y_time)
            return

        # print("执行双键移动逻辑...")
        # 3. 计算X轴的有效长按时间
        #    根据您的描述: "x轴按键的时间要减去0.05秒再计算"
        #    但考虑到预操作是 短按(0.05) + 暂停(0.05)，所以实际用于长按的时间要减去0.1
        #    这里遵循您更精确的描述 "短按0.05s并抬起，暂停0.05秒"，总计0.1秒
        x_effective_time = x_time - stutter_step_total_time

        # 4. 比较X轴的有效长按时间和Y轴的总时间，确定哪个先抬起
        if x_effective_time < y_time:
            short_key, long_key = x_key, y_key
            short_time, long_time = x_effective_time, y_time
        else:
            short_key, long_key = y_key, x_key
            short_time, long_time = y_time, x_effective_time

        # print(f"X轴预操作: 短按 {x_key} 0.05s, 暂停 0.05s")
        # 5. 开始执行按键序列
        # X轴预操作: "x轴的按键短按0.05s并抬起，暂停0.05秒"
        # 注意：keypress是按下并立即抬起，所以它的持续时间参数就是按下的时间
        controller.keyPressChar(x_key, 0.05)
        time.sleep(0.05)

        # print(f"同时按下 {x_key} 和 {y_key}")
        # X轴和Y轴的按键按下 (此时X轴是第二次按下，进入长按)
        controller.key_down(x_key)
        time.sleep(0.05)
        controller.key_down(y_key)

        # print(f"等待 {short_time:.4f}s...")
        # 等待较短按键所需时间
        if short_time > 0.05:
            time.sleep(short_time)

        # print(f"抬起短时间键: {short_key}")
        # 抬起较短时间的那个按键
        controller.key_up(short_key)

        # 计算并等待剩余时间
        remaining_time = long_time - short_time + 0.05
        # print(f"等待剩余时间 {remaining_time:.4f}s...")
        if remaining_time > 0:
            time.sleep(remaining_time)

        # print(f"抬起长时间键: {long_key}")
        # 抬起最后一个键
        controller.key_up(long_key)



def move_pixels(controller: "VNCController", pixels: int, direction_index: int, run_mode: bool = True):
    """
    向指定方向移动指定像素
    :param controller: VNCController对象
    :param pixels: 要移动的像素数
    :param direction_index: 方向索引 (0:上, 1:右, 2:下, 3:左)
    :param run_mode: 是否为奔跑模式（仅对水平移动有效）
    """
    if not (0 <= direction_index < 4):
        print(f"错误的方向索引: {direction_index}")
        return
    if pixels <= 0:
        print("移动像素数必须大于0")
        return

    key_to_press = DIRECTIONS[direction_index]
    is_horizontal = direction_index in [1, 3]

    if is_horizontal:
        speed = status.speed_run if run_mode else status.speed_x
        press_type = 1
        mode_str = '跑' if run_mode else '走'
        print(f"向{key_to_press}移动 {pixels} 像素，{mode_str}模式")
    else:  # 垂直移动
        speed = status.speed_y
        press_type = 0
        print(f"向{key_to_press}移动 {pixels} 像素")

    if speed is None or speed == 0:
        print(f"{'水平' if is_horizontal else '垂直'}速度未初始化或为0，无法移动")
        return

    move_time = abs(pixels / speed) * 0.25
    print(f"计算移动时间: {move_time:.4f}s")

    handle_key_real_down(controller, key_to_press, move_time, press_type)



def back_jump(controller: PYAUTO):
    """
    后跳
    :param controller: vnc控制器
    :return:
    """
    controller.keyDownChar("down")
    time.sleep(random.uniform(0.05, 0.15))
    controller.keyDownChar("c")
    time.sleep(random.uniform(0.13, 0.20))
    controller.keyUpChar("c")
    controller.keyUpChar("down")



def attack_target(controller: PYAUTO, hero_foot, target_foot, img: np.ndarray, key: str | None = None):
    """
    攻击目标
    :param controller: 控制器对象
    :param hero_foot: 角色位置
    :param key: 指定按键，如果不指定就随机选择一个
    :param target_foot: 目标位置
    :param img:  图片
    """
    # 游戏
    thx = 30  # 捡东西时，x方向的阈值
    thy = 30  # 捡东西时，y方向的阈值
    attx = 50  # 攻击时，x方向的阈值
    atty = 50  # 攻击时，y方向的阈值

    # 先计算可用技能
    judgment_array = skill.process_image_blocks(img)

    if key_config_run.DEFAULT_CONFIG.get("skills") is None:
        raise ValueError("按键数组未配置")

    # 处于攻击距离
    if abs(hero_foot[0] - target_foot[0]) < attx and abs(hero_foot[1] - target_foot[1]) < atty:
        if not key:
            # 使用判断数组获取可用按键
            items = get_available_items(judgment_array) if judgment_array else []
            # 过滤掉值为None的元素
            valid_items = [item for item in items if item is not None]

            if not valid_items:
                key = "x"
                controller.keyPressChar(key)
                print("没有可用的有效按键，跳过攻击")
                return

            # 攻击
            key = random.choice(valid_items)
        controller.keyPressChar(key)

        print(f"攻击1，按下按键: {key}")

    else:
        # 不处于攻击距离，需要移动
        move_to_target_once(controller, hero_foot, target_foot)
        if not key:
            # 再进行攻击
            items = get_available_items(judgment_array) if judgment_array else []
            # 过滤掉值为None的元素
            valid_items = [item for item in items if item is not None]
            print(f"有效按键列表:{valid_items}")
            if not valid_items:
                # 没有可用的有效按键，按x键
                time.sleep(0.2)
                key = "x"
                print(f"没有可用的有效按键，按下默认按键: {key}")
            else:
                # 攻击
                key = random.choice(valid_items)
                print(f"攻击2，按下按键: {key}")
            print(f"攻击3，按下按键: {key}")
            controller.keyPressChar(key)
    time.sleep(1)



def get_available_items(judgment_array):
    """
    根据判断数组获取可用按键列表
    :param judgment_array: 判断数组，包含True/False/None值
    :return: 可用按键列表
    """
    if status.configurable_keys is None or len(status.configurable_keys) < 14:
        raise ValueError("按键数组未配置")
    print("configurable_keys:", status.configurable_keys)
    print(f"judgment_array:{judgment_array}")
    available_items = []

    for i, value in enumerate(judgment_array):
        if value is True and i < len(status.configurable_keys) and status.configurable_keys[i] is not None:
            available_items.append(status.configurable_keys[i])

    print("计算结果:", available_items)
    return available_items


def find_nearest_target(hero_foot, target_det_list):
    """
    从目标列表中找到距离英雄最近的目标坐标。

    该函数通过计算欧氏距离来比较英雄与每个目标的远近。

    :param hero_foot: 英雄的脚底坐标，一个包含 (x, y) 的元组或列表。
    :param target_det_list: 一个目标检测对象的列表。列表中的每个对象都需要有一个 'ifoot' 属性，
                            该属性也是一个包含 (x, y) 坐标的元组或列表。
    :return: 返回列表中距离英雄最近的目标的 'ifoot' 坐标（一个元组或列表）。
             如果传入的目标列表为空，则返回 None。
    """
    # 边缘情况：如果目标列表为空，则直接返回 None，避免后续代码出错
    if not target_det_list:
        return None

    # 优化：如果目标列表只有一个元素，那么它就是最近的，直接返回它的坐标
    if len(target_det_list) == 1:
        return target_det_list[0].ifoot

    min_distance = float("inf")  # 初始化一个无穷大的最小距离值
    nearest_foot = None  # 初始化最近目标的坐标为 None

    # 遍历列表中的每一个目标
    for target_det in target_det_list:
        target_foot = target_det.ifoot
        # 使用勾股定理（欧氏距离）计算英雄与当前目标脚底之间的直线距离
        # dis = ((hero_foot[0] - target_foot[0]) ** 2 +
        #        (hero_foot[1] - target_foot[1]) ** 2) ** 0.5
        # 省略了开平方，可能能节省一捏捏的性能
        dis = ((hero_foot[0] - target_foot[0]) ** 2 + (hero_foot[1] - target_foot[1]) ** 2)

        # 如果发现当前目标的距离比已记录的最小距离还要近
        if dis < min_distance:
            min_distance = dis  # 更新最小距离
            nearest_foot = target_foot  # 保存这个更近目标的坐标

    # 遍历完所有目标后，返回记录下的那个最近目标的坐标
    return nearest_foot
