# -*- coding: utf-8 -*-
"""Combat controller (Phase 1 skeleton -> partial extraction).

Adds CombatState (dataclass) to begin migrating mutable combat fields out
of PlayerThread in later steps. For now we only expose a dry_run_rotation
helper to validate future skill order logic without side effects.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Optional
from dataclasses import dataclass, field

if TYPE_CHECKING:  # pragma: no cover
    from core.player import PlayerThread  # type: ignore


@dataclass
class CombatState:
    last_skill_times: dict = field(default_factory=dict)
    boss_mode: bool = False
    rotation_index: int = 0
    # future: track target HP snapshots, immunity flags, etc.


class CombatController:
    def __init__(self, pt: 'PlayerThread') -> None:
        self.pt = pt
        self.state = CombatState()

    # Delegations (still using PlayerThread implementations)
    def process_pass(self):
        return self.pt.process_pass()

    def attach_monster(self):
        return self.pt.attach_monster()

    def process_boss_room(self):
        return self.pt.process_boss_room()

    def release_buffer(self):
        return self.pt.release_buffer()

    def move_to_monster(self):  # shared with movement but logically combat positioning
        return self.pt.move_to_monster()

    def agg_pick_up_goods(self):  # boss loot aggregation
        return self.pt.agg_pick_up_goods()

    # ---- Phase 1 test hook ----
    def dry_run_rotation(self, skills: List[str]) -> List[str]:
        """Return an execution order preview (no real key presses).
        Placeholder now simply echoes while skipping empty entries.
        """
        return [s for s in skills if s]