from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, Optional, List
import time

try:
    # 复用现有日志（若已切到统一 logger，可替换引用）
    from utils.log.logging_setup import logger  # type: ignore
except Exception:  # 回退
    import logging
    logger = logging.getLogger(__name__)

# PlayerThread 类型提示（避免循环导入，仅用于类型检查）
if False:  # pragma: no cover
    from core.player import PlayerThread  # noqa


@dataclass
class MapHandler:
    """单一地图处理策略。
    enter: 进入地图/副本的流程，成功返回 True
    room_flow: 刷图房间推进（可选，暂未接入）
    """
    name: str
    enter: Callable[["PlayerThread"], bool]
    room_flow: Optional[Callable[["PlayerThread"], None]] = None


_HANDLERS: Dict[str, MapHandler] = {}


def register_map(name: str, aliases: Optional[List[str]] = None):
    """装饰器注册地图进入策略。
    用法:
    @register_map("风暴幽城")
    def enter_fbyc(pt: PlayerThread) -> bool: ...
    """
    aliases = aliases or []

    def _decorator(func: Callable[["PlayerThread"], bool]):
        handler = MapHandler(name=name, enter=func)
        keys = {name.lower(), *(a.lower() for a in aliases)}
        for k in keys:
            _HANDLERS[k] = handler
        logger.debug(f"注册地图策略: {name} (含别名: {aliases})")
        return func

    return _decorator


# ------------------ 默认/兜底策略 ------------------

def _default_enter(pt: "PlayerThread") -> bool:
    """默认进入地图逻辑（兜底）。
    仅尝试: 关闭弹窗 -> 点击传送阵 -> 返回 True/False
    真实地图选中逻辑仍由旧条件代码保留（后续逐步迁移）。
    """
    try:
        # 若存在关闭按钮尝试关闭 (依赖 FindPic，可选)
        try:
            from utils.common.image import FindPic  # 延迟导入
            ret = FindPic(
                pt.vnc_connection.capture(x1=0, y1=0, x2=1067, y2=600),
                0,
                0,
                1067,
                600,
                "关闭.bmp",
                0.9,
            )
            if ret:
                logger.debug("发现关闭弹窗，后续可添加点击逻辑")
        except Exception:
            pass

        if not pt.operator_module.click_menu_item("传送阵"):
            logger.debug("点击传送阵失败")
            return False
        # 占位：具体地图定位 / 难度选择 / 进入按键 未来拆分
        logger.info(f"[默认策略] 进入地图占位: {pt.player.map_name}")
        return True
    except Exception as e:
        logger.warning(f"默认进入策略异常: {e}")
        return False


_DEFAULT_HANDLER = MapHandler(name="__default__", enter=_default_enter)


def get_map_handler(map_name: Optional[str]) -> MapHandler:
    if not map_name:
        return _DEFAULT_HANDLER
    return _HANDLERS.get(map_name.lower(), _DEFAULT_HANDLER)


# ------------------ 预注册当前已知地图 (指向默认逻辑，可逐步替换) ------------------
for _n in [
    "风暴幽城",
    "风暴逆鳞普通",
    "流雨瀑布",
    "海伯伦的预言所",
    "深渊：终末崇拜者",
    "跌宕群岛",
    "妖气追踪",
    "德洛斯矿山外围",
]:
    if _n.lower() not in _HANDLERS:
        _HANDLERS[_n.lower()] = MapHandler(name=_n, enter=_default_enter)


# ------------------ 示例：自定义地图策略占位 ------------------
@register_map("深渊：终末崇拜者")
def enter_shenyuan(pt: "PlayerThread") -> bool:
    """示例: 深渊特殊进入逻辑 (当前占位，后续补充真实步骤)。"""
    logger.info("[策略] 深渊：终末崇拜者 进入逻辑开始")
    ok = _default_enter(pt)
    # TODO: 添加深渊特有票据检测 / 难度 / 传送坐标点击
    return ok


@register_map("德洛斯矿山外围")
def enter_kuangshan(pt: "PlayerThread") -> bool:
    logger.info("[策略] 德洛斯矿山外围 进入逻辑开始")
    ok = _default_enter(pt)
    # TODO: 若矿山不使用传送阵，可在此改为寻路/走到NPC后打开面板
    return ok


__all__ = [
    "MapHandler",
    "register_map",
    "get_map_handler",
]