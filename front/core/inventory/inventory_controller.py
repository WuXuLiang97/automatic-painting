# -*- coding: utf-8 -*-
"""Inventory controller (Phase 1 skeleton).

Handles storage / selling / daily tasks / access operations via delegation.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from core.player import PlayerThread  # type: ignore


class InventoryController:
    def __init__(self, pt: 'PlayerThread') -> None:
        self.pt = pt

    def deposit_goods(self):
        return self.pt.deposit_goods()

    def sell(self):
        return self.pt.sell()

    def daily_tasks(self):
        return self.pt.daily_tasks()

    def access(self):
        return self.pt.access()

    def access_0(self):
        return self.pt.access_0()

    def auto_pick(self):
        return self.pt.auto_pick()

    def agg_pick_up_goods(self):
        return self.pt.agg_pick_up_goods()  # shared with combat (loot logic)