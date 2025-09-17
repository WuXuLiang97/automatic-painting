# -*- coding: utf-8 -*-
import datetime
import json
import os.path
import random
# import pprint
import string
import threading
import time
import traceback

import cv2
import numpy as np
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import pyqtSignal, QByteArray, QPoint, QSize, QThread, QUrl
from PyQt5.QtGui import QPixmap, QImage, QDesktopServices
from PyQt5.QtWidgets import QMainWindow, QAbstractItemView, QTableWidgetItem, QHeaderView, QMessageBox

from core.KeyboardListenerThread import KeyPressSignal, KeyboardListenerThread
# from core.check_caton import CheckPlayerDynamics
from core.check_d import CheckProcess
from core.global_variable import display_queue
from core.player import PlayerThread
# from core.yolo_process import YoloProcess

from utils.common_util import get_date
# from utils.config_util import get_settings_group, get_all_role_settings, get_gui_config, set_ip, ini_file_path
from core.callRoleSettings import RoleSettingsWindow
from core.callSettingsGroup import SettingsGroupWindow
from utils.screenshot_util import screenshot_util
# from utils.yjs import yjs
from utils.cross_control import pyauto
# from view.main0914 import Ui_MainWindow
from view.main0916 import Ui_MainWindow
from view.key_config_run import KeyConfigDialog

# from view.key_config_run import KeyConfigDialog
from core.device_identity_client import send_request
from core.device_time_utils import get_identity_mark
# from core.window_position import WindowPositionUpdater
from core import global_variable as gv
from utils.api import test_view_subgroups, test_view_subgroup_config
from core.vnc import VNC, api
from core.capturecardconnection import CaptureCardConnection
from utils.cv_recognizer import vnc_mm
from root_dir import root_path

# 拼接文件路径
CONFIG_PATH = os.path.join(root_path, "json_resources/config.json")
f_program_version = '250908'
Network = 0


def get_gui_config():
    """获取GUI配置"""
    # 默认配置
    default_config = {
        "ip": "192.168.1.1",
        "yjs": 0,
        "banzhuan": 0,
        "vmware_ip": "127.0.0.1",
        "vmware_prot": "5900",
        "vmware_password": "",
        "tab_index": 0,
        'vid': '',
        'pid': '',
        'identifier': "0",
    }

    try:
        # 如果配置文件存在，读取它
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
                file_config = json.load(file)
                # 合并默认配置和文件配置
                return {**default_config, **file_config}

        # 如果配置文件不存在，创建默认配置
        with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
            json.dump(default_config, file, indent=4, ensure_ascii=False)
        return default_config

    except json.JSONDecodeError:
        print("Warning: Config file is corrupted or not in JSON format.")
        return default_config
    except Exception as e:
        print(f"Error loading config: {e}")
        return default_config


class DisplayThread(QThread):
    """专用展示线程"""
    update_signal = pyqtSignal(np.ndarray)  # 图像更新信号

    def __init__(self):
        super().__init__()
        self.running = True
        self.lock = threading.Lock()  # 添加线程锁

    def run(self):
        while self.running:
            with self.lock:  # 使用锁保护共享资源
                if not display_queue.empty():
                    frame = display_queue.get()
                    self.update_signal.emit(frame)
            time.sleep(0.033)

    def stop(self):
        with self.lock:
            self.running = False


class AppMain(QMainWindow, Ui_MainWindow):
    """
    主应用程序窗口类，继承自QMainWindow和Ui_MainWindow（后者通常是通过pyuic从UI设计文件生成的类）。

    该类负责初始化主窗口，启动工作线程，处理信号连接，并管理其他子窗口。
    """

    stop_message = pyqtSignal()  # 定义一个自定义信号stop_message，用于在需要时停止某些操作或线程。

    def __init__(self, parent=None, dic=None):
        """
        初始化MyWindow类实例。

        Args:
            parent (QWidget, optional): 父窗口对象。默认为None。
        """
        super().__init__(parent)  # 调用父类QMainWindow的构造函数
        self.displaythread = None
        self.checkProcess = None
        self.playerThread = None
        self.VNC = None
        self.identifier = None
        self.heartbeat_socket = None
        self.heartbeat_thread = None
        self.server_ip = None
        self.server_address = None
        self.dic = dic
        self.authapp = None
        self.role_settings = {}
        # self.sock = None
        self.setupUi(self)  # 假设这个方法是在某个UI文件中通过pyuic生成的，用于设置窗口的UI界面
        self.action12.triggered.connect(self.show_login)
        self.loadSettings("json_resources/ui_config.json")

        self.lineEdit.textChanged.connect(self.on_text_changed)
        self.lineEdit_3.textChanged.connect(self.on_text_changed)
        self.lineEdit_4.textChanged.connect(self.on_text_changed)
        self.lineEdit_5.textChanged.connect(self.on_text_changed)
        self.lineEdit_10.textChanged.connect(self.on_text_changed)
        self.lineEdit_9.textChanged.connect(self.on_text_changed)
        # self.lineEdit_8.textChanged.connect(self.on_text_changed)
        self.comboBox.addItems(self.list_capture_devices())

        self.tabWidget.currentChanged.connect(self.on_tab_changed)
        self.comboBox.currentTextChanged.connect(self.on_combobox_changed)
        self.startBtn_2.clicked.connect(self.connect_to_vnc)
        self.startBtn_4.clicked.connect(self.connect_to_vnc)
        self.helpBtn.clicked.connect(self.open_local_webpage)
        # self.ComboBox_2.currentIndexChanged.connect(self.on_combobox_changed)
        self.ComboBox_3.currentIndexChanged.connect(self.on_combobox_changed)
        self.init_content()  # 初始化窗口内容，可能是设置一些初始值或UI组件的状态

        self.key_press_signal = KeyPressSignal()  # 键盘检测线程
        # self.check_player_dynamics = CheckPlayerDynamics()  # 人物卡住检测
        # self.WindowPositionUpdater = WindowPositionUpdater()  # 初始化窗口坐标检查进程
        self.yoloProcess = None  # YOLO处理进程初始化为None，后续可能按需加载

        # 标记是否为首次加载模型
        self.is_first_load_model = True
        # 初始化模型加载状态
        self.load_model_status = "NoReady"

        self.key_press_signal.key_pressed.connect(self.on_key_pressed)
        # self.playerThread.sock_connect_message.connect(self.sock_connect)  # 连接角色表更新信号

        # 设置窗体禁止最大化
        self.setFixedSize(self.width(), self.height())  # 设置窗口为固定大小，防止用户最大化

        # 初始化设置窗口
        print(self.dic,7777777777)
        self.settings_group_window = SettingsGroupWindow(dic=self.dic)  # 初始化设置组窗口
        self.role_settings_window = RoleSettingsWindow(dic=self.dic)  # 初始化角色设置窗口

        # 连接设置组窗口的信号

        self.settings_group_window.send_update_settings_group_signal.connect(
            self.role_settings_window.receive_update_settings_group_signal)  # 连接设置组更新信号到角色设置窗口
        self.settings_group_window.send_update_settings_group_signal.connect(
            self.receive_update_settings_group_signal)  # 连接设置组更新信号到当前窗口的接收方法


        # 连接下拉框激活信号到更新角色表数据的方法
        self.settingsGroupComboBox.activated.connect(self.update_roles_table_data)  # 假设settingsGroupComboBox是UI中的某个下拉框
        # self.Keyboardsettings.triggered.connect(self.open_keyboard_settings)
        # 创建并启动键盘监听线程
        self.Keyboardsettings.triggered.connect(self.open_keyboard_settings)
        self.keyboard_thread = KeyboardListenerThread(self.key_press_signal)
        self.keyboard_thread.start()  # self.yoloProcess = YoloProcess()  # self.yoloProcess.load_model()  # self.playerThread.yolo = self.yoloProcess

    def open_keyboard_settings(self):
        """打开按键配置对话框"""
        dialog = KeyConfigDialog(self)
        dialog.exec_()
    def init_content(self):
        """
        初始化窗口内容，特别是与角色表格相关的设置。

        该方法设置了角色表格（self.rolesTable）的列宽自适应、列数、列标题，并禁用了编辑功能。
        此外，还调用了两个方法用于更新设置组数据和角色表格数据。
        """

        # 设置角色表格的列数为7
        self.rolesTable.setColumnCount(8)

        # 设置角色表格的水平头部标签
        header_labels = ['位置', '职业类型', '转职职业', '身高', '地图名称', '难度', '刷完？', '预留疲劳']
        self.rolesTable.setHorizontalHeaderLabels(header_labels)

        # 获取水平头部
        header = self.rolesTable.horizontalHeader()

        # 设置列宽策略：混合模式
        header.setSectionResizeMode(QHeaderView.Interactive)  # 改为交互模式

        # 设置特定列的自适应策略
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 位置 - 按内容调整
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 身高 - 按内容调整
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 难度 - 按内容调整
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 刷完？ - 按内容调整

        # 设置长文本列的初始宽度和最大宽度
        self.rolesTable.setColumnWidth(1, 80)  # 角色职业类型
        self.rolesTable.setColumnWidth(2, 80)  # 角色转职职业
        self.rolesTable.setColumnWidth(4, 120)  # 地图名称
        self.rolesTable.setColumnWidth(6, 50)  # 地图名称

        # 允许用户手动调整列宽
        header.setSectionsMovable(True)
        header.setSectionsClickable(True)

        # 禁用角色表格的编辑功能
        self.rolesTable.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # 调用方法更新设置组数据，这可能涉及从某个数据源（如文件、数据库或网络）加载设置组信息
        self.update_settings_group_data()

        # 调用方法更新角色表格数据，展示当前的角色信息
        self.update_roles_table_data()

        gui_config = get_gui_config()

        # 获取保存的索引（默认值为0，即第一个标签页）
        saved_index = gui_config.get("tab_index", 0)

        # 检查索引是否有效（必须在标签页数量范围内）
        tab_count = self.tabWidget.count()
        if 0 <= saved_index < tab_count:
            # 通过索引切换标签页
            self.tabWidget.setCurrentIndex(saved_index)
            gv.tab_index = gui_config['tab_index']
            print(f"已恢复到标签页索引：{saved_index}")

        # 初始化ui的主机地址
        self.lineEdit.setText(str(gui_config['ip']))
        gv.server_ip = gui_config['ip']

        # 初始化ui的虚拟机ip地址
        self.lineEdit_3.setText(str(gui_config['vmware_ip']))
        gv.vmware_ip = gui_config['vmware_ip']

        # 初始化ui的虚拟机端口
        self.lineEdit_4.setText(str(gui_config['vmware_prot']))
        gv.vmware_prot = gui_config['vmware_prot']

        # 初始化ui的虚拟机vnc密码
        self.lineEdit_5.setText(str(gui_config['vmware_password']))
        gv.vmware_password = gui_config['vmware_password']

        # 初始化ui的主控vid
        self.lineEdit_10.setText(str(gui_config['vid']))
        gv.vid = gui_config['vid']

        # 初始化ui的主控pid
        self.lineEdit_9.setText(str(gui_config['pid']))
        gv.pid = gui_config['pid']

        # # 初始化ui的主控采集卡编号
        # self.lineEdit_8.setText(str(gui_config['identifier']))
        # gv.identifier = gui_config['identifier']

        # 初始化ui的主机地址
        # self.ComboBox_2.setCurrentIndex(int(gui_config['yjs']))
        # 初始化ui的功能（搬砖还是半自动剧情）
        self.ComboBox_3.setCurrentIndex(int(gui_config['banzhuan']))
        gv.banzhuan = gui_config['banzhuan']
        # 初始化ui的机器码
        self.lineEdit_2.setText(get_identity_mark())
        chars = string.ascii_letters + string.digits  # 大小写字母+数字
        random_string = ''.join(random.choices(chars, k=10))
        self.setWindowTitle(random_string)

        # 启动显示线程
        self.displaythread = DisplayThread()
        self.displaythread.update_signal.connect(self.update_image)
        self.displaythread.start()
        global Network
        Network = 1

        # for i in range(3):
        #     try:
        #         ret = send_request(f_program_version=f_program_version, state=0)
        #         return_data_1 = ret_data(ret)
        #         if return_data_1.response == 200 or return_data_1.response == 201:
        #             if return_data_1.response == 201:
        #                 self.update_log(
        #                     return_data_1.msg)  # my_print('亲爱的用户们：\n\t我们软件已推出新版本，增加了新功能并优化了现有功能。为方便您更新，我们已在Q群提供更新文件。请您自行进入Q群下载并安装新版本。如遇问题，请随时在Q群反馈。感谢您的支持！\n祝您使用愉快')
        #
        #             else:
        #                 self.update_log(f'已连接到网络')
        #             self.setWindowTitle(f'工具人({str(f_program_version)})    {return_data_1.msg}')
        #             global Network
        #             Network = 1
        #             break
        #         else:
        #             # my_print(f'尝试连接网络{i + 1}次')
        #             self.update_log(return_data_1.msg)
        #             break
        #     except Exception as e:
        #         self.update_log(f"机器码验证错误:{e}")

    def show_login(self):
        self.authapp.show()


    # def show_keyboard_settings(self):
    #     self.keyboardapp.show()

    def on_key_pressed(self, key):
        if key == "start":
            self.start_clicked()
        elif key == "stop":
            self.stop_clicked()

    # 槽函数1：标签页切换（参数为新标签的索引）
    def on_tab_changed(self, index):
        tab_text = ''
        with open(CONFIG_PATH, 'r') as file:
            settings = json.load(file)
        sender_obj = self.sender()  # 使用 self.sender() 获取发送者
        if sender_obj == self.tabWidget:
            tab_text = index  # 获取标签页标题
            print(f"已切换到：{tab_text}（索引：{index}）")
            gv.tab_index = tab_text
            settings["tab_index"] = tab_text
            if index == 1:
                self.comboBox.addItems(self.list_capture_devices())
        with open(CONFIG_PATH, 'w') as file:
            json.dump(settings, file, indent=4)

    def on_text_changed(self):
        """
            处理文本输入框内容变化的事件。
            根据发送信号的文本输入框控件，更新配置字典中相应的键值对，并保存配置文件。
            同时，打印输出文本输入框的名称及其当前内容。
            """
        text = ''
        with open(CONFIG_PATH, 'r') as file:
            settings = json.load(file)
        sender_obj = self.sender()  # 使用 self.sender() 获取发送者
        if sender_obj == self.lineEdit:
            text = self.lineEdit.text()  # 读取 self.lineEdit 的内容
            gv.server_ip = text
            settings["ip"] = text
        if sender_obj == self.lineEdit_3:
            text = self.lineEdit_3.text()  # 读取 self.lineEdit 的内容
            gv.vmware_ip = text
            settings["vmware_ip"] = text
        if sender_obj == self.lineEdit_4:
            text = self.lineEdit_4.text()  # 读取 self.lineEdit 的内容
            gv.vmware_prot = text
            settings["vmware_prot"] = text
        if sender_obj == self.lineEdit_5:
            text = self.lineEdit_5.text()  # 读取 self.lineEdit 的内容
            gv.vmware_ip = text
            settings["vmware_password"] = text
        if sender_obj == self.lineEdit_10:
            text = self.lineEdit_10.text()  # 读取 self.lineEdit 的内容
            gv.vid = text
            settings["vid"] = text
        if sender_obj == self.lineEdit_9:
            text = self.lineEdit_9.text()  # 读取 self.lineEdit 的内容
            gv.pid = text
            settings["pid"] = text
        # if sender_obj == self.lineEdit_8:
        #     text = self.lineEdit_8.text()  # 读取 self.lineEdit 的内容
        #     gv.identifier = text
        #     settings["identifier"] = text
        with open(CONFIG_PATH, 'w') as file:
            json.dump(settings, file, indent=4)

    def on_combobox_changed(self):
        """
        处理下拉框选择项变化的事件。
        根据发送信号的下拉框控件，更新配置字典中相应的键值对。
        """
        with open(CONFIG_PATH, 'r') as file:
            settings = json.load(file)
        currentIndex = None
        sender_obj = self.sender()  # 使用 self.sender() 获取发送者
        # if sender_obj == self.ComboBox_2:
        #     currentIndex = self.ComboBox_2.currentIndex()
        #     settings['yjs'] = currentIndex
        #     # 更新用模拟键盘还是易键鼠
        #     pyauto.sign = currentIndex
        if sender_obj == self.ComboBox_3:
            currentIndex = self.ComboBox_3.currentIndex()
            settings['banzhuan'] = currentIndex
            gv.banzhuan = currentIndex
        elif sender_obj == self.comboBox:
            currentIndex = self.comboBox.currentText()
            settings['identifier'] = currentIndex
            gv.identifier = currentIndex
        with open(CONFIG_PATH, 'w') as file:
            json.dump(settings, file, indent=4)

    def update_settings_group_data(self):
        """
        更新设置组数据到组合框中。

        此方法首先通过调用get_settings_group()函数获取最新的设置组列表。
        然后，它清除设置组组合框（self.settingsGroupComboBox）中现有的所有项。
        最后，它将获取到的设置组列表中的每个项目添加到组合框中，以便用户可以从中选择。
        """
        try:
            ret = test_view_subgroups(self.dic.get("cookies"))
            print(ret)
            self.settingsGroupComboBox.clear()
            # # 将获取到的设置组列表中的每个项目添加到组合框中
            self.settingsGroupComboBox.addItems(ret.get('subgroups'))
            # # 调用get_settings_group()函数获取最新的设置组列表
            # settings_group_list = get_settings_group()
            # print(f"settings_group_list:{settings_group_list}")
            # # 清除设置组组合框中现有的所有项
            # self.settingsGroupComboBox.clear()
            # # # 将获取到的设置组列表中的每个项目添加到组合框中
            # self.settingsGroupComboBox.addItems(settings_group_list)
        except Exception as e:
            print("update_settings_group_data:", e)
            print("完整堆栈：")
            traceback.print_exc()
            QMessageBox.information(self, "警告", f"update_settings_group_data: {e}")

    def update_roles_table_data(self):
        """
        更新角色表数据
        :return:
        """

        # role_list = get_all_role_settings(self.settingsGroupComboBox.currentText())
        # print(f"role_list:{role_list}")
        # if role_list is None:
        #     return
        # self.rolesTable.setRowCount(len(role_list))
        # index = 0
        # today = get_date()
        # for role in role_list:
        #     self.rolesTable.setItem(index, 0, QTableWidgetItem(role_list[role]['role_index']))
        #     self.rolesTable.setItem(index, 1, QTableWidgetItem(role_list[role]['role_occupation']))
        #     self.rolesTable.setItem(index, 2, QTableWidgetItem(role_list[role]['height']))
        #     self.rolesTable.setItem(index, 3, QTableWidgetItem(role_list[role]['map_name']))
        #     self.rolesTable.setItem(index, 4, QTableWidgetItem(role_list[role]['map_level']))
        #     if today != role_list[role]['finished_time']:
        #         self.rolesTable.setItem(index, 5, QTableWidgetItem("否"))
        #     else:
        #         self.rolesTable.setItem(index, 5, QTableWidgetItem("是"))
        #     index = index + 1

        """
        更新角色表数据
        :return:
        """
        try:
            # 重置内部数据结构
            self.role_settings = {}
            if not self.settingsGroupComboBox.currentText():
                return
            # 获取新数据
            list_data = []
            ret = test_view_subgroup_config(self.dic.get("cookies"), self.settingsGroupComboBox.currentText())
            # print(f"update_roles_table_data:")
            # pprint.pprint(ret)
            # 检查是否有配置数据
            if not ret or 'configs' not in ret or not ret['configs']:
                # 如果没有数据，清空表格
                self.rolesTable.setRowCount(0)
                return

            # 处理数据
            for item in ret['configs']:
                # pprint.pprint(item)
                list_data.append(str(item['brush_order']))
                self.role_settings[str(item['brush_order'])] = item

            # 设置表格行数
            self.rolesTable.setRowCount(len(self.role_settings))

            # 获取今天的日期用于比较
            today = get_date()

            # 按刷图顺序排序角色
            sorted_roles = sorted(self.role_settings.items(), key=lambda x: int(x[0]))

            # 填充表格
            for index, (role_id, role_data) in enumerate(sorted_roles):
                # 确保我们有足够的数据
                if not role_data:
                    continue

                # 填充每一列数据
                self.rolesTable.setItem(index, 0, QTableWidgetItem(str(role_id)))
                self.rolesTable.setItem(index, 1, QTableWidgetItem(role_data.get('career', '')))
                self.rolesTable.setItem(index, 2, QTableWidgetItem(role_data.get('convert_career', '')))
                self.rolesTable.setItem(index, 3, QTableWidgetItem(str(role_data.get('height', ''))))
                self.rolesTable.setItem(index, 4, QTableWidgetItem(role_data.get('map', '')))
                self.rolesTable.setItem(index, 5, QTableWidgetItem(str(role_data.get('difficulty', ''))))
                self.rolesTable.setItem(index, 7, QTableWidgetItem(str(role_data.get('leave_pl', ''))))

                # 检查是否刷完
                expire_time = role_data.get('brush_map_expire_time', '')
                if expire_time:
                    try:
                        # 转换为日期对象进行比较
                        expire_date = datetime.datetime.strptime(expire_time, '%Y-%m-%d %H:%M:%S')
                        if expire_date.hour < 6:
                            previous_day = expire_date - datetime.timedelta(days=1)
                            expire_date = previous_day.strftime("%Y-%m-%d")
                        else:
                            expire_date = expire_date.strftime("%Y-%m-%d")
                        print(f"302expire_date:{expire_date}")
                        if today != expire_date:
                            self.rolesTable.setItem(index, 6, QTableWidgetItem("否"))
                        else:
                            self.rolesTable.setItem(index, 6, QTableWidgetItem("是"))
                    except ValueError:
                        # 日期格式错误
                        self.rolesTable.setItem(index, 6, QTableWidgetItem("未知"))
                else:
                    self.rolesTable.setItem(index, 6, QTableWidgetItem("否"))
        except Exception as e:
            print("更新角色表格数据异常:", e)
            print("完整堆栈：")
            traceback.print_exc()
            QMessageBox.information(self, "警告", e)

    def start_clicked(self):
        """
        处理开始按钮点击事件的方法。

        此方法首先尝试初始化游戏窗口的相关设置，包括获取窗口句柄、激活窗口以及将其置于最顶层。
        如果在此过程中发生任何异常，则更新日志并提示用户未检测到游戏。
        如果模型加载状态不是"Ready"，则更新日志并提示用户先加载模型。
        如果一切正常，则设置玩家线程的角色组、YOLO处理实例，并初始化并启动玩家线程和检查进程。
        最后，禁用开始按钮以防止重复点击。

        注意：此方法依赖于多个外部定义的属性和方法，如screenshot_util, self.load_model_status,
        self.playerThread, self.yoloProcess, self.settingsGroupComboBox, self.checkProcess,
        以及self.startBtn等。
        """
        if Network == 1:
            try:
                send_request(f_program_version=f_program_version, state=1)

                # 确保显示线程已创建
                if not self.displaythread:
                    # 创建新的显示线程
                    self.displaythread = DisplayThread()
                    self.displaythread.update_signal.connect(self.update_image)
                    self.displaythread.start()
                # 初始化工作线程
                self.playerThread = PlayerThread(dic=self.dic)  # 初始玩家刷图线程

                self.checkProcess = CheckProcess()  # 初始化检查进程
                # 连接播放器线程的信号
                self.playerThread.message.connect(self.update_log)  # 连接消息信号到更新日志的方法
                # self.playerThread.player_dynamics_tuple.connect(self.update_player_dynamics_list)
                self.playerThread.role_table_message.connect(self.update_roles_table_data)  # 连接角色表更新信号
                self.key_press_signal.mouse_moved.connect(self.playerThread.handle_mouse_press)

                self.checkProcess.ghost_state_message.connect(self.playerThread.receive_ghost_state_message)

            except Exception as e:
                # 如果在初始化游戏窗口时发生异常，则更新日志并返回
                self.update_log(f"未检测到游戏:{e}")

                return

            # 设置玩家线程的角色组
            self.playerThread.current_role_group = self.settingsGroupComboBox.currentText()

            # 初始化玩家线程
            self.playerThread.initialize()

            # 启动玩家线程
            self.playerThread.start()

            # 启动检查进程（可能是用于检查游戏状态或其他任务的进程）
            self.checkProcess.start()

            # 禁用开始按钮，防止重复点击
            self.startBtn.setEnabled(False)

    def stop_clicked(self):
        try:
            # 安全停止并销毁工作线程
            if self.playerThread:
                self.playerThread.stop()  # 发送停止信号
                time.sleep(1)
                self.playerThread.terminate()
                self.playerThread = None  # 重置引用

            if self.checkProcess:
                self.checkProcess.stop()
                time.sleep(1)
                self.checkProcess.terminate()
                self.checkProcess = None

            pyauto.releaseallkey()
            self.startBtn.setEnabled(True)
            self.update_log("脚本已停止")


        except Exception as e:
            print("停止操作异常", e)

    def open_settings_group_dialog(self):
        """
        打开设置组对话框的方法。

        此方法调用设置组窗口（self.settings_group_window）的show()方法，使其可见。
        这通常用于提供一个界面，让用户可以选择或配置不同的设置组。
        """
        self.settings_group_window.show()  # 显示设置组窗口

    def open_roles_dialog(self):
        """
        打开角色设置对话框的方法。

        此方法调用角色设置窗口（self.role_settings_window）的show()方法，使其可见。
        这通常用于提供一个界面，让用户可以配置或选择游戏中的角色设置。
        """
        self.role_settings_window.show()  # 显示角色设置窗口

    def receive_update_settings_group_signal(self):
        """
        接收更新设置组数据的信号并处理。

        此方法是一个事件处理器，当接收到指示需要更新设置组数据的信号时被调用。
        它调用update_settings_group_data()方法来获取最新的设置组列表，并更新到UI中的组合框中。
        这样，用户就可以看到最新的设置组选项了。
        """
        # 调用update_settings_group_data方法来更新设置组数据
        self.update_settings_group_data()



    def update_log(self, log):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"{timestamp} - {log}"
        print(log)

        # 添加日志前获取当前滚动位置
        scrollbar = self.logPlainTextEdit.verticalScrollBar()
        prev_value = scrollbar.value()
        prev_max = scrollbar.maximum()

        # 添加日志
        self.logPlainTextEdit.appendPlainText(log_entry)

        # 添加日志后获取新滚动位置
        new_max = scrollbar.maximum()

        # 调试信息
        print(f"添加日志前: {prev_value}/{prev_max}")
        print(f"添加日志后: {scrollbar.value()}/{new_max}")

        # 确保滚动到底部
        if new_max > prev_max:  # 只有文档长度变化时才滚动
            # 方法1: 直接设置最大值
            scrollbar.setValue(new_max)

            # 方法2: 使用文本光标
            cursor = self.logPlainTextEdit.textCursor()
            cursor.movePosition(QtGui.QTextCursor.End)
            self.logPlainTextEdit.setTextCursor(cursor)
            self.logPlainTextEdit.ensureCursorVisible()

            # 强制处理GUI事件
            QtCore.QCoreApplication.processEvents()

            # 再次检查并设置
            if scrollbar.value() < scrollbar.maximum():
                scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        try:
            self.cleanup_vnc()
            # 关闭登录窗口
            self.authapp.close()
            # 如果线程还在运行，等待它结束
            try:
                self.keyboard_thread.stop()  # 停止键盘监听线程
            except Exception as e:
                print("closeEvent", e)
            if self.playerThread:
                self.playerThread.stop()
                self.playerThread.wait(2000)  # 等待2秒安全退出

            if self.checkProcess:
                self.checkProcess.stop()
                self.checkProcess.wait(2000)

            if self.displaythread:
                try:
                    self.displaythread.stop()
                    self.displaythread.wait(1000)
                    self.checkProcess.terminate()
                except:
                    pass
                self.displaythread = None

            # 在窗口关闭之前保存设置
            self.saveSettings("json_resources/ui_config.json")


        except Exception as e:
            print("closeEvent", e)

    def loadSettings(self, filename):
        # 尝试从文件中加载窗口的设置
        try:
            with open(filename, 'r') as file:
                settings = json.load(file)
                self.restoreGeometry(QByteArray.fromBase64(settings['geometry'].encode()))
                self.move(QPoint(settings['x'], settings['y']))
                self.resize(QSize(settings['width'], settings['height']))
        except FileNotFoundError:
            # 如果文件不存在，则使用默认设置
            pass
        except json.JSONDecodeError:
            # 如果文件存在但格式不正确，则使用默认设置并可能给出警告
            print("Warning: Config file is corrupted or not in JSON format.")

    def saveSettings(self, filename):
        # 保存窗口的设置到文件
        geometry = self.saveGeometry().toBase64().data().decode()
        settings = {'geometry': geometry, 'x': self.x(), 'y': self.y(), 'width': self.width(), 'height': self.height()}
        with open(filename, 'w') as file:
            json.dump(settings, file, indent=4)

    def connect_to_vnc(self):
        sender_obj = self.sender()
        if sender_obj == self.startBtn_2:
            if self.VNC is not None:
                QMessageBox.information(self, "提示", f"vnc连接状态：已连接成功")
                return
            image = None
            try:
                vm_ip = self.lineEdit_3.text().strip()
                vm_port = self.lineEdit_4.text().strip()
                vm_pass = self.lineEdit_5.text().strip()
                print(vm_pass)

                if not vm_ip or not vm_port:
                    QMessageBox.warning(self, "错误", "IP和端口不能为空")
                    return

                self.VNC = VNC(vm_ip, vm_port, vm_pass)

                # 截图
                image = self.VNC.capture()
                # 更新共享对象
                pyauto.VNC = self.VNC
                pyauto.pyauto_init(1, 0.05)
                vnc_mm.VNC = self.VNC
                screenshot_util.VNC = self.VNC

                # 保存配置
                self.save_vnc_config(vm_ip, vm_port, vm_pass)
            except Exception as e:
                self.cleanup_vnc()
                print("connect_to_vnc 连接失败:", e)

            if isinstance(image, np.ndarray):
                self.label_7.setText("已连接成功")
                self.label_7.setStyleSheet("color: green;")  # 设置文字为红色
            else:
                self.VNC = None
                self.label_7.setText("状态：连接失败")
                self.label_7.setStyleSheet("color: red;")  # 设置文字为红色
                QMessageBox.information(self, "警告", f"连接失败，请检查ip、端口和密码！")
        elif sender_obj == self.startBtn_4:
            if self.identifier.connection_status:
                QMessageBox.information(self, "提示", f"采集卡连接状态：已连接成功")
                return
            image = None
            try:
                vid_str = self.lineEdit_10.text().strip()
                pid_str = self.lineEdit_9.text().strip()
                # identifier = int(self.lineEdit_8.text().strip())
                identifier = self.comboBox.currentText()
                print(f"identifier:{identifier}")
                if not vid_str or not pid_str or not identifier:
                    QMessageBox.warning(self, "错误", "主控VID和主控PID、采集卡不能为空")
                    return

                # 转换vid和pid
                def convert_to_int(s):
                    if s.startswith('0x') or s.startswith('0X'):
                        # 去掉前缀，然后按16进制转换为整数，再转换为十六进制字符串（带0x前缀）
                        return hex(int(s[2:], 16))
                    else:
                        # 按10进制转换为整数，再转换为十六进制字符串
                        return hex(int(s))

                vid = convert_to_int(vid_str)
                pid = convert_to_int(pid_str)

                self.identifier.connect(int(identifier), (1920, 1080))

                print(f"self.identifier:{self.identifier}")

                # 截图
                image = self.identifier.capture()
                # 更新共享对象
                pyauto.VNC = None
                pyauto.pyauto_init(2, 0.02)
                # 键鼠盒子初始化
                pyauto.init(1920, 1080, vid, pid)
                vnc_mm.VNC = self.identifier
                screenshot_util.VNC = self.identifier
                # 保存配置
                self.save_capturecardconnection_config(vid, pid, identifier)
            except Exception as e:
                self.cleanup_vnc()
                print("connect_to_vnc 连接失败:", e)

            if isinstance(image, np.ndarray):
                self.label_15.setText("已连接成功")
                self.label_15.setStyleSheet("color: green;")  # 设置文字为红色
            else:
                self.VNC = None
                self.label_15.setText("状态：连接失败")
                self.label_15.setStyleSheet("color: red;")  # 设置文字为红色
                QMessageBox.information(self, "警告", f"连接失败，请检查ip、端口和密码！")

    def list_capture_devices(self):
        """
        列出所有可用的视频采集设备
        """
        # 创建采集卡连接实例
        self.identifier = CaptureCardConnection()
        return self.identifier.find_available_devices()

    def save_vnc_config(self, ip, port, password):
        """保存VNC配置到文件"""
        config = get_gui_config()
        config.update({
            "vmware_ip": ip,
            "vmware_prot": port,
            "vmware_password": password
        })
        with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=4, ensure_ascii=False)

    def save_capturecardconnection_config(self, vid, pid, identifier):
        """保存VNC配置到文件"""
        config = get_gui_config()
        config.update({
            "vid": vid,
            "pid": pid,
            "identifier": str(identifier)
        })
        with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=4, ensure_ascii=False)

    def cleanup_vnc(self):
        """清理VNC资源"""
        if self.VNC:
            try:
                api.shutdown()
            except:
                pass
            self.VNC = None

    def update_image(self, qimage):
        pixmap = self.convert_cv_qt(qimage)
        # 改为：先将QImage转换为QPixmap
        pixmap = QPixmap.fromImage(pixmap)
        # 设置pixmap
        self.label_10.setPixmap(pixmap)
        # 调整QLabel大小为图像大小
        # self.resize(pixmap.size())

    def convert_cv_qt(self, cv_img):
        """将OpenCV图像转换为QImage"""
        # OpenCV使用BGR格式，PyQt使用RGB格式
        if len(cv_img.shape) == 3:  # 彩色图像
            # 将BGR转换为RGB
            rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            return QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:  # 灰度图像
            h, w = cv_img.shape
            return QImage(cv_img.data, w, h, w, QImage.Format_Grayscale8)

    def open_local_webpage(self):
        """打开本地HTML文件"""
        # 替换为你的本地HTML文件路径
        # 可以是绝对路径，例如：C:/projects/help/index.html
        # 也可以是相对路径（相对于当前Python文件）
        local_html_path = os.path.join(root_path, 'help.html')

        # 将本地路径转换为QUrl
        url = QUrl.fromLocalFile(local_html_path)

        # 使用系统默认浏览器打开
        if not QDesktopServices.openUrl(url):
            print(f"无法打开文件: {local_html_path}")

    # def open_keyboard_settings(self):
    #     """打开按键配置对话框"""
    #     dialog = KeyConfigDialog(self)
    #     dialog.exec_()
