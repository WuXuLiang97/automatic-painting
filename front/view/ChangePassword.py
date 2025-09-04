import json
import logging
import os
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

from config import REMEMBER_FILE
from utils.api import change_password, login


class ChangePasswordPage(QWidget):
    """修改密码页面"""

    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 标题
        title = QLabel("修改密码", self)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 30px;")

        # 用户名输入
        username_label = QLabel("用户名:")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")

        # 旧密码输入
        old_password_label = QLabel("旧密码:")
        self.old_password_input = QLineEdit()
        self.old_password_input.setPlaceholderText("请输入当前密码")
        self.old_password_input.setEchoMode(QLineEdit.Password)

        # 新密码输入
        new_password_label = QLabel("新密码:")
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("请输入新密码")
        self.new_password_input.setEchoMode(QLineEdit.Password)

        # 确认新密码
        confirm_label = QLabel("确认新密码:")
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("请再次输入新密码")
        self.confirm_input.setEchoMode(QLineEdit.Password)

        # 修改密码按钮
        change_pwd_btn = QPushButton("修改密码")
        change_pwd_btn.clicked.connect(self.change_password)

        # 创建底部按钮布局
        button_layout = QHBoxLayout()

        # 返回登录按钮
        back_btn = QPushButton("返回登录")
        back_btn.setStyleSheet(
            "color: blue; text-decoration: underline; border: none; background: transparent;"
        )
        back_btn.clicked.connect(self.go_to_login)

        # # 注册按钮
        # register_btn = QPushButton("注册账号")
        # register_btn.setStyleSheet("color: blue; text-decoration: underline; border: none; background: transparent;")
        # register_btn.clicked.connect(self.go_to_register)

        # 添加按钮到底部布局
        button_layout.addWidget(back_btn)
        button_layout.addStretch()
        # button_layout.addWidget(register_btn)

        # 添加组件到布局
        layout.addWidget(title)
        layout.addWidget(username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(old_password_label)
        layout.addWidget(self.old_password_input)
        layout.addWidget(new_password_label)
        layout.addWidget(self.new_password_input)
        layout.addWidget(confirm_label)
        layout.addWidget(self.confirm_input)
        layout.addWidget(change_pwd_btn)
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
                margin-top: 10px;n'n
                color: blue;
                text-decoration: underline;
            }
        """
        )

    def change_password(self):
        """处理修改密码请求"""
        username = self.username_input.text().strip()
        old_password = self.old_password_input.text().strip()
        new_password = self.new_password_input.text().strip()
        confirm_password = self.confirm_input.text().strip()

        # 验证输入
        if not username or not old_password or not new_password or not confirm_password:
            QMessageBox.warning(self, "输入错误", "所有字段不能为空")
            return

        if new_password != confirm_password:
            QMessageBox.warning(self, "输入错误", "两次输入的新密码不一致")
            return

        if old_password == new_password:
            QMessageBox.warning(self, "输入错误", "新密码不能与旧密码相同")
            return
        # 先登录获取cookies
        cookies = login(username, old_password)
        # 调用API修改密码
        logging.debug(f"尝试修改密码: {username}")
        ret = change_password(cookies, old_password, new_password)

        # 检查修改是否成功
        if ret.get("error"):
            logging.warning(f"修改密码失败: {ret.get('error')}")
            QMessageBox.critical(self, "修改密码失败", ret.get("error"))
            return

        # 修改成功
        logging.info(f"密码修改成功: {username}")
        QMessageBox.information(self, "修改成功", "密码已成功修改！")

        # 清除记住的密码（如果存在）
        if os.path.exists(REMEMBER_FILE):
            try:
                with open(REMEMBER_FILE, "r") as f:
                    data = json.load(f)
                    if data.get("username") == username:
                        os.remove(REMEMBER_FILE)
                        logging.debug("已清除记住的密码")
            except:
                pass

        # 返回登录页面
        self.go_to_login()

    def go_to_login(self):
        # 清空输入框
        self.username_input.clear()
        self.old_password_input.clear()
        self.new_password_input.clear()
        self.confirm_input.clear()

        self.stacked_widget.setCurrentIndex(0)  # 切换到登录页面

    def go_to_register(self):
        # 清空输入框
        self.username_input.clear()
        self.old_password_input.clear()
        self.new_password_input.clear()
        self.confirm_input.clear()

        self.stacked_widget.setCurrentIndex(1)  # 切换到注册页面
