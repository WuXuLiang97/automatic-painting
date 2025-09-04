import logging
import random
import string
from PyQt5.QtWidgets import (
    QWidget,
    QStackedWidget,
    QVBoxLayout,
)
from PyQt5.QtCore import QTimer

from view.ChangePassword import ChangePasswordPage
from view.LoginPage import LoginPage
from view.Register import RegisterPage

class AuthApp(QWidget):
    def __init__(self):
        super().__init__()
        self.should_auto_login = False  # 自动登录标志
        self.remembered_user = None  # 记住的用户信息
        chars = string.ascii_letters + string.digits  # 大小写字母+数字
        random_string = "".join(random.choices(chars, k=10))
        self.setWindowTitle(random_string)
        self.setGeometry(500, 300, 400, 300)

        # 创建堆叠窗口
        self.stacked_widget = QStackedWidget()

        # 创建页面
        self.login_page = LoginPage(self.stacked_widget, self)
        self.register_page = RegisterPage(self.stacked_widget)
        self.change_password_page = ChangePasswordPage(
            self.stacked_widget
        )  # 添加修改密码页面

        # 添加页面到堆叠窗口
        self.stacked_widget.addWidget(self.login_page)
        self.stacked_widget.addWidget(self.register_page)
        self.stacked_widget.addWidget(self.change_password_page)  # 添加修改密码页面

        # 设置主布局
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

    def showEvent(self, event):
        """重写showEvent以处理自动登录"""
        super().showEvent(event)
        # 延迟执行自动登录，确保UI完全加载
        QTimer.singleShot(100, self.try_auto_login)

    def try_auto_login(self):
        """尝试自动登录"""
        if self.should_auto_login:
            logging.debug("触发自动登录")
            self.login_page.try_auto_login()
