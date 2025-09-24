# -*- coding: utf-8 -*-
"""Map domain module (Phase 1 scaffolding, iteration 1.1).

Now starts migrating real map logic out of PlayerThread. This controller
wraps PlayerThread but stores/derives state via MapState. For now only a
subset of pure-calculation helpers are implemented; combat / IO remain in
PlayerThread.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Tuple

from core.map.map_state import MapState
from core.common import a_mapInfo, a_DictInfo, Point  # type: ignore
from core.directional_astar import a_star  # type: ignore
from utils.log.logging_setup import logger  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
    from core.player import PlayerThread  # type: ignore

RoomId = Tuple[int, int]


class MapController:
    def __init__(self, pt: 'PlayerThread') -> None:
        self.pt = pt

    # --------------- lifecycle ---------------
    @property
    def state(self) -> MapState:
        return self.pt.map_state

    def init_map_layout(self, map_name: str) -> None:
        """Copy static layout into runtime state."""
        layout = a_mapInfo.get(map_name)
        if layout is None:
            logger.warning(f"No a_mapInfo entry for map: {map_name}")
            self.state.room_info_map = None
            return
        # deep copy (layout is small)
        self.state.room_info_map = [row[:] for row in layout]
        self.state.reset()
        logger.info(f"Map layout initialized for {map_name}")

    # --------------- query helpers ---------------
    def opened_rooms_count(self) -> int:
        return self.state.opened_rooms_count()

    # --------------- path / direction logic ---------------
    def find_path_to(self, target: Optional[RoomId]) -> Optional[str]:
        if not target:
            return None
        if not (self.state.player_room_id and self.state.room_info_map):
            return None
        priority_direction = "right"
        direction = a_star(
            self.state.room_info_map,
            self.state.player_room_id,
            target,
            priority_direction,
        )
        logger.debug(f"a_star result from {self.state.player_room_id} -> {target}: {direction}")
        return direction

    def path_to_boss(self) -> Optional[str]:
        return self.find_path_to(self.state.boss_room_id)

    def path_to_query(self) -> Optional[str]:
        return self.find_path_to(self.state.query_room_id)

    def path_to_elite(self) -> Optional[str]:
        return self.find_path_to(self.state.elite_room_id)

    def path_to_nearest_room_to_boss(self) -> Optional[str]:
        """Fallback: choose already-open (value==0) room closest to boss."""
        if not (self.state.boss_room_id and self.state.room_info_map):
            return None
        boss = self.state.boss_room_id
        # collect explored (value == 0)
        explored: list[RoomId] = []
        for i, row in enumerate(self.state.room_info_map):
            for j, v in enumerate(row):
                if v == 0:
                    explored.append((i, j))
        if not explored:
            return None
        best = None
        best_d = 1e9
        for r in explored:
            d = (r[0] - boss[0]) ** 2 + (r[1] - boss[1]) ** 2
            if d < best_d:
                best_d = d
                best = r
        if best is None:
            return None
        return self.find_path_to(best)

    def find_nearest_zero_to_target(self, target: RoomId) -> Optional[RoomId]:
        """Replicates old helper: nearest explored(0) room to target."""
        if not self.state.room_info_map:
            return None
        zero_coords: list[RoomId] = []
        for x in range(len(self.state.room_info_map)):
            for y in range(len(self.state.room_info_map[x])):
                if self.state.room_info_map[x][y] == 0:
                    zero_coords.append((x, y))
        if not zero_coords:
            return None
        min_distance = float('inf')
        nearest: Optional[RoomId] = None
        for coord in zero_coords:
            d2 = (coord[0] - target[0]) ** 2 + (coord[1] - target[1]) ** 2
            if d2 < min_distance:
                min_distance = d2
                nearest = coord
        return nearest

    # --------------- door position / direction ---------------
    def find_door_direction(self) -> Optional[str]:
        """Invoke legacy PlayerThread logic until fully migrated.
        If PlayerThread has migrated implementation, it'll still work.
        """
        if hasattr(self.pt, "find_door_direction"):
            # Avoid recursion if PlayerThread delegates back.
            # (Check attribute owner)
            return self.pt.__class__.__dict__.get("find_door_direction", lambda s: None)(self.pt)  # type: ignore
        return None

    def find_door_pos(self):  # kept signature for compatibility
        if hasattr(self.pt, "find_door_pos"):
            return self.pt.__class__.__dict__.get("find_door_pos", lambda s: None)(self.pt)  # type: ignore
        return None

__all__ = ["MapController"]