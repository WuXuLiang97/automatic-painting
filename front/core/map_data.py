# -*- coding: utf-8 -*-
"""集中存放地图/掉落/坐标等静态数据。
拆分自 core.common 以降低其导入副作用并提升可读性。
后续如需做配置化，可改为从 JSON / 数据库动态加载。
"""
from __future__ import annotations

# 物品品质拾取策略
pink_goods_info = {
    "风暴逆鳞普通": {
        '蓝色': True,
        '紫色': True,
        '粉色': False,
        '金色': True,
    },
    "德洛斯矿山外围": {
        '蓝色': True,
        '紫色': True,
        '粉色': True,
        '金色': True,
    },
}

# 地图特定的最小房间数要求
MAP_MIN_ROOMS = {
    "跌宕群岛": 8,
    "妖气追踪": 8,
    "风暴逆鳞普通": 4,
    "德洛斯矿山外围": 12
}

# Boss / 怪物高度等信息
map_boss_info = {
    "风暴幽城": {
        'boss_fbyc_mymbz': {'height': 245},
        'monster_fbyc_min_boss': {'height': 180}
    },
    "风暴逆鳞普通": {
        'boss_fbnl_yhzgdzstk': {'height': 240},
        # 名字高度+380（身体+离地）
        'boss_fbnl_phzwh': {'height': 277},
        # 身体高度+120离地高度
        'boss_fbnl_phzwh_box': {'height': 50},
    },
    "流雨瀑布": {
        'boss_lypb': {'height': 200},
        'monster_lypb_min_boss': {'height': 200},
        'monster_lypb_min_boss_xgswzljl': {'height': 242},
    },
    "海伯伦的预言所": {
        'boss_fbyc_mymbz': {'height': 245},
        'monster_fbyc_min_boss': {'height': 180}
    },
    "德洛斯矿山外围": {
        'boss_dlsks_onsblk': {'height': 140},
        'boss_dlsks_qtzft': {'height': 182},
        'boss_dlsks_klj': {'height': 182},
    },
    "深渊：终末崇拜者": {
        'boss_sy': {'height': 100},
        'boss_sy_1': {'height': 0},
        'boss_sy-zmcbz': {'height': 175},
        'boss_sy-zmcbz_box': {'height': 0},
    },
    "跌宕群岛": {
        'monster_115_1': {'height': 240},
        'monster_115_1_box': {'height': 0},
        'monster_115_2': {'height': 180},
        'monster_115_2_box': {'height': 0},
        'monster_115_3': {'height': 162},
        'monster_115_3_box': {'height': 0},
        'monster_115_4': {'height': 200},
        'monster_115_4_box': {'height': 0},
        'monster_115_5': {'height': 220},
        'monster_115_5_box': {'height': 0},
        'boss_115_1': {'height': 180},
        'boss_115_1_box': {'height': 0},
        'boss_115_2': {'height': 220},
        'boss_115_2_box': {'height': 0},
        'boss_115_3': {'height': 140},
        'boss_115_3_box': {'height': 0},
        'boss_115_4': {'height': 140},
        'boss_115_4_box': {'height': 0},
    },
    "妖气追踪": {
        'monster_115_1': {'height': 240},
        'monster_115_1_box': {'height': 0},
        'monster_115_2': {'height': 180},
        'monster_115_2_box': {'height': 0},
        'monster_115_3': {'height': 162},
        'monster_115_3_box': {'height': 0},
        'monster_115_4': {'height': 200},
        'monster_115_4_box': {'height': 0},
        'monster_115_5': {'height': 220},
        'monster_115_5_box': {'height': 0},
        'monster_115_6': {'height': 220},
        'monster_115_6_box': {'height': 0},
        'boss_115_1': {'height': 180},
        'boss_115_1_box': {'height': 0},
        'boss_115_2': {'height': 220},
        'boss_115_2_box': {'height': 0},
        'boss_115_3': {'height': 140},
        'boss_115_3_box': {'height': 0},
        'boss_115_4': {'height': 140},
        'boss_115_4_box': {'height': 0},
    },
    "通用": {
        'monster_115_1': {'height': 240},
        'monster_115_1_box': {'height': 0},
        'monster_115_2': {'height': 180},
        'monster_115_2_box': {'height': 0},
        'monster_115_3': {'height': 162},
        'monster_115_3_box': {'height': 0},
        'monster_115_4': {'height': 200},
        'monster_115_4_box': {'height': 0},
        'monster_115_5': {'height': 220},
        'monster_115_5_box': {'height': 0},
        'monster_115_6': {'height': 220},
        'monster_115_6_box': {'height': 0},
        'boss_115_1': {'height': 180},
        'boss_115_1_box': {'height': 0},
        'boss_115_2': {'height': 220},
        'boss_115_2_box': {'height': 0},
        'boss_115_3': {'height': 140},
        'boss_115_3_box': {'height': 0},
        'boss_115_4': {'height': 140},
        'boss_115_4_box': {'height': 0},
        'boss_dlsks_onsblk': {'height': 140},
        'boss_dlsks_qtzft': {'height': 182},
        'boss_dlsks_klj': {'height': 182},
        'boss_fbnl_yhzgdzstk': {'height': 240},
        'boss_fbnl_phzwh': {'height': 277},
        'boss_fbnl_phzwh_box': {'height': 50},
    },
}

# 小地图坐标裁剪信息
map_pos_info = {
    "风暴幽城": {"x1": 1067 - 6 - 108, "y1": 48, "x2": 1067 - 6, "y2": 48 + 54},
    "风暴逆鳞普通": {"x1": 1067 - 6 - 72, "y1": 48, "x2": 1067 - 6, "y2": 48 + 36},
    "流雨瀑布": {"x1": 1067 - 11 - 126, "y1": 52, "x2": 1067 - 11, "y2": 52 + 54},
    "海伯伦的预言所": {"x1": 1067 - 11 - 90, "y1": 52, "x2": 1067 - 11, "y2": 52 + 72},
    "德洛斯矿山外围": {"x1": 1067 - 12 - 126, "y1": 52, "x2": 1067 - 12, "y2": 52 + 54},
    "深渊：终末崇拜者": {"x1": 1067 - 12 - 126, "y1": 52, "x2": 1067 - 12, "y2": 52 + 54},
    "跌宕群岛": {"x1": 1067 - 12 - 126, "y1": 52, "x2": 1067 - 12, "y2": 52 + 54},
    "妖气追踪": {"x1": 1067 - 12 - 126, "y1": 52, "x2": 1067 - 12, "y2": 52 + 54},
    "通用": {"x1": 1067 - 12 - 162, "y1": 52, "x2": 1067 - 12, "y2": 52 + 90},
}

# 地图房间结构（默认填充，可能后续动态识别）
a_mapInfo = {
    "风暴幽城": [
        [1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1], ],
    "风暴逆鳞普通": [
        [1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1], ],
    "流雨瀑布": [
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1], ],
    "海伯伦的预言所": [
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1], ],
    "德洛斯矿山外围": [
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1], ],
    "深渊：终末崇拜者": [
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1], ],
    "跌宕群岛": [
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1], ],
    "妖气追踪": [
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1], ],
    "通用": [
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1], ],
}

# 方向判定区域（用于判断下一房间方向）
a_DictInfo = {
    '风暴幽城': {
        'right': {"min_x": 833, "max_x": 1067, "min_y": 0, "max_y": 600},
        'left': {"min_x": 0, "max_x": 233, "min_y": 0, "max_y": 600},
        "up": {"min_x": 250, "max_x": 817, "min_y": 125, "max_y": 417},
        "down": {"min_x": 250, "max_x": 1067, "min_y": 417, "max_y": 600},
    },
    '风暴逆鳞普通': {
        'right': {"min_x": 817, "max_x": 1067, "min_y": 0, "max_y": 600},
        'left': {"min_x": 0, "max_x": 533, "min_y": 0, "max_y": 600},
        "up": {"min_x": 533, "max_x": 1067, "min_y": 0, "max_y": 600},
        "down": {"min_x": 0, "max_x": 1067, "min_y": 458, "max_y": 650},
    },
    '流雨瀑布': {
        'right': {"min_x": 933, "max_x": 1067, "min_y": 300, "max_y": 600},
        'left': {"min_x": 0, "max_x": 233, "min_y": 300, "max_y": 600},
        "up": {"min_x": 250, "max_x": 817, "min_y": 125, "max_y": 417},
        "down": {"min_x": 250, "max_x": 1067, "min_y": 417, "max_y": 600},
    },
    '海伯伦的预言所': {
        'right': {"min_x": 933, "max_x": 1067, "min_y": 300, "max_y": 600},
        'left': {"min_x": 0, "max_x": 233, "min_y": 300, "max_y": 600},
        "up": {"min_x": 250, "max_x": 1067, "min_y": 125, "max_y": 417},
        "down": {"min_x": 250, "max_x": 1067, "min_y": 417, "max_y": 600},
    },
    '德洛斯矿山外围': {
        'right': {"min_x": 933, "max_x": 1067, "min_y": 0, "max_y": 600},
        'left': {"min_x": 0, "max_x": 233, "min_y": 0, "max_y": 600},
        "up": {"min_x": 250, "max_x": 875, "min_y": 125, "max_y": 417},
        "down": {"min_x": 250, "max_x": 933, "min_y": 417, "max_y": 650},
    },
    '跌宕群岛': {
        'right': {"min_x": 933, "max_x": 1067, "min_y": 0, "max_y": 600},
        'left': {"min_x": 0, "max_x": 233, "min_y": 0, "max_y": 600},
        "up": {"min_x": 0, "max_x": 1067, "min_y": 125, "max_y": 370},
        "down": {"min_x": 250, "max_x": 933, "min_y": 500, "max_y": 650},
    },
    '妖气追踪': {
        'right': {"min_x": 933, "max_x": 1067, "min_y": 0, "max_y": 600},
        'left': {"min_x": 0, "max_x": 350, "min_y": 0, "max_y": 600},
        "up": {"min_x": 0, "max_x": 1067, "min_y": 0, "max_y": 370},
        "down": {"min_x": 250, "max_x": 933, "min_y": 500, "max_y": 650},
    },
    '通用': {
        'right': {"min_x": 933, "max_x": 1067, "min_y": 0, "max_y": 600},
        'left': {"min_x": 0, "max_x": 350, "min_y": 0, "max_y": 600},
        "up": {"min_x": 0, "max_x": 1067, "min_y": 0, "max_y": 370},
        "down": {"min_x": 0, "max_x": 1067, "min_y": 417, "max_y": 650},
    },
}

__all__ = [
    'pink_goods_info',
    'MAP_MIN_ROOMS',
    'map_boss_info',
    'map_pos_info',
    'a_mapInfo',
    'a_DictInfo'
]
