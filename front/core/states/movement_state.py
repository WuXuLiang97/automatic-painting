# -*- coding: utf-8 -*-
"""MovementState (Phase 1 introduction).

Holds movement/combat shared positional lists. Currently not yet wired to
replace direct PlayerThread attribute access; it is instantiated and
populated for progressive migration.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from core.common import Point

@dataclass
class MovementState:
    player_pos: Point = field(default_factory=lambda: Point(None, None))
    monsters: List = field(default_factory=list)   # List[Tuple[x,y,...]]
    doors: List = field(default_factory=list)
    goods: List = field(default_factory=list)
    box: List = field(default_factory=list)
    is_boss: bool = False
