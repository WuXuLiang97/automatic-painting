# -*- coding: utf-8 -*-
import random
import sys
import json
import base64
import logging
import string

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtWidgets import (QApplication, QWidget, QStackedWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox, QCheckBox)
from PyQt5.QtCore import Qt, QTimer
from utils.api import test_login, test_register, test_change_password  # 添加修改密码API
# 这里可以添加跳转到主界面的代码
from core.callMain import AppMain
from root_dir import root_path

# 设置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
import os
target_dir = os.path.join(r"C:\Program Files", "json_resources")  # 拼接子目录
# 用户数据存储文件
USER_DATA_FILE = os.path.join(target_dir, 'users.json')
# 记住密码的配置文件
REMEMBER_FILE = os.path.join(target_dir, 'remember.json')


def encrypt_password(password):
    """简单的密码加密（Base64编码）"""
    return base64.b64encode(password.encode()).decode()


def decrypt_password(encrypted):
    """解密密码"""
    try:
        return base64.b64decode(encrypted.encode()).decode()
    except:
        logging.error("密码解密失败")
        return ""


def load_remembered_user():
    """加载记住的用户信息"""
    if not os.path.exists(REMEMBER_FILE):
        logging.debug("没有找到记住密码文件")
        return None

    try:
        with open(REMEMBER_FILE, "r") as f:
            data = json.load(f)
            logging.debug(f"从文件加载记住的用户: {data['username']}")

            # 解密密码
            data["password"] = decrypt_password(data["password"])
            print(f"密码{data['password']}")
            return data
    except Exception as e:
        logging.error(f"加载记住的用户失败: {str(e)}")
        return None


def save_remembered_user(username, password, remember, auto_login):
    """保存记住的用户信息"""
    try:
        if remember:
            # 加密密码
            encrypted = encrypt_password(password)
            data = {"username": username, "password": encrypted, "remember": remember, "auto_login": auto_login}

            with open(REMEMBER_FILE, "w") as f:
                json.dump(data, f)
            logging.debug(f"保存记住的用户: {username}, 自动登录: {auto_login}")
        else:
            # 如果不记住密码，删除文件
            if os.path.exists(REMEMBER_FILE):
                os.remove(REMEMBER_FILE)
                logging.debug("删除记住密码文件")
    except Exception as e:
        logging.error(f"保存记住的用户失败: {str(e)}")


def update_remembered_auto_login(username, new_auto_login_state):
    """仅更新 remember.json 中的 auto_login 字段"""
    if not os.path.exists(REMEMBER_FILE):
        logging.warning("记住密码文件不存在，无法更新 auto_login")
        return False
    try:
        # 读取现有数据
        with open(REMEMBER_FILE, "r") as f:
            data = json.load(f)

        # 检查用户名是否匹配（避免误更新其他用户的配置）
        if data.get("username") != username:
            logging.warning(f"用户名不匹配，无法更新 {username} 的 auto_login")
            return False

        # 更新 auto_login 字段
        data["auto_login"] = new_auto_login_state

        # 写回更新后的数据（保持密码和其他字段不变）
        with open(REMEMBER_FILE, "w") as f:
            json.dump(data, f)

        logging.debug(f"更新 {username} 的 auto_login 为: {new_auto_login_state}")
        return True

    except Exception as e:
        logging.error(f"更新 auto_login 失败: {str(e)}")
        return False


def load_application_font(size=10, widget=None):
    font_path = os.path.join(root_path, "utils", "Arial.ttf")
    if os.path.exists(font_path):
        font_id = QtGui.QFontDatabase.addApplicationFont(font_path)
        if font_id != -1:
            font_families = QtGui.QFontDatabase.applicationFontFamilies(font_id)
            if font_families:
                app_font = QtGui.QFont(font_families[0])
                app_font.setPointSize(size)
                if widget is None:
                    # 设置应用程序全局字体
                    QtWidgets.QApplication.setFont(app_font)
                else:
                    widget.setFont(app_font)
                return True
    # 回退到系统字体
    font = QtGui.QFont("Microsoft YaHei")
    font.setPointSize(9)
    QtWidgets.QApplication.setFont(font)
    return False


class LoginPage(QWidget):
    def __init__(self, stacked_widget, parent_app):
        super().__init__()
        self.main_app = None
        self.stacked_widget = stacked_widget
        self.parent_app = parent_app
        self.auto_login_attempted = False  # 标记是否已尝试自动登录
        self.initUI()
        self.load_remembered_user()
        self.username = ''

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
        self.remember_checkbox.stateChanged.connect(self.update_checkbox_states)
        self.remember_checkbox.stateChanged.connect(self.handle_remember_change)

        # 登录按钮
        login_btn = QPushButton("登录")
        login_btn.clicked.connect(self.login)

        # 创建底部按钮布局
        button_layout = QHBoxLayout()

        # 注册按钮
        register_btn = QPushButton("注册账号")
        register_btn.setStyleSheet("color: blue; text-decoration: underline; border: none; background: transparent;")
        register_btn.clicked.connect(self.go_to_register)

        # 修改密码按钮
        change_pwd_btn = QPushButton("修改密码")
        change_pwd_btn.setStyleSheet("color: blue; text-decoration: underline; border: none; background: transparent;")
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
        self.setStyleSheet("""
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
        """)

    def handle_remember_change(self, state):
        """处理记住密码复选框状态改变"""
        # 如果取消记住密码，自动登录也必须取消
        if not self.remember_checkbox.isChecked() and self.auto_login_checkbox.isChecked():
            self.auto_login_checkbox.setChecked(False)

    def handle_auto_login_change(self, state):
        """处理自动登录复选框状态改变"""
        username = self.username_input.text().strip()
        if not username:
            return

        # 如果当前用户是记住的用户，立即更新配置文件
        if self.parent_app.remembered_user and self.parent_app.remembered_user["username"] == username:
            auto_login = self.auto_login_checkbox.isChecked()
            update_remembered_auto_login(username, auto_login)
            logging.debug(f"已更新 {username} 的自动登录设置: {auto_login}")
        else:
            # 对于新用户，设置会在登录时保存
            logging.debug(f"用户 {username} 的自动登录设置将在登录时保存")

    def update_checkbox_states(self):
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
            self.login()

    def login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "输入错误", "用户名和密码不能为空")
            return

        # 调用API测试登录
        logging.debug(f"尝试登录: {username}")
        ret = test_login(username, password)
        logging.debug(f"登录返回: {ret}")

        # 根据API返回结果处理
        if ret:
            # 保存记住密码和自动登录设置
            save_remembered_user(username, password, self.remember_checkbox.isChecked(), self.auto_login_checkbox.isChecked())
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
        self.parent_app.change_password_page.username_input.setText(self.username_input.text().strip())


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
        back_btn.setStyleSheet("color: blue; text-decoration: underline; border: none; background: transparent;")
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
        self.setStyleSheet("""
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
        """)

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
        ret = test_register(username, password)

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
        self.parent().change_password_page.username_input.setText(self.username_input.text().strip())


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
        back_btn.setStyleSheet("color: blue; text-decoration: underline; border: none; background: transparent;")
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
        self.setStyleSheet("""
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
        """)

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
        cookies = test_login(username, old_password)
        # 调用API修改密码
        logging.debug(f"尝试修改密码: {username}")
        ret = test_change_password(cookies, old_password, new_password)

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


class AuthApp(QWidget):
    def __init__(self):
        super().__init__()
        self.should_auto_login = False  # 自动登录标志
        self.remembered_user = None  # 记住的用户信息
        chars = string.ascii_letters + string.digits  # 大小写字母+数字
        random_string = ''.join(random.choices(chars, k=10))
        self.setWindowTitle(random_string)
        self.setGeometry(500, 300, 400, 300)

        # 创建堆叠窗口
        self.stacked_widget = QStackedWidget()

        # 创建页面
        self.login_page = LoginPage(self.stacked_widget, self)
        self.register_page = RegisterPage(self.stacked_widget)
        self.change_password_page = ChangePasswordPage(self.stacked_widget)  # 添加修改密码页面

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    load_application_font()
    window = AuthApp()
    window.show()
    sys.exit(app.exec_())
