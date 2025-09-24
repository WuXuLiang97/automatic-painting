# -*- coding: utf-8 -*-
"""Application layer.

编排用例 / 流程：聚合 domain + infrastructure，隔离上层 UI。
后续放置：
- game_loop.py (主循环)
- services/ (组合多个 infrastructure 以提供更粗粒度用例)
- controllers/ (状态机驱动器、命令接口)
"""
