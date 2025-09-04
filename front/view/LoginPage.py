import logging
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QCheckBox,
)
from PyQt5.QtCore import Qt
from view.bis.callMain import AppMain
from utils.api import login
from utils.user.user import (
    load_remembered_user,
    save_remembered_user,
    update_remembered_auto_login,
)


class LoginPage(QWidget):
    def __init__(self, stacked_widget, parent_app):
        super().__init__()
        self.main_app = None
        self.stacked_widget = stacked_widget
        self.parent_app = parent_app
        self.auto_login_attempted = False  # 标记是否已尝试自动登录
        self.initUI()
        self.load_remembered_user()
        self.username = ""

    def initUI(self):
        layout = QVBoxLayout()

        # 标题
        title = QLabel("用户登录", self)
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

        # 记住密码复选框
        self.remember_checkbox = QCheckBox("记住密码")
        self.remember_checkbox.setChecked(True)

        # 自动登录复选框
        self.auto_login_checkbox = QCheckBox("自动登录")
        # 连接状态改变信号到更新函数
        self.auto_login_checkbox.stateChanged.connect(self.handle_auto_login_change)

        # 关联复选框状态
        self.remember_checkbox.stateChanged.connect(self.handle_update_checkbox_states)
        self.remember_checkbox.stateChanged.connect(self.handle_remember_change)

        # 登录按钮
        login_btn = QPushButton("登录")
        login_btn.clicked.connect(self.handle_login)

        # 创建底部按钮布局
        button_layout = QHBoxLayout()

        # 注册按钮
        register_btn = QPushButton("注册账号")
        register_btn.setStyleSheet(
            "color: blue; text-decoration: underline; border: none; background: transparent;"
        )
        register_btn.clicked.connect(self.go_to_register)

        # 修改密码按钮
        change_pwd_btn = QPushButton("修改密码")
        change_pwd_btn.setStyleSheet(
            "color: blue; text-decoration: underline; border: none; background: transparent;"
        )
        change_pwd_btn.clicked.connect(self.go_to_change_password)

        # 添加按钮到底部布局
        button_layout.addWidget(register_btn)
        button_layout.addStretch()
        button_layout.addWidget(change_pwd_btn)

        # 创建复选框布局
        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(self.remember_checkbox)
        checkbox_layout.addWidget(self.auto_login_checkbox)
        checkbox_layout.addStretch()

        # 添加组件到布局
        layout.addWidget(title)
        layout.addWidget(username_label)
        layout.addWidget(self.username_input)
        layout.addWidget(password_label)
        layout.addWidget(self.password_input)
        layout.addLayout(checkbox_layout)
        layout.addWidget(login_btn)
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

    def handle_remember_change(self, state):
        """处理记住密码复选框状态改变"""
        # 如果取消记住密码，自动登录也必须取消
        if (
            not self.remember_checkbox.isChecked()
            and self.auto_login_checkbox.isChecked()
        ):
            self.auto_login_checkbox.setChecked(False)

    def handle_auto_login_change(self, state):
        """处理自动登录复选框状态改变"""
        username = self.username_input.text().strip()
        if not username:
            return

        # 如果当前用户是记住的用户，立即更新配置文件
        if (
            self.parent_app.remembered_user
            and self.parent_app.remembered_user["username"] == username
        ):
            auto_login = self.auto_login_checkbox.isChecked()
            update_remembered_auto_login(username, auto_login)
            logging.debug(f"已更新 {username} 的自动登录设置: {auto_login}")
        else:
            # 对于新用户，设置会在登录时保存
            logging.debug(f"用户 {username} 的自动登录设置将在登录时保存")

    def handle_update_checkbox_states(self):
        """更新复选框状态之间的依赖关系"""
        # 如果取消记住密码，自动登录也必须取消
        if not self.remember_checkbox.isChecked():
            self.auto_login_checkbox.setChecked(False)

        # 如果选择自动登录，必须同时记住密码
        if self.auto_login_checkbox.isChecked():
            self.remember_checkbox.setChecked(True)

    def load_remembered_user(self):
        """加载记住的用户信息到输入框"""
        remembered = load_remembered_user()
        if remembered:
            logging.debug(f"加载记住的用户: {remembered['username']}")
            self.username_input.setText(remembered["username"])
            self.password_input.setText(remembered["password"])
            self.remember_checkbox.setChecked(remembered["remember"])

            # 记录记住的用户信息
            self.parent_app.remembered_user = remembered

            # 加载自动登录状态
            auto_login = remembered.get("auto_login", False)
            self.auto_login_checkbox.setChecked(auto_login)

            # 标记需要自动登录
            self.parent_app.should_auto_login = auto_login
            logging.debug(f"设置自动登录标志: {auto_login}")

    def try_auto_login(self):
        """尝试自动登录"""
        if self.parent_app.should_auto_login and not self.auto_login_attempted:
            logging.debug("尝试自动登录...")
            self.auto_login_attempted = True
            self.handle_login()

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "输入错误", "用户名和密码不能为空")
            return

        # 调用API测试登录
        logging.debug(f"尝试登录: {username}")
        ret = login(username, password)
        logging.debug(f"登录返回: {ret}")

        # 根据API返回结果处理
        if ret:
            # 保存记住密码和自动登录设置
            save_remembered_user(
                username,
                password,
                self.remember_checkbox.isChecked(),
                self.auto_login_checkbox.isChecked(),
            )
            self.username = username
            # 登录成功
            logging.info(f"登录成功: {username}")
            # QMessageBox.information(self, "登录成功", f"欢迎回来, {username}!")
            dic = {"username": username, "cookies": ret}

            self.main_app = AppMain(dic=dic)
            self.main_app.show()
            self.main_app.authapp = self.window()
            # 关闭登录窗口
            self.window().hide()  # 关闭整个登录窗口
        else:
            # 登录失败
            error_msg = ret.get("message", "用户名或密码错误")
            logging.warning(f"登录失败: {error_msg}")
            QMessageBox.critical(self, "登录失败", error_msg)

    def go_to_register(self):
        self.stacked_widget.setCurrentIndex(1)  # 切换到注册页面

    def go_to_change_password(self):
        self.stacked_widget.setCurrentIndex(2)  # 切换到修改密码页面
        # 预填充用户名
        self.parent_app.change_password_page.username_input.setText(
            self.username_input.text().strip()
        )
