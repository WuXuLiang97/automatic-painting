import os
from PyQt5 import QtGui, QtWidgets
from config import FONT_FILE


def load_application_font(size=10, widget=None):
    """
    加载应用程序字体（优先自定义字体，找不到则用微软雅黑）
    :param size: 字体大小，默认10
    :param widget: 可选，指定控件设置字体，否则全局设置
    :return: 是否加载自定义字体成功
    """
    if os.path.exists(FONT_FILE):
        font_id = QtGui.QFontDatabase.addApplicationFont(FONT_FILE)
        if font_id != -1:
            font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                app_font = QtGui.QFont(font_families[0])
                app_font.setPointSize(size)
                if widget is None:
                    QtWidgets.QApplication.setFont(app_font)
                else:
                    widget.setFont(app_font)
                return True
    # 如果找不到自定义字体，则使用系统微软雅黑
    font = QtGui.QFont("Microsoft YaHei")
    font.setPointSize(9)
    QtWidgets.QApplication.setFont(font)
    return False
