from __future__ import annotations
import os
import json
from dataclasses import dataclass  # removed unused 'field'
from typing import Dict, Any, Optional

from root_dir import root_path
# Import shared static map/data constants (centralized in map_data)
from .map_data import (
    pink_goods_info,
    MAP_MIN_ROOMS,
    map_boss_info,
    map_pos_info,
    a_mapInfo,
    a_DictInfo,
)

# --------------------------------------------------------------------------------------
# Lazy load occupation info (keep old global name for compatibility)
# --------------------------------------------------------------------------------------
_OCCUPATION_INFO_PATH = os.path.join(root_path, "res/occupation_info_1067.json")
_occupation_info_cache: Optional[Dict[str, Any]] = None

def load_occupation_info(force_reload: bool = False) -> Dict[str, Any]:
    """Load (or reload) occupation info JSON lazily.
    Exposed via the legacy name occupationInfoMap for backward compatibility.
    """
    global _occupation_info_cache
    if force_reload or _occupation_info_cache is None:
        try:
            with open(_OCCUPATION_INFO_PATH, "r", encoding="utf-8") as f:
                _occupation_info_cache = json.load(f)
        except FileNotFoundError:
            _occupation_info_cache = {}
    return _occupation_info_cache

# Backward compatible global (was eagerly loaded). Now a proxy object.
class _OccupationInfoProxy(dict):
    def __init__(self):  # type: ignore[override]
        super().__init__()
    def _refresh(self):
        data = load_occupation_info()
        super().clear()
        super().update(data)
    def __getitem__(self, item):  # type: ignore[override]
        if not self:
            self._refresh()
        return super().__getitem__(item)
    def get(self, key, default=None):  # type: ignore[override]
        if not self:
            self._refresh()
        return super().get(key, default)

occupationInfoMap: Dict[str, Any] = _OccupationInfoProxy()  # noqa: N816 (legacy casing)

# --------------------------------------------------------------------------------------
# Data structures
# --------------------------------------------------------------------------------------
@dataclass
class Point:
    x: int
    y: int

@dataclass
class Player:
    map_name: Optional[str] = None            # 地图名称
    map_level: Optional[int] = None           # 地图级别 (numeric after resolution)
    player_room_id: Optional[str] = None      # 玩家房间id
    player_occupation: Optional[str] = None   # 玩家_职业
    player_height: Optional[int] = None
    x_speed: Optional[int] = None
    y_speed: Optional[int] = None
    x_speed_walk: Optional[int] = None
    y_speed_walk: Optional[int] = None
    has_get_speed: bool = False               # 有速度标记
    is_daily_tasks: Optional[bool] = None
    pl_value: Optional[int] = None

@dataclass
class MoveInfo:
    leftRightDirection: str
    upDownDirection: str
    xTime: int
    yTime: int
    run: bool = False

# --------------------------------------------------------------------------------------
# Constants & configuration dictionaries
# Keep original variable names for external code compatibility
# --------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------
# Helper accessors
# --------------------------------------------------------------------------------------

def get_boss_height(map_name: str, boss_key: str, default: int = 0) -> int:
    return map_boss_info.get(map_name, {}).get(boss_key, {}).get('height', default)


def get_minimap_rect(map_name: str) -> Optional[Dict[str, int]]:
    return map_pos_info.get(map_name) or map_pos_info.get("通用")


__all__ = [
    'Point', 'Player', 'MoveInfo', 'mapLevelDict', 'pink_goods_info', 'MAP_MIN_ROOMS',
    'map_boss_info', 'map_pos_info', 'a_mapInfo', 'a_DictInfo', 'load_occupation_info',
    'occupationInfoMap', 'get_boss_height', 'get_minimap_rect'
]


if __name__ == '__main__':
    # Simple self-test / debug output
    print(get_boss_height("流雨瀑布", 'monster_lypb_min_boss_xgswzljl'))
    print(a_mapInfo.get("风暴逆鳞普通"))
    zero_count = sum(1 for row in a_mapInfo.get("风暴逆鳞普通", []) for e in row if e == 0)
    print("0的数量:", zero_count)
