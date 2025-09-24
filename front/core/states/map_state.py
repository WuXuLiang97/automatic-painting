# -*- coding: utf-8 -*-
"""MapState (Phase 1 skeleton).
Tracks dynamic map-related fields currently stored on PlayerThread.
Wiring will be incremental; for now PlayerThread just instantiates it.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, List, Tuple

@dataclass
class MapState:
    room_info_map: Any = None  # matrix / list structure
    player_room_id: Optional[Tuple[int, int]] = None
    boss_room_id: Optional[Tuple[int, int]] = None
    query_room_id: Optional[Tuple[int, int]] = None
    elite_room_id: Optional[Tuple[int, int]] = None
    special_room_id: Optional[Tuple[int, int]] = None
    pass_room_id: list = field(default_factory=list)
