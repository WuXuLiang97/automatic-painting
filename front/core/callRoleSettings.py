import traceback
from datetime import datetime, timedelta

from PyQt5.QtCore import QStringListModel
from PyQt5.QtWidgets import QMainWindow, QMessageBox
from config import map_names, map_levels, player_types, player_jobs
from utils.api import (
    view_subgroups,
    delete_subgroup_config,
    delete_subgroup,
    add_subgroup_config,
    view_subgroup_config,
    update_subgroup_config,
)
from view.roleSettings import Ui_Form


def get_yesterday_date():
    now = datetime.now()
    yesterday = now - timedelta(days=2)
    return yesterday.strftime("%Y-%m-%d")


class RoleSettingsWindow(QMainWindow, Ui_Form):
    def __init__(self, parent=None, dic=None):
        super().__init__(parent)
        self.dic = dic
        self.setupUi(self)
        self.list_model = QStringListModel()
        self.list_data = []
        self.role_settings = {}
        self.map_names = map_names
        self.role_occupation_type = player_types
        self.role_occupations = player_jobs
        self.map_levels = map_levels
        self.init_content()
        # 绑定槽函数
        self.roleIndexList.clicked.connect(self.clicked_list)
        self.roleOccupationTypeComboBox.currentTextChanged.connect(
            self.update_settings_roleOccupationComboBox
        )
        # 连接下拉框激活信号到更新角色表数据的方法
        self.settingsGroupComboBox.activated.connect(
            self.update_roles_settings_data
        )  # 假设settingsGroupComboBox是UI中的某个下拉框
        self.modifyRoleSettingsBtn.clicked.connect(self.updateConfig)

    def init_content(self):
        self.mapNameComboBox.addItems(map_names)
        # 职业类型添加列表
        self.roleOccupationTypeComboBox.addItems(self.role_occupation_type)
        # 以职业类型为键得到字典中的角色职业
        role_occupations = self.role_occupations[
            self.roleOccupationTypeComboBox.currentText()
        ]
        # 职业添加列表
        self.roleOccupationComboBox.addItems(role_occupations)
        self.mapLevelComboBox.addItems(self.map_levels)
        self.isBrushComboBox.addItems(["是", "否"])
        self.isDailyTaskComboBox.addItems(["是", "否"])
        self.player_height.setText(str(0))
        self.retainPL.setText(str(0))
        self.update_settings_group_data()
        self.update_roles_settings_data()

    def updateConfig(self):
        """修改配置，不包括刷图序号"""
        try:
            config_data = {
                "brush_order": int(self.roleIndex.text()),
                "career": self.roleOccupationTypeComboBox.currentText(),
                "convert_career": self.roleOccupationComboBox.currentText(),
                "height": int(self.player_height.text()),
                "map": self.mapNameComboBox.currentText(),
                "difficulty": str(self.mapLevelComboBox.currentIndex() + 1),
                "leave_pl": int(self.retainPL.text()),
                "today_task_completed": self.isBrushComboBox.currentText(),
                "everyday_tasks": self.isDailyTaskComboBox.currentText(),
                "brush_map_expire_time": "2025-01-01 00:00:01",
            }
            ret = update_subgroup_config(
                self.dic.get("cookies"),
                self.settingsGroupComboBox.currentText(),
                int(self.roleIndex.text()),
                config_data,
            )
            if ret.get("message"):
                QMessageBox.information(self, "提示", ret.get("message"))
            else:
                QMessageBox.information(self, "error", ret.get("error"))
        except Exception as e:
            print("updateConfig:", e)
            print("完整堆栈：")
            traceback.print_exc()
            QMessageBox.information(self, "警告", f"updateConfig: {e}")

    def update_roles_settings_data(self):
        """
        更新角色设置数据
        :return:
        """
        try:
            if self.settingsGroupComboBox.currentText() != "":
                ret = view_subgroup_config(
                    self.dic.get("cookies"), self.settingsGroupComboBox.currentText()
                )
                print("更新配置")
                print(ret)
                self.list_data.clear()
                for item in ret["configs"]:
                    self.list_data.append(str(item["brush_order"]))
                    self.role_settings[str(item["brush_order"])] = item
                print(f"self.list_data:{self.list_data}")
                self.list_model.setStringList(self.list_data)
                self.roleIndexList.setModel(self.list_model)
        except Exception as e:
            print("update_roles_settings_data:", e)
            print("完整堆栈：")
            traceback.print_exc()
            QMessageBox.information(self, "警告", f"update_roles_settings_data: {e}")

    def update_settings_group_data(self):
        """
        更新设置组数据
        :return:
        """
        try:
            ret = view_subgroups(self.dic.get("cookies"))
            print("获取配置组")
            print(ret)
            self.settingsGroupComboBox.clear()
            self.settingsGroupComboBox.addItems(ret.get("subgroups"))
        except Exception as e:
            print("update_settings_group_data:", e)
            print("完整堆栈：")
            traceback.print_exc()
            QMessageBox.information(self, "警告", f"update_settings_group_data: {e}")

    def update_settings_roleOccupationComboBox(self):
        """
        更新角色职业
        :return:
        """
        self.roleOccupationComboBox.clear()
        role_occupations = self.role_occupations[
            self.roleOccupationTypeComboBox.currentText()
        ]
        self.roleOccupationComboBox.addItems(role_occupations)

    def clicked_list(self, index):
        # 职业列表清空
        self.roleOccupationComboBox.clear()
        role_occupations = self.role_occupations[
            self.roleOccupationTypeComboBox.currentText()
        ]
        # 职业添加列表
        self.roleOccupationComboBox.addItems(role_occupations)
        value = self.list_data[index.row()]
        role_settings = self.role_settings[str(value)]
        print(f"role_settings:{role_settings}")
        try:
            self.roleIndex.setText(str(role_settings["brush_order"]))
            self.roleOccupationTypeComboBox.setCurrentText(role_settings["career"])
            self.roleOccupationComboBox.setCurrentText(role_settings["convert_career"])
            self.player_height.setText(str(role_settings["height"]))
            self.mapNameComboBox.setCurrentText(role_settings["map"])
            self.mapLevelComboBox.setCurrentText(
                self.map_levels[int(role_settings["difficulty"]) - 1]
            )
            self.isBrushComboBox.setCurrentText(role_settings["today_task_completed"])
            self.retainPL.setText(str(role_settings["leave_pl"]))
        except Exception as e:
            print(e)

    def receive_update_settings_group_signal(self):
        """
        接收更新设置组信号
        :return:
        """
        self.update_settings_group_data()

    def save_role_settings(self):
        """
        保存角色设置
        :return:
        """
        try:
            if self.settingsGroupComboBox.currentText() == "":
                QMessageBox.information(self, "警告", "配置组名称不能为空")
                return
            config_data = {
                "brush_order": int(self.roleIndex.text()),
                "career": self.roleOccupationTypeComboBox.currentText(),
                "convert_career": self.roleOccupationComboBox.currentText(),
                "height": int(self.player_height.text()),
                "map": self.mapNameComboBox.currentText(),
                "difficulty": str(self.mapLevelComboBox.currentIndex() + 1),
                "leave_pl": int(self.retainPL.text()),
                "today_task_completed": self.isBrushComboBox.currentText(),
                "everyday_tasks": self.isDailyTaskComboBox.currentText(),
                "brush_map_expire_time": "2025-01-01 00:00:01",
            }
            ret = add_subgroup_config(
                self.dic.get("cookies"),
                self.settingsGroupComboBox.currentText(),
                config_data,
            )
            if ret.get("message"):
                QMessageBox.information(self, "提示", ret.get("message"))
                self.roleIndex.setText(str(int(self.roleIndex.text()) + 1))
            else:
                QMessageBox.information(self, "error", ret.get("error"))
            self.update_roles_settings_data()
        except Exception as e:
            print("更新角色表格数据异常:", e)
            print("完整堆栈：")
            traceback.print_exc()

    def del_role_settings(self):
        """
        del角色设置
        :return:
        """
        try:
            if self.settingsGroupComboBox.currentText() == "":
                QMessageBox.information(self, "警告", "配置组名称不能为空")
                return
            ret = delete_subgroup_config(
                self.dic.get("cookies"),
                self.settingsGroupComboBox.currentText(),
                self.roleIndex.text(),
            )
            if ret.get("message"):
                QMessageBox.information(self, "提示", ret.get("message"))
            else:
                QMessageBox.information(self, "error", ret.get("error"))
            self.update_roles_settings_data()
        except Exception as e:
            print("del_role_settings:", e)
            print("完整堆栈：")
            traceback.print_exc()
            QMessageBox.information(self, "警告", f"del_role_settings: {e}")

    def delall_role_settings(self):
        """
        del所有角色设置
        :return:
        """
        try:
            if self.settingsGroupComboBox.currentText() == "":
                QMessageBox.information(self, "警告", "配置组名称不能为空")
                return
            reply = QMessageBox.question(
                self,
                "提示",
                "你确定要清空角色配置吗？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                ret = delete_subgroup(
                    self.dic.get("cookies"), self.settingsGroupComboBox.currentText()
                )
                if ret.get("message"):
                    QMessageBox.information(self, "提示", ret.get("message"))
                else:
                    QMessageBox.information(self, "error", ret.get("error"))
                self.update_roles_settings_data()
            else:
                pass
        except Exception as e:
            print("delall_role_settings:", e)
            print("完整堆栈：")
            traceback.print_exc()
            QMessageBox.information(self, "警告", f"delall_role_settings: {e}")
