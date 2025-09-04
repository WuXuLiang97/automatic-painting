from utils.common.load_image import load_images_from_directory, read_from_path
from root_dir import root_path

# 加载目录下的所有PNG图片到内存
image_data_GRAY, image_data_HSV = load_images_from_directory()

MSDK_DLL_PATH = root_path + "/res/msdk.dll"

minimap = {
    "德洛斯矿山外围": {"width": 126, "height": 54, "row": 7, "col": 3},
    "流雨瀑布": {"width": 126, "height": 54, "row": 7, "col": 3},
    "风暴幽城": {"width": 108, "height": 54, "row": 6, "col": 3},
    "风暴逆鳞普通": {"width": 72, "height": 36, "row": 4, "col": 2},
    "海伯伦的预言所": {"width": 90, "height": 72, "row": 5, "col": 4},
    "深渊：终末崇拜者": {"width": 126, "height": 54, "row": 7, "col": 3},
    "跌宕群岛": {"width": 126, "height": 54, "row": 7, "col": 3},
    "妖气追踪": {"width": 126, "height": 54, "row": 7, "col": 3},
    "通用": {"width": 162, "height": 90, "row": 9, "col": 5},
}

MAP_HERO = root_path + "/res/map_hero.png"
MAP_SPECIAL_ROOM = root_path + "/res/map_special_room.png"
MAP_BOSS = root_path + "/res/map_boss.png"
MAP_QUERY = root_path + "/res/map_query.png"
MAP_QUERY1 = root_path + "/res/map_query1.png"
MAP_ELITE = root_path + "/res/map_elite.png"

hero_template = read_from_path(MAP_HERO)
special_room_template = read_from_path(MAP_SPECIAL_ROOM)
boss_template = read_from_path(MAP_BOSS)
query_template = read_from_path(MAP_QUERY)
query_template1 = read_from_path(MAP_QUERY1)
elite_template = read_from_path(MAP_QUERY1)

LIUYUPUBU = "流雨瀑布"
FENGBAOYOUCHENG = "风暴幽城"
FENGBAONILIN = "风暴逆鳞普通"
DELUOSIKUANGSHAN = "德洛斯矿山外围"
DIEDANGQUNDAO = "跌宕群岛"
YAOQIZHUISHI = "妖气追踪"
SHENYUANZHONGMOU = "深渊：终末崇拜者"
HAIBOLUN = "海伯伦的预言所"
TONGYONG = "通用"
QITA = "其他"


RECT_MINMAPS = {
    LIUYUPUBU: (48, 48 + 54, 1067 - 6 - 126, 1067 - 6),
    FENGBAOYOUCHENG: (48, 48 + 54, 1067 - 6 - 108, 1067 - 6),
    FENGBAONILIN: (48, 48 + 54, 1067 - 6 - 108, 1067 - 6),
    DELUOSIKUANGSHAN: (52, 52 + 54, 1067 - 12 - 126, 1067 - 12),
    DIEDANGQUNDAO: (52, 52 + 54, 1067 - 12 - 126, 1067 - 12),
    YAOQIZHUISHI: (52, 52 + 54, 1067 - 12 - 126, 1067 - 12),
    TONGYONG: (52, 52 + 90, 1067 - 12 - 162, 1067 - 12),
    QITA: (48, 48 + 54, 1067 - 6 - 126, 1067 - 6),
    HAIBOLUN: None,
    SHENYUANZHONGMOU: None,
}

KEY_CODE_DICT = {
    "1": 49,
    "2": 50,
    "3": 51,
    "4": 52,
    "5": 53,
    "6": 54,
    "7": 55,
    "8": 56,
    "9": 57,
    "0": 48,
    "-": 189,
    "=": 187,
    "back": 8,
    "a": 65,
    "b": 66,
    "c": 67,
    "d": 68,
    "e": 69,
    "f": 70,
    "g": 71,
    "h": 72,
    "i": 73,
    "j": 74,
    "k": 75,
    "l": 76,
    "m": 77,
    "n": 78,
    "o": 79,
    "p": 80,
    "q": 81,
    "r": 82,
    "s": 83,
    "t": 84,
    "u": 85,
    "v": 86,
    "w": 87,
    "x": 88,
    "y": 89,
    "z": 90,
    "ctrl": 17,
    "alt": 18,
    "shift": 16,
    "win": 91,
    "space": 32,
    "cap": 20,
    "tab": 9,
    "~": 192,
    "esc": 27,
    "enter": 13,
    "up": 38,
    "down": 40,
    "left": 37,
    "right": 39,
    "option": 93,
    "print": 44,
    "delete": 46,
    "home": 36,
    "end": 35,
    "pgup": 33,
    "pgdn": 34,
    "f1": 112,
    "f2": 113,
    "f3": 114,
    "f4": 115,
    "f5": 116,
    "f6": 117,
    "f7": 118,
    "f8": 119,
    "f9": 120,
    "f10": 121,
    "f11": 122,
    "f12": 123,
    "[": 219,
    "]": 221,
    "\\": 220,
    ";": 186,
    "'": 222,
    ",": 188,
    ".": 190,
    "/": 191,
}

# 默认GUI配置
DEFAULT_GUI_CONFIG = {
    "ip": "127.0.0.1",
    "yjs": 0,
    "banzhuan": 0,
    "vmware_ip": "127.0.0.1",
    "vmware_prot": "5900",
    "vmware_password": "",
}