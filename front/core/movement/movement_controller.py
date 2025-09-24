# -*- coding: utf-8 -*-
"""Movement controller (Phase 1 extraction).

Phase 1 objective: progressively move movement related pure/low‑level logic
out of PlayerThread so later phases (state machine, testability) become easier.

Currently fully migrated:
- compute_move_info
- compute_move_info_walk

Still delegating (pending body migration – original implementations remain
in PlayerThread until verified):
- move_to_monster
- player_left_right_move
- clearingobstacles
- get_move_speed (UI / OCR heavy, defer)

After verification we will: (1) move remaining bodies here, (2) replace
PlayerThread methods with thin wrappers calling this controller.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass

if TYPE_CHECKING:  # pragma: no cover
    from core.player import PlayerThread  # type: ignore
    from core.common import MoveInfo, Point  # type: ignore


@dataclass
class MovementConfig:
    """Configuration / tweakable coefficients (extracted from magic numbers)."""
    high_dx_threshold: int = 200  # when to treat as long horizontal move
    walk_delta_factor: float = 0.1  # factor used in walk speed delta calc
    run_delta_factor: float = 0.05  # factor used in run speed delta calc


class MovementController:
    def __init__(self, pt: 'PlayerThread') -> None:
        self.pt = pt
        self.cfg = MovementConfig()

    # ---------------- Pure calculations (migrated) ----------------
    def compute_move_info(self, player_pos, target_pos, diff_x: int, diff_y: int):
        """Compute movement (run) toward a target.

        Migrated unchanged from PlayerThread.compute_move_info (Phase 1).
        Returns a MoveInfo or None if inputs invalid.
        """
        # 输入校验
        if (
            player_pos.x is None
            or player_pos.y is None
            or any(v <= 0 for v in [player_pos.x, player_pos.y, target_pos.x, target_pos.y])
        ):
            return None

        from core.common import MoveInfo  # local import to avoid cycles
        move_info = MoveInfo("left", "up", 0, 0, False)

        # X 方向
        dx = abs(player_pos.x - target_pos.x)
        if dx > diff_x:
            delta = self.pt.player.x_speed * self.cfg.run_delta_factor
            if player_pos.x > target_pos.x and player_pos.x - target_pos.x > delta:
                # face left
                move_info.leftRightDirection = "left"
            elif player_pos.x < target_pos.x and target_pos.x - player_pos.x > delta:
                move_info.leftRightDirection = "right"
            if player_pos.x < target_pos.x:
                move_info.faceDirection = "right"
            if dx > self.cfg.high_dx_threshold:
                move_info.longDistance = True
            move_info.xTime = abs(player_pos.x - target_pos.x - diff_x) / self.pt.player.x_speed

        # Y 方向
        dy = abs(player_pos.y - target_pos.y)
        if dy > diff_y:
            if player_pos.y < target_pos.y:
                move_info.upDownDirection = "down"
            move_info.yTime = abs(player_pos.y - target_pos.y - diff_y) / self.pt.player.y_speed
        return move_info

    def compute_move_info_walk(self, player_pos, target_pos, diff_x: int, diff_y: int):
        """Compute movement (walk) variant.

        Migrated unchanged from PlayerThread.compute_move_info_walk.
        """
        if (
            player_pos.x is None
            or player_pos.y is None
            or any(v <= 0 for v in [player_pos.x, player_pos.y, target_pos.x, target_pos.y])
        ):
            return None
        from core.common import MoveInfo  # local import to avoid cycles
        move_info = MoveInfo("left", "up", 0, 0, False)
        dx = abs(player_pos.x - target_pos.x)
        if dx > diff_x:
            delta = self.pt.player.x_speed_walk * self.cfg.walk_delta_factor
            if player_pos.x > target_pos.x and player_pos.x - target_pos.x > delta:
                move_info.leftRightDirection = "left"
            elif player_pos.x < target_pos.x and target_pos.x - player_pos.x > delta:
                move_info.leftRightDirection = "right"
            if player_pos.x < target_pos.x:
                move_info.faceDirection = "right"
            if dx > self.cfg.high_dx_threshold:
                move_info.longDistance = True
            move_info.xTime = abs(player_pos.x - target_pos.x - diff_x) / self.pt.player.x_speed_walk
        dy = abs(player_pos.y - target_pos.y)
        if dy > diff_y:
            if player_pos.y < target_pos.y:
                move_info.upDownDirection = "down"
            move_info.yTime = abs(player_pos.y - target_pos.y - diff_y) / self.pt.player.y_speed_walk
        return move_info

    # ---------------- Still delegating (bodies not yet migrated) ----------------
    def get_move_speed(self):  # heavy UI / OCR side effects – defer
        return self.pt.get_move_speed()

    def move_to_monster(self):
        return self.pt.move_to_monster()

    def player_left_right_move(self):
        return self.pt.player_left_right_move()

    def clearingobstacles(self):  # keep original spelling
        return self.pt.clearingobstacles()

    # ---------------- Dry-run helpers (Phase 1 test hooks) ----------------
    def dry_run_path(self, player_x: int, player_y: int, target_x: int, target_y: int) -> Optional[dict]:
        """Pure function style preview used for early unit tests.
        Returns dict summary instead of mutating any real state.
        """
        from core.common import Point  # lazy import
        p_pos = Point(player_x, player_y)
        t_pos = Point(target_x, target_y)
        mi = self.compute_move_info(p_pos, t_pos, 0, 0)
        if mi is None:
            return None
        return {
            "lr": mi.leftRightDirection,
            "ud": mi.upDownDirection,
            "xTime": round(mi.xTime, 3),
            "yTime": round(mi.yTime, 3),
            "long": mi.longDistance,
            "face": getattr(mi, 'faceDirection', None),
        }
