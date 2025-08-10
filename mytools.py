import ctypes
import json
import os
import random
import threading
import time
import logging
import pyperclip
import pywintypes
import win32con
import win32gui
from PyQt5.QtCore import pyqtSignal, QObject, Qt
from PyQt5.QtWidgets import (QMainWindow, QMessageBox, QApplication, QDialog,
                             QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
                             QListWidget, QLabel, QInputDialog, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView)
from pynput import keyboard

from utils.pyauto_b import pyauto
from view.my_tools import Ui_Form

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MyTools")

# 默认职业数据
DEFAULT_CLASS_DATA = {
    '男气功': 'eJwVyr0OwVAAR/Hzb4P23n5cEoOSSOQOVGJnt9be2SghkiZeyWwzeCWkL6DO9ktOGwwUHqm2IBZs0IPohXooRhHmhIbIooS1xyyZPFGFCq1KdEYHzA7t8Rc0VT/HO+Y1syujhvEN9yH9Er+xmcJUQS5lJZaiu+m6k+DIqf+ggfYH8PgRJg==',
    '男散打': 'eJwdx6EOglAAhtHvR5DrdXNT7uZMOIc4i12aG9kA0Wr0CRgvZCLQDL6QkHgAnJ52Bi/0JneuZxBbWkyA3uiEDHaGpmiJHihEDdph97gX1uF8jj0aSTPSG8EB26GSJCLJiQviC24j1awrVh/mkbQYMVT4/DzJKcmo/ytg+AIdlRNw',
    '帕拉丁': 'eJwlxksKglAAhtHvVxC5poMIaiZCBCE0dxOtolmJ5uPeSLfhIhw3a9Cm3EBBZ3QWb+X7F84FiB0vQqEP8lCASk5XzA1Tk79Rhe4cG0zLoSfu2FsyR/pgM7B9opH1RJRLScPfQM9MSf27pcMxwvIFQCMTjg==',
    '召唤': 'eJxFyjkOAWEAQOH3ZhIRW2TyNxpLgkRiizC2AygIUWhVLuI21DqF0oXmAlS87kteFsVRdGG/BGnzIF/CFxaxhh0MNGNMcEyo41DXOjX3pHDFmU6wT+9IYUB3R/fwfWi/cUTrhnMbW8JSU12YbCieqJ4pr7SSyq874Q9iyD4Anw+H',
    '逐风者': 'eJwVwbENgkAAhtHvJ5pcMDGGXIE0NGhCYajZAAEPiLABy8gm1HQWLnULGN7zgTkEM64EcWXDCP1QgiyquHnsExn0JWywL1STt+SO+0PHgmwg64h70jd2RBPRwuXD6VwxsbAbWXHUtBQM9HTg/wMeEZM=',
    '镇魂者': 'eJwNyUEKgkAYhuH3G1PHX8aRCNoIEYhgqWC7LtEpuoDHatWinYsu5QXq2T6bi849edxBNHzwQl90Q290RQvqsQQ5lHJcsQu2QxnNiHK6CfO0Be3AueQ0cwioYh+pjbImVJDhGYDIi5SFkUBOwb+2H011C2s=',
    '巅峰狂徒': 'eJwVx7ENgkAAhtHvxwJyRCUERE7gIBxnYWPoWIIp3NDOwqVYAH3d26LzIXqxLiAsbxKhL5pRjh7oiUr0wVwoKmSJr5iGUBNumBZ1eMfQ4waKkcqTB7KJ9M7xZAHHn2ekoaalJ/zewbYD5okKiQ==',
    '黑暗武士': 'eJwNjL8LAXEAR9/ny+kOSbnhFo5CiS4xnQynDFKIv0EZKBa//yKT3eCfssngO756732Mh1kzj0E0iJCDXLRDb+TTn5FP0AgN0BP10IHqlm6eSkC0p3yk/SK7oDWhFaKMsobmGHVQjDbUPbSiNqQ2JVwSSv6X0o8iyhVOnLlw5cYd2ONzZMGPh6XMiVSES886jsMOQ8zU6qkBIZ6tzIGOTdNDZmwZ20d6xZeEgM8fCTgelQ==',
    '狂战士': 'eJwNyj0LglAYhuH7UQJ7h+jj5DlCEUZDk7Q2uocitKSOgb+tua2h/9Ps1FbXfI0RcXynOoPY8iQp0AS9UYYWqOTkKFaYoQRdcC9sj45YIHQ61OQeS5UP7Bo2LUuv9Rf1mn+YXhXdpJkjUONpyHhQ0mnA/wukYvwBELkQgw==',
    '阿修罗': 'eJwVzbEKglAAhtHvvyXYBaPiakiDCm2BheXgErg2ODQ3BN6Xa25r6HEcWn2B6rzAGQ3TiadrQGSU6En4RgFKsUJL1HJwlCHa4wyq2N0VvLBHlLOpsTE6YROKM9sGXdCNlWfdsxiYfYg6mas0z4lJSH8LPKhwtPT8eRi/NGMQCA==',
    '驭剑士': 'eJwlxzEKwjAARuH3J0SaiG0NFCSoIHRx6aIdeglPUeqJHDyCs5uDlyoUx4o++IY3mqVsz6UDsf1qn2QZeiPLaYEaVKI1oWNnsBV6ERzHnJBId9yB2lMXbCL7M3Gi+lBe8QOrFnNDufBM/HvgsCSK30UYZ7FZDmo=',
    '暗殿骑士': 'eJwNzDsKg0AYAOH5NcWikEoSSCeIKAuChUUaNbti4+MUdp7MOl0KSy+0F8gWU3zNuCAOwo31DcLD13xRCjmRCumoLqRFevSPqKC0lB+igdzw0mQzMpJOJAvPnbjmdu8psGhm4PDDjgHD6LWA+wNc8w72',
    '流浪武士': 'eJwdjL0KQFAYQM/HHUSZvICSUrIZvIFJhnsvxegNKM9kMtgMXsoL+Dl1hrOc2wmUO9FUIESv5YF3IR5SIDuyULSIxs+RE9+QWbKOtCcdSEbimmgmWFFhhwE0HxvDO+uxf41wPztbDzs=',
    '刃影': 'eJwNy7sJhEAABuF/BEFWMND10PV9yIKJmNqEVdjcxWYX2JQNuJN9wTxRGkenjl1CVpeSRNwihwIsW8n6l/lgHEvFUmMafIsfmHvmDjMyfbGeNLNhcQwo9FNJQ0tFHzyi5wVhwAph',
    '猎人': 'eJwVzD8OwWAcAND300W+QSwO0KWJSLo7A6Fa/SMVg7ic2WZwqV4A7wBvmi2z2cNhS1jJpJf5R+zEXpyUlfIo1aKxeUut9VkaFJ3UKy7iKh/lN3EXi0H9O04anadeq3L1NzJ9AXY3EGc=',
    '妖护使': 'eJwVwT0KgmAAANCnBcYXRIPQHIQgLa5dolM0hiD5SxLSbZrbGrqUF4jem+PtMr44n4ik3lZX0Ve0EJWKRFE53oSP0MhroZV3sl42ONyF0f4hneye1ptOqTEY1V56rUTlb2L+Ad03E2c=',
    '女光明骑士': 'eJwNzTEOgjAAhtHvL0G0MRWJoilUihISZycv4Y6zmydzcnBz8FJcQIY3v9E4mQe3K4h2YjMuH+Y/ZFBCTEnfaIbWhBwt0Re7wm7QFrvDl5wHeof19DWqaPeUBxRoImqojxRPdEId+Z2FG6Yl4GiIvPCUZCR0QAXjH+KnDN4=',
    '狩猎者': 'eJw1x70KQFAYgOH3OxZ9xWJwB6ekZDVT/o5TyiWYuDKzzeCm3IBSnu15TBSYFV+BkHASBsiNGKSmHCl6pEUd+YZe6EA2kXWox87YBllIdyQemPgdeGYc47cFnhfdFw3L',
    '征战者': 'eJwlwb0JwlAYAMD7nhEkoJViLQQhMT/GEDSlCziFy1nbWbhUFrDwbk7rSE+PibDztkriKxbSUrTOnTbTTvLe6SO/yUvlxbZyrBWNYnC4itH+LjaVHrXG4KWTKf2NzD+0awvm',
    '缪斯': 'eJwNy70NglAAhtHnxcZ8BWEAEzQS4uXnioiABaGiZQqWw9bOwqVYQE9/tiBSsDA/QRx4s9+hL0pQyvGFJrxDZ3TFLsQleYFl6IPlyONupBV2x2qShtMDtcQd1qMBjVg4UVLTUgArjgzPf1HRwPYD6WIO1w==',
    '元素爆破师': 'eJwdxzEKgzAAhtHvj4nYCAVNQShODgFxcHDqIJS6e4pezrlbBy+VC4i+7SVTyHxZXyAafhRCO3qiCt3wNeqQI2QMf/wHBXxO3/J44wzREkf5Ek1oplnQPaMGAqeNHIOlvDZDOgBrgwmO',
    '次元行者': 'eJw1xz8KggAYh+H3JwT2BUIgDjq1CBJIa5dodBD8gyYo3qLdgzi7OXgpLxAIPtuzO+7F+fJ5gwhYcEO0IaE7inhdsRzLSCueHVqxEqtJfqjBWuKeuEADjxF/4uZVdJxmalp6omMD7H9oQg+9',
}

# 默认配置
DEFAULT_CONFIG = {
    'selected_class': '男气功',
    'auto_copy': True,
    'enable_hotkeys': False,
    'class_data': DEFAULT_CLASS_DATA  # 存储所有职业数据
}

# 用户配置存储文件
CONFIG_FILE = "my_tools_config.json"


class KeyPressSignal(QObject):
    key_pressed = pyqtSignal(str)


class KeyboardListenerThread(threading.Thread):
    """键盘监听线程"""

    def __init__(self, signal):
        self.running = True
        threading.Thread.__init__(self)
        self.signal = signal

    def run(self):
        def on_press(key):
            try:
                if key == keyboard.Key.home:
                    self.signal.key_pressed.emit("start")
                elif key == keyboard.Key.end:
                    self.signal.key_pressed.emit("stop")
            except AttributeError:
                # 处理特殊键的情况（这里可以忽略）
                pass

        # 创建键盘监听器，并设置停止条件
        with keyboard.Listener(on_press=on_press) as listener:
            while self.running:
                time.sleep(1)
        print("KeyboardListenerThread 已停止")

    def stop(self):
        """安全停止线程"""
        self.running = False


class ClassEditorDialog(QDialog):
    """职业数据编辑器对话框"""

    def __init__(self, class_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑职业数据")
        self.setMinimumSize(600, 400)
        self.class_data = class_data.copy()  # 使用副本，防止直接修改原始数据

        # 创建UI
        self.layout = QVBoxLayout()

        # 表格控件
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["职业名称", "配置数据"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 初始不可编辑

        # 填充表格数据
        self.populate_table()

        # 按钮区域
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("添加职业")
        self.add_btn.clicked.connect(self.add_class)

        self.edit_btn = QPushButton("编辑选中项")
        self.edit_btn.clicked.connect(self.edit_selected)

        self.delete_btn = QPushButton("删除选中项")
        self.delete_btn.clicked.connect(self.delete_selected)

        self.reset_btn = QPushButton("重置为默认")
        self.reset_btn.clicked.connect(self.reset_to_default)

        self.save_btn = QPushButton("保存并关闭")
        self.save_btn.clicked.connect(self.accept)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)

        # 添加到主布局
        self.layout.addWidget(self.table)
        self.layout.addLayout(button_layout)
        self.setLayout(self.layout)

    def populate_table(self):
        """填充表格数据"""
        self.table.setRowCount(len(self.class_data))
        sorted_classes = sorted(self.class_data.keys())

        for row, class_name in enumerate(sorted_classes):
            # 职业名称
            name_item = QTableWidgetItem(class_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)  # 不可编辑

            # 配置数据
            config_item = QTableWidgetItem(self.class_data[class_name])
            config_item.setFlags(config_item.flags() & ~Qt.ItemIsEditable)  # 不可编辑

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, config_item)

    def add_class(self):
        """添加新职业"""
        class_name, ok = QInputDialog.getText(
            self, "添加职业", "请输入职业名称:"
        )

        if not ok or not class_name:
            return

        # 检查是否已存在
        if class_name in self.class_data:
            QMessageBox.warning(self, "添加失败", f"职业 '{class_name}' 已存在!")
            return

        config_data, ok = QInputDialog.getText(
            self, "配置数据", f"请输入 '{class_name}' 的配置数据:"
        )

        if ok and config_data:
            self.class_data[class_name] = config_data
            self.populate_table()
            QMessageBox.information(self, "添加成功", f"已添加职业 '{class_name}'")

    def edit_selected(self):
        """编辑选中的职业"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "编辑失败", "请先选择一个职业!")
            return

        row = selected_items[0].row()
        old_class_name = self.table.item(row, 0).text()

        # 编辑名称
        new_class_name, ok = QInputDialog.getText(
            self, "编辑职业", "修改职业名称:", text=old_class_name
        )

        if not ok or not new_class_name:
            return

        # 检查名称是否已存在
        if new_class_name != old_class_name and new_class_name in self.class_data:
            QMessageBox.warning(self, "编辑失败", f"职业 '{new_class_name}' 已存在!")
            return

        # 编辑配置数据
        current_config = self.class_data[old_class_name]
        new_config, ok = QInputDialog.getText(
            self, "编辑配置", f"修改 '{new_class_name}' 的配置数据:",
            text=current_config
        )

        if ok:
            # 如果名称有变化，先删除旧的
            if new_class_name != old_class_name:
                del self.class_data[old_class_name]

            self.class_data[new_class_name] = new_config
            self.populate_table()
            QMessageBox.information(self, "编辑成功", f"已更新职业 '{new_class_name}'")

    def delete_selected(self):
        """删除选中的职业"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "删除失败", "请先选择一个职业!")
            return

        row = selected_items[0].row()
        class_name = self.table.item(row, 0).text()

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除职业 '{class_name}' 吗?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            del self.class_data[class_name]
            self.populate_table()
            QMessageBox.information(self, "删除成功", f"已删除职业 '{class_name}'")

    def reset_to_default(self):
        """重置为默认职业数据"""
        reply = QMessageBox.question(
            self, "确认重置",
            "确定要重置所有职业数据为默认值吗? 当前数据将丢失!",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.class_data = DEFAULT_CLASS_DATA.copy()
            self.populate_table()
            QMessageBox.information(self, "重置成功", "已恢复为默认职业数据")

    def get_class_data(self):
        """获取编辑后的职业数据"""
        return self.class_data


class MyTools(Ui_Form, QMainWindow):
    """主应用类"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.key_press_signal = None
        self.setupUi(self)
        self.setWindowTitle("职业工具 - 用户可编辑版")

        self.keyboard_thread = None

        # 加载配置
        self.config = self.load_config()

        # 初始化UI
        self.init_ui()

        # 绑定事件
        self.bind_events()

        self.start_keyboard_listener()

    def init_ui(self):
        """初始化界面组件"""
        # 初始化职业下拉框
        self.comboBox.clear()
        self.comboBox.addItems(sorted(self.config['class_data'].keys()))

        # 设置选中项
        selected_class = self.config['selected_class']
        index = self.comboBox.findText(selected_class, Qt.MatchExactly)
        if index != -1:
            self.comboBox.setCurrentIndex(index)
        else:
            self.comboBox.setCurrentIndex(0)
            self.config['selected_class'] = self.comboBox.currentText()

        # 设置复选框状态
        self.checkBox.setChecked(self.config['auto_copy'])
        self.checkBox_2.setChecked(self.config['enable_hotkeys'])

        # 添加编辑按钮
        self.edit_btn = QPushButton("编辑职业数据", self)
        self.edit_btn.setGeometry(20, 150, 120, 30)  # 设置位置和大小
        self.edit_btn.clicked.connect(self.open_class_editor)

        # 添加状态栏提示
        self.statusBar().showMessage("就绪 | Home键: 启动监听, End键: 停止监听")

    def load_config(self):
        """加载用户配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)

                # 验证配置完整性
                for key in DEFAULT_CONFIG:
                    if key not in config:
                        config[key] = DEFAULT_CONFIG[key]

                # 确保职业数据存在
                if 'class_data' not in config or not config['class_data']:
                    config['class_data'] = DEFAULT_CLASS_DATA.copy()

                return config
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")

        # 使用默认配置
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        """保存用户配置"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            QMessageBox.warning(self, "配置保存失败", f"保存配置时出错: {str(e)}")

    def bind_events(self):
        """绑定UI事件"""
        # 复选框状态变化
        self.checkBox.stateChanged.connect(self.on_auto_copy_changed)
        self.checkBox_2.stateChanged.connect(self.on_hotkeys_enabled_changed)

        # 职业选择变化
        self.comboBox.currentIndexChanged.connect(self.on_class_selected)

        self.key_press_signal = KeyPressSignal()  # 键盘检测线程
        self.key_press_signal.key_pressed.connect(self.handle_key_press)

        try:
            # 创建并启动键盘监听线程
            self.keyboard_thread = KeyboardListenerThread(self.key_press_signal)
            self.keyboard_thread.start()
            self.statusBar().showMessage("键盘监听已启动 - 使用Home/End键控制")
            logger.info("键盘监听线程已启动")
        except Exception as e:
            error_msg = f"启动键盘监听失败: {str(e)}"
            self.statusBar().showMessage(error_msg)
            logger.error(error_msg)

    def on_auto_copy_changed(self, state):
        """自动复制配置变化处理"""
        self.config['auto_copy'] = (state == Qt.Checked)
        self.save_config()

    def on_hotkeys_enabled_changed(self, state):
        """热键启用状态变化处理"""
        self.config['enable_hotkeys'] = (state == Qt.Checked)
        self.save_config()

    def on_class_selected(self):
        """职业选择变化处理"""
        selected_class = self.comboBox.currentText()
        self.config['selected_class'] = selected_class
        self.save_config()

        # 更新状态栏
        self.statusBar().showMessage(f"已选择职业: {selected_class}")

        # 复制新选择的职业配置
        self.copy_current_class_data()

    def copy_current_class_data(self):
        """复制当前职业配置到剪贴板"""
        selected_class = self.comboBox.currentText()
        class_data = self.config['class_data']

        if selected_class in class_data:
            data = class_data[selected_class]
            try:
                pyperclip.copy(data)
                msg = f"已复制【{selected_class}】配置到剪贴板"
                self.statusBar().showMessage(msg)
                logger.info(msg)
            except Exception as e:
                error_msg = f"复制失败: {str(e)}"
                self.statusBar().showMessage(error_msg)
                logger.error(error_msg)
        else:
            error_msg = f"未找到【{selected_class}】的配置数据"
            self.statusBar().showMessage(error_msg)
            logger.warning(error_msg)

    def start_keyboard_listener(self):
        """启动键盘监听线程"""
        if self.keyboard_thread and self.keyboard_thread.is_alive():
            return

    def stop_keyboard_listener(self):
        """停止键盘监听线程"""
        if self.keyboard_thread and self.keyboard_thread.is_alive():
            try:
                self.keyboard_thread.stop()
                self.keyboard_thread.join(timeout=1.0)
                self.statusBar().showMessage("键盘监听已停止")
                logger.info("键盘监听线程已停止")
            except Exception as e:
                error_msg = f"停止键盘监听失败: {str(e)}"
                self.statusBar().showMessage(error_msg)
                logger.error(error_msg)

    def handle_key_press(self, key):
        """处理键盘按键信号"""
        if key == "start":
            # 在新线程中执行操作，避免阻塞主线程
            threading.Thread(target=self.execute_dnf_actions, daemon=True).start()
        elif key == "stop":
            logger.info("停止键按下")

    def execute_dnf_actions(self):
        """执行DNF相关操作"""
        try:
            self.copy_current_class_data()

            # 激活DNF窗口
            activate_window_by_handle()
            time.sleep(0.2)

            # 根据复选框状态执行操作
            if self.checkBox.isChecked():
                dnf_key()

            if self.checkBox_2.isChecked():
                dnf_称号()
        except Exception as e:
            logger.error(f"执行DNF操作时出错: {str(e)}")

    def open_class_editor(self):
        """打开职业数据编辑器"""
        dialog = ClassEditorDialog(self.config['class_data'], self)
        if dialog.exec_() == QDialog.Accepted:
            # 更新职业数据
            self.config['class_data'] = dialog.get_class_data()
            self.save_config()

            # 更新下拉框
            current_selection = self.comboBox.currentText()
            self.comboBox.clear()
            self.comboBox.addItems(sorted(self.config['class_data'].keys()))

            # 尝试恢复之前的选中项
            index = self.comboBox.findText(current_selection, Qt.MatchExactly)
            if index != -1:
                self.comboBox.setCurrentIndex(index)
            else:
                self.comboBox.setCurrentIndex(0)

            QMessageBox.information(self, "更新成功", "职业数据已更新并保存!")
            logger.info("职业数据已更新")

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        self.stop_keyboard_listener()
        self.save_config()
        event.accept()


# ================== DNF相关函数 ==================
def get_hwnd():
    """获取DNF窗口句柄"""
    dnf_hwnd = win32gui.FindWindow('地下城与勇士', '地下城与勇士：创新世纪')
    if dnf_hwnd != 0:
        logger.info(f"地下城与勇士窗口的句柄: {dnf_hwnd}")
    return dnf_hwnd


hwnd = get_hwnd()  # 获取窗口句柄


def activate_window_by_handle():
    """激活DNF窗口"""
    if not isinstance(hwnd, int):
        logger.error("窗口句柄必须是整数类型")
        return False

    if not win32gui.IsWindow(hwnd):
        logger.error("窗口句柄无效或窗口已关闭")
        return False

    try:
        win32gui.SetForegroundWindow(hwnd)
        win32gui.SendMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)
        time.sleep(random.uniform(0.01, 0.02))
        return True
    except pywintypes.error as e:
        if e.winerror == 5:  # ERROR_ACCESS_DENIED
            current_process_id = ctypes.windll.kernel32.GetCurrentProcessId()
            ctypes.windll.user32.AllowSetForegroundWindow(current_process_id)
            try:
                win32gui.SetForegroundWindow(hwnd)
                win32gui.SendMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)
                time.sleep(random.uniform(0.01, 0.02))
                return True
            except pywintypes.error as e:
                logger.error(f"激活窗口时出错: {e}")
        else:
            logger.error(f"激活窗口时发生未知错误: {e}")
        return False


def move_too(x, y):
    """移动到相对窗口的位置"""
    left, top = win32gui.GetWindowRect(hwnd)[:2]
    pyauto.moveTo(left + x, top + y)


def move_and_click(x, y, button="left", delay=0.3):
    """移动到指定位置并点击"""
    move_too(x, y)
    time.sleep(delay)
    pyauto.click(button)
    time.sleep(delay)


def dnf_key():
    """执行DNF技能导入操作"""
    try:
        pyauto.KeyPressChar('k')
        time.sleep(0.3)
        move_and_click(277, 150)  # 点菜单
        move_and_click(295, 214)  # 点导入
        move_and_click(675, 326)  # 点同时应用技能树
        time.sleep(0.3)
        move_and_click(641, 424)  # 点确定
        time.sleep(0.3)
        pyauto.KeyPressChar('space')
        time.sleep(0.3)
        move_and_click(641, 424, delay=0.2)  # 点确定
        move_and_click(491, 593)  # 点学习
        pyauto.KeyPressChar('space')
        time.sleep(0.3)
        move_and_click(491, 593)  # 点学习
        pyauto.KeyPressChar('esc')
        time.sleep(0.3)
        logger.info("技能导入操作完成")
    except Exception as e:
        logger.error(f"执行技能导入时出错: {str(e)}")


def dnf_称号():
    """执行DNF称号替换操作"""
    try:
        pyauto.KeyPressChar('f9')
        time.sleep(0.3)
        move_and_click(711, 598)  # 点替换
        move_and_click(427, 227)  # 点特殊成就
        move_and_click(471, 336)  # 点装备穿戴
        move_and_click(610, 307)  # 点基础达标
        logger.info("称号替换操作完成")
    except Exception as e:
        logger.error(f"执行称号替换时出错: {str(e)}")


if __name__ == "__main__":
    app = QApplication([])
    window = MyTools()
    window.show()
    app.exec_()
