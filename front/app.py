# -*- coding: utf-8 -*-
import sys
import logging
import os
from PyQt5.QtWidgets import (
    QApplication,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QSharedMemory, QSystemSemaphore
from utils.font.font import load_application_font
from view.AuthApp import AuthApp
from core.logger import init_logging, get_logger
from config import f_program_version, DEBUG_MODE

APP_KEY = "dxf_auto_single_instance_key"
SEMAPHORE_KEY = "dxf_auto_single_instance_sem"


def install_exception_hook():
    def handle_exception(exctype, value, tb):
        logging.exception("Uncaught exception", exc_info=(exctype, value, tb))
        QMessageBox.critical(None, "错误", f"发生未捕获异常: {value}")
    sys.excepthook = handle_exception


def ensure_single_instance():
    semaphore = QSystemSemaphore(SEMAPHORE_KEY, 1)
    semaphore.acquire()
    shared = QSharedMemory(APP_KEY)
    already_running = False
    if not shared.create(1):
        already_running = True
    semaphore.release()
    if already_running:
        QMessageBox.information(None, "提示", "程序已在运行中。")
        return False
    return True


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    # Initialize unified logging (idempotent)
    init_logging()
    log = get_logger(__name__)
    log.info("Application starting | version=%s | debug=%s", f_program_version, DEBUG_MODE)
    app = QApplication(sys.argv)
    install_exception_hook()
    load_application_font()
    if not ensure_single_instance():
        return 0
    window = AuthApp()
    window.show()
    try:
        return app.exec_()
    except Exception:
        log.exception("Runtime exception in QApplication event loop")
        return 1
    finally:
        log.info("Application exiting")


if __name__ == "__main__":
    sys.exit(main())
