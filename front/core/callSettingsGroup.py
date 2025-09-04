import traceback

from PyQt5.QtCore import QStringListModel, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from utils.api import view_subgroups, create_subgroup, delete_subgroup
from view.settingsGroup import Ui_Form


class SettingsGroupWindow(QMainWindow, Ui_Form):
    send_update_settings_group_signal = pyqtSignal()

    def __init__(self, parent=None, dic=None):
        super().__init__(parent)
        self.dic = dic
        self.setupUi(self)
        # 设置窗体禁止最大化
        self.setFixedSize(self.width(), self.height())
        self.list_model = QStringListModel()
        self.list_data = []
        self.init_content()
        # 绑定槽函数
        self.settingsGroupList.clicked.connect(self.clicked_list)

    def init(self):
        pass

    def init_content(self):
        self.update_settings_group_list_data()

    def clicked_list(self, index):
        print(index.data())
        self.settingsGroupName.setText(index.data())

        # settings_group_name = self.list_data[index.row()]
        # self.settingsGroupName.setText(settings_group_name)

    def update_settings_group_list_data(self):
        # self.list_data = get_settings_group()
        # print(self.list_data)
        # self.list_model.setStringList(self.list_data)
        # self.settingsGroupList.setModel(self.list_model)
        try:
            ret = view_subgroups(self.dic.get("cookies"))
            print("获取配置组")
            print(ret)
            self.list_model.setStringList(ret.get('subgroups'))
            self.settingsGroupList.setModel(self.list_model)
        except Exception as e:
            print("update_settings_group_list_data:", e)
            print("完整堆栈：")
            traceback.print_exc()
            QMessageBox.information(self, "警告", f"update_settings_group_list_data: {e}")

    def save_settings_group(self):
        try:
            if self.settingsGroupName.text() == "":
                QMessageBox.information(self, "警告", "配置组名称不能为空")
                return
            # 创建配置组
            ret = create_subgroup(self.dic.get("cookies"), self.settingsGroupName.text())
            # 更新配置组信息
            self.update_settings_group_list_data()
            self.send_update_settings_group_signal.emit()
            if ret.get("message"):
                QMessageBox.information(self, "提示", ret.get("message"))
            else:
                QMessageBox.information(self, "error", ret.get("error"))
        except Exception as e:
            print("save_settings_group:", e)
            print("完整堆栈：")
            traceback.print_exc()
            QMessageBox.information(self, "警告", f"save_settings_group: {e}")
        # # 创建配置组  # save_settings_group(self.settingsGroupName.text())  # # 更新配置组信息  # self.update_settings_group_list_data()  # self.send_update_settings_group_signal.emit()

    def del_settings_group(self):
        try:
            if self.settingsGroupName.text() == "":
                QMessageBox.information(self, "警告", "配置组名称不能为空")
                return
            ret = delete_subgroup(self.dic.get("cookies"), self.settingsGroupName.text())
            if ret.get("message"):
                QMessageBox.information(self, "提示", ret.get("message"))
            else:
                QMessageBox.information(self, "error", ret.get("error"))
            # delete_settings_group(self.settingsGroupName.text())
            self.settingsGroupName.setText("")
            self.update_settings_group_list_data()
            self.send_update_settings_group_signal.emit()
        except Exception as e:
            print("del_settings_group:", e)
            print("完整堆栈：")
            traceback.print_exc()
            QMessageBox.information(self, "警告", f"del_settings_group: {e}")
