

import json
import logging
import os
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
)
from PyQt5.QtCore import Qt
from config import USER_DATA_FILE
from utils.api import register

class RegisterPage(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 标题
        title = QLabel("用户注册", self)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 30px;")

        # 用户名输入
        username_label = QLabel("用户名:")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")

        # 密码输入
        password_label = QLabel("密码:")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)

        # 确认密码
        confirm_label = QLabel("确认密码:")
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("请再次输入密码")
        self.confirm_input.setEchoMode(QLineEdit.Password)

        # 注册按钮
        register_btn = QPushButton("注册")
        register_btn.clicked.connect(self.register)

        # 创建底部按钮布局
        button_layout = QHBoxLayout()

        # 返回登录按钮
        back_btn = QPushButton("返回登录")
        back_btn.setStyleSheet(
            "color: blue; text-decoration: underline; border: none; background: transparent;"
        )
        back_btn.clicked.connect(self.go_to_login)

        # # 修改密码按钮
        # change_pwd_btn = QPushButton("修改密码")
        # change_pwd_btn.setStyleSheet("color: blue; text-decoration: underline; border: none; background: transparent;")
        # change_pwd_btn.clicked.connect(self.go_to_change_password)

        # 添加按钮到底部布局
        button_layout.addWidget(back_btn)
        button_layout.addStretch()
        # button_layout.addWidget(change_pwd_btn)

        # 添加组件到布局
        layout.addWidget(title)
        layout.addWidget(username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)
        layout.addWidget(confirm_label)
        layout.addWidget(self.confirm_input)
        layout.addWidget(register_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 设置全局样式
        self.setStyleSheet(
            """
            QWidget {
                font-family: 'Microsoft YaHei';
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-bottom: 15px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border: none;
                border-radius: 4px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QCheckBox {
                margin-top: 5px;
                margin-bottom: 15px;
            }
            QPushButton[style*="background: transparent"] {
                background: transparent;
                padding: 5px;
                margin-top: 10px;
                color: blue;
                text-decoration: underline;
            }
        """
        )

    def register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        confirm = self.confirm_input.text().strip()

        # 验证输入
        if not username or not password or not confirm:
            QMessageBox.warning(self, "输入错误", "所有字段不能为空")
            return

        if password != confirm:
            QMessageBox.warning(self, "输入错误", "两次输入的密码不一致")
            return

        logging.debug(f"尝试注册: {username}")
        ret = register(username, password)

        # 检查用户名是否已存在
        if ret.get("error"):
            logging.warning(f"注册失败: {ret.get('error')}")
            QMessageBox.warning(self, "注册失败", ret.get("error"))
            return

        # 保存用户信息
        self.save_user(username, password)
        logging.info(f"注册成功: {username}")
        QMessageBox.information(self, "注册成功", "账号创建成功！")
        self.go_to_login()

    def user_exists(self, username):
        """检查用户是否存在"""
        if not os.path.exists(USER_DATA_FILE):
            return False

        try:
            with open(USER_DATA_FILE, "r") as f:
                users = json.load(f)
                return username in users
        except:
            return False

    def save_user(self, username, password):
        """保存用户信息到文件"""
        users = {}
        if os.path.exists(USER_DATA_FILE):
            try:
                with open(USER_DATA_FILE, "r") as f:
                    users = json.load(f)
            except:
                pass

        users[username] = password

        with open(USER_DATA_FILE, "w") as f:
            json.dump(users, f)
        logging.debug(f"用户保存成功: {username}")

    def go_to_login(self):
        # 清空输入框
        self.username_input.clear()
        self.password_input.clear()
        self.confirm_input.clear()

        self.stacked_widget.setCurrentIndex(0)  # 切换到登录页面

    def go_to_change_password(self):
        self.stacked_widget.setCurrentIndex(2)  # 切换到修改密码页面
        # 预填充用户名
        self.parent().change_password_page.username_input.setText(
            self.username_input.text().strip()
        )
