from __future__ import annotations
from core.common import MoveInfo, Point, Player

# Movement & similarity utility functions extracted from player.py
# Phase 0 refactor: keep pure logic here so it can be unit tested later

def compute_move_info(player: Player, player_pos: Point, target_pos: Point, diff_x: int = 0, diff_y: int = 0):
    """Compute running movement info based on player speed.
    Returns MoveInfo or None if invalid inputs.
    """
    if (
        player_pos.x is None
        or player_pos.y is None
        or any(v is None or v <= 0 for v in [player_pos.x, player_pos.y, target_pos.x, target_pos.y])
    ):
        return None
    move_info = MoveInfo("left", "up", 0, 0, False)
    # X axis
    dx = abs(player_pos.x - target_pos.x)
    if dx > diff_x:
        delta = player.x_speed * 0.05
        if player_pos.x > target_pos.x and player_pos.x - target_pos.x > delta:
            move_info.leftRightDirection = "left"
        elif player_pos.x < target_pos.x and target_pos.x - player_pos.x > delta:
            move_info.leftRightDirection = "right"
        if player_pos.x < target_pos.x:
            move_info.isForward = True
        if dx > 200:
            move_info.isForward = True
        move_info.xTime = abs(player_pos.x - target_pos.x - diff_x) / player.x_speed
    # Y axis
    dy = abs(player_pos.y - target_pos.y)
    if dy > diff_y:
        if player_pos.y < target_pos.y:
            move_info.upDownDirection = "down"
        move_info.yTime = abs(player_pos.y - target_pos.y - diff_y) / player.y_speed
    return move_info


def compute_move_info_walk(player: Player, player_pos: Point, target_pos: Point, diff_x: int = 0, diff_y: int = 0):
    """Compute walking movement info (slower speed)."""
    if (
        player_pos.x is None
        or player_pos.y is None
        or any(v is None or v <= 0 for v in [player_pos.x, player_pos.y, target_pos.x, target_pos.y])
    ):
        return None
    move_info = MoveInfo("left", "up", 0, 0, False)
    dx = abs(player_pos.x - target_pos.x)
    if dx > diff_x:
        delta = player.x_speed_walk * 0.1
        if player_pos.x > target_pos.x and player_pos.x - target_pos.x > delta:
            move_info.leftRightDirection = "left"
        elif player_pos.x < target_pos.x and target_pos.x - player_pos.x > delta:
            move_info.leftRightDirection = "right"
        if player_pos.x < target_pos.x:
            move_info.isForward = True
        if dx > 200:
            move_info.isForward = True
        move_info.xTime = abs(player_pos.x - target_pos.x - diff_x) / player.x_speed_walk
    dy = abs(player_pos.y - target_pos.y)
    if dy > diff_y:
        if player_pos.y < target_pos.y:
            move_info.upDownDirection = "down"
        move_info.yTime = abs(player_pos.y - target_pos.y - diff_y) / player.y_speed_walk
    return move_info


def similarity(s1: str, s2: str) -> float:
    """Levenshtein similarity between two strings (0~1)."""
    if s1 == s2:
        return 1.0
    m, n = len(s1), len(s2)
    if m == 0 or n == 0:
        return 0.0 if m + n > 0 else 1.0
    # dp[i][j] = edit distance between s1[:i] and s2[:j]
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        c1 = s1[i - 1]
        for j in range(1, n + 1):
            c2 = s2[j - 1]
            cost = 0 if c1 == c2 else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # deletion
                dp[i][j - 1] + 1,      # insertion
                dp[i - 1][j - 1] + cost  # substitution
            )
    distance = dp[m][n]
    max_len = max(m, n)
    return 1 - distance / max_len if max_len > 0 else 1.0
