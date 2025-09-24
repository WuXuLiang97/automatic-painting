# -*- coding: utf-8 -*-
"""Map state container.

Encapsulates mutable, runtime map exploration state so logic can migrate
out of PlayerThread. Phase 1 minimal fields only; future phases may move
more responsibilities (path cache, timestamps, etc.).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

RoomId = Tuple[int, int]

@dataclass
class MapState:
    # Full A* map layout (copied from a_mapInfo[map_name])
    room_info_map: Optional[List[List[int]]] = None

    # Dynamic discovered rooms
    boss_room_id: Optional[RoomId] = None
    query_room_id: Optional[RoomId] = None  # 问号房
    elite_room_id: Optional[RoomId] = None  # 精英房
    special_room_id: Optional[RoomId] = None  # 终点 / 特殊
    player_room_id: Optional[RoomId] = None

    # Cache for last chosen direction per room to avoid recomputation
    direction_cache: Dict[RoomId, str] = field(default_factory=dict)

    def reset(self):
        self.boss_room_id = None
        self.query_room_id = None
        self.elite_room_id = None
        self.special_room_id = None
        self.player_room_id = None
        self.direction_cache.clear()

    def opened_rooms_count(self) -> int:
        if not self.room_info_map:
            return 0
        count = 0
        for row in self.room_info_map:
            for v in row:
                if v == 0:
                    count += 1
        return count

__all__ = ["MapState", "RoomId"]
