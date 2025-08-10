import traceback

import win32gui
from LogDebug import logger


def get_hwnd():
    dnf_hwnd = win32gui.FindWindow('地下城与勇士', '地下城与勇士：创新世纪')
    if dnf_hwnd != 0:
        logger.info("地下城与勇士：创新世纪窗口的句柄:", dnf_hwnd)
    return dnf_hwnd


try:
    hwnd = get_hwnd()

except Exception as e:
    logger.exception(f"player模块:{e}")
    traceback.print_exc()
