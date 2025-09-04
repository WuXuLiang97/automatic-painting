# -*- coding: utf-8 -*-
import sys
import logging
from PyQt5.QtWidgets import (
    QApplication,
)
from utils.font.font import load_application_font
from view.AuthApp import AuthApp

# 设置日志格式
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    load_application_font()
    window = AuthApp()
    window.show()
    sys.exit(app.exec_())
