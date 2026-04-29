import traceback
from datetime import datetime, timedelta

from PyQt5.QtCore import QStringListModel
from PyQt5.QtWidgets import QMainWindow, QMessageBox

from utils.api import test_view_subgroups, test_delete_subgroup_config, test_delete_subgroup, test_add_subgroup_config, test_view_subgroup_config, test_update_subgroup_config
# from utils.config_util import get_settings_group, get_all_role_settings, save_role_settings, delete_role_settings, delete_all_role_settings
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
        # 设置窗体禁止最大化
        # self.setFixedSize(self.width(), self.height())
        self.list_model = QStringListModel()
        self.list_data = []
        self.role_settings = {}
        self.map_names = ['深渊：最终调律者', '生命巡礼','怀纳千海之天', '深渊：终末崇拜者', '风暴逆鳞普通', '德洛斯矿山外围', '跌宕群岛', '妖气追踪']
        self.role_occupation_type = ["男鬼剑士", "女鬼剑士", "男格斗家", "女格斗家", "男神枪手", "女神枪手", "男魔法师", "女魔法师", "男光职者", "女光职者", "暗夜使者", "守护者", "魔枪士", "枪剑士", "弓箭手", "黑暗武士", "缔造者"]
        self.role_occupations = {"男鬼剑士": {"剑魂", "鬼泣", "狂战士", "阿修罗", "剑影"}, "女鬼剑士": {"驭剑士", "暗殿骑士", "契魔者", "流浪武士", "刃影"}, "男格斗家": {"气功师", "散打", "街霸", "柔道家"}, "女格斗家": {"气功师", "散打", "街霸", "柔道家"}, "男神枪手": {"漫游枪手", "枪炮师", "机械师", "弹药专家", "合金战士"}, "女神枪手": {"漫游枪手", "枪炮师", "机械师", "弹药专家", "协战师"},
                                 "男魔法师": {"元素爆破师", "冰结师", "猩红法师", "逐风者", "次元行者"}, "女魔法师": {"元素师", "召唤师", "战斗法师", "魔道学者", "小魔女"}, "男光职者": {"光明骑士", "蓝拳使者", "驱魔师", "惩戒者"}, "女光职者": {"光明骑士", "正义审判者", "驱魔师", "除恶者"}, "暗夜使者": {"暗星", "黑夜术士", "忍者", "影舞者"}, "守护者": {"混沌魔灵", "帕拉丁", "龙骑士", "精灵骑士"},
                                 "魔枪士": {"征战者", "决战者", "狩猎者", "暗枪士"}, "枪剑士": {"暗刃", "特工", "战线佣兵", "源能专家"}, "弓箭手": {"缪斯", "旅人", "猎人", "妖护使", "奇美拉"}, "黑暗武士": {"黑暗武士"}, "缔造者": {"缔造者"},

                                 }
        self.map_levels = ['普通', '冒险', '勇士', '王者', '噩梦']
        self.init_content()
        # 绑定槽函数
        self.roleIndexList.clicked.connect(self.clicked_list)
        self.roleOccupationTypeComboBox.currentTextChanged.connect(self.update_settings_roleOccupationComboBox)
        # 连接下拉框激活信号到更新角色表数据的方法
        self.settingsGroupComboBox.activated.connect(self.update_roles_settings_data)  # 假设settingsGroupComboBox是UI中的某个下拉框
        self.modifyRoleSettingsBtn.clicked.connect(self.updateConfig)

    def init_content(self):
        self.mapNameComboBox.addItems(self.map_names)
        # 职业类型添加列表
        self.roleOccupationTypeComboBox.addItems(self.role_occupation_type)
        # 以职业类型为键得到字典中的角色职业
        role_occupations = self.role_occupations[self.roleOccupationTypeComboBox.currentText()]
        # 职业添加列表
        self.roleOccupationComboBox.addItems(role_occupations)
        self.mapLevelComboBox.addItems(self.map_levels)
        self.isBrushComboBox.addItems(['是', '否'])
        self.isDailyTaskComboBox.addItems(['是', '否'])
        self.moving_Speed.setText(str(0))
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
                "moving_speed": int(self.moving_Speed.text()),
                "map": self.mapNameComboBox.currentText(),
                "difficulty": str(self.mapLevelComboBox.currentIndex() + 1),
                "leave_pl": int(self.retainPL.text()),
                "today_task_completed": self.isBrushComboBox.currentText(),
                "everyday_tasks": self.isDailyTaskComboBox.currentText(),
                "brush_map_expire_time": "2025-01-01 00:00:01"}
            ret = test_update_subgroup_config(self.dic.get("cookies"), self.settingsGroupComboBox.currentText(), int(self.roleIndex.text()), config_data)
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
                ret = test_view_subgroup_config(self.dic.get("cookies"), self.settingsGroupComboBox.currentText())
                print("更新配置")
                print(ret)
                self.list_data.clear()
                for item in ret['configs']:
                    self.list_data.append(str(item['brush_order']))
                    self.role_settings[str(item['brush_order'])] = item
                # self.role_settings = get_all_role_settings(self.settingsGroupComboBox.currentText())
                # print(self.role_settings)
                # self.list_data.clear()
                # for key in self.role_settings:
                #     self.list_data.append(key)
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
            # # 获取设置组
            # settings_group_list = get_settings_group()
            # self.settingsGroupComboBox.clear()
            # self.settingsGroupComboBox.addItems(settings_group_list)
            ret = test_view_subgroups(self.dic.get("cookies"))
            print("获取配置组")
            print(ret)
            self.settingsGroupComboBox.clear()
            self.settingsGroupComboBox.addItems(ret.get('subgroups'))
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
        role_occupations = self.role_occupations[self.roleOccupationTypeComboBox.currentText()]
        self.roleOccupationComboBox.addItems(role_occupations)

    def clicked_list(self, index):
        # 职业列表清空
        self.roleOccupationComboBox.clear()
        role_occupations = self.role_occupations[self.roleOccupationTypeComboBox.currentText()]
        # 职业添加列表
        self.roleOccupationComboBox.addItems(role_occupations)
        value = self.list_data[index.row()]
        role_settings = self.role_settings[str(value)]
        print(f"role_settings:{role_settings}")
        print(type(role_settings['moving_speed']))
        if role_settings['moving_speed'] is None or role_settings['moving_speed'] == 0:
            moving_speed = "0"
        else:
            moving_speed = role_settings['moving_speed']
        # print(role_settings)
        try:
            self.roleIndex.setText(str(role_settings['brush_order']))
            self.roleOccupationTypeComboBox.setCurrentText(role_settings['career'])
            self.roleOccupationComboBox.setCurrentText(role_settings['convert_career'])
            self.player_height.setText(str(role_settings['height']))
            self.mapNameComboBox.setCurrentText(role_settings['map'])
            self.moving_Speed.setText(str(moving_speed))
            self.mapLevelComboBox.setCurrentText(self.map_levels[int(role_settings['difficulty']) - 1])
            self.isBrushComboBox.setCurrentText(role_settings['today_task_completed'])
            self.retainPL.setText(str(role_settings['leave_pl']))
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
                "moving_speed": int(self.moving_Speed.text()),
                "map": self.mapNameComboBox.currentText(),
                "difficulty": str(self.mapLevelComboBox.currentIndex() + 1),
                "leave_pl": int(self.retainPL.text()),
                "today_task_completed": self.isBrushComboBox.currentText(),
                "everyday_tasks": self.isDailyTaskComboBox.currentText(),
                "brush_map_expire_time": "2025-01-01 00:00:01"}
            ret = test_add_subgroup_config(self.dic.get("cookies"), self.settingsGroupComboBox.currentText(), config_data)
            if ret.get("message"):
                QMessageBox.information(self, "提示", ret.get("message"))
                self.roleIndex.setText(str(int(self.roleIndex.text()) + 1))
                self.moving_Speed.setText(str(0))
            else:
                QMessageBox.information(self, "error", ret.get("error"))
            # save_role_settings(self.settingsGroupComboBox.currentText(),
            #                    {"role_index": self.roleIndex.text(),
            #                     "role_occupation_type": self.roleOccupationTypeComboBox.currentText(),
            #                     "role_occupation": self.roleOccupationComboBox.currentText(),
            #                     "height": self.player_height.text(),
            #                     "map_name": self.mapNameComboBox.currentText(),
            #                     "map_level": self.mapLevelComboBox.currentText(),
            #                     "is_brush": self.isBrushComboBox.currentText(),
            #                     "is_daily_tasks": self.isDailyTaskComboBox.currentText(),
            #                     "retain_pl": self.retainPL.text(),
            #                     "finished_time": get_yesterday_date()})
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
            ret = test_delete_subgroup_config(self.dic.get("cookies"), self.settingsGroupComboBox.currentText(), self.roleIndex.text())
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
        # delete_role_settings(self.settingsGroupComboBox.currentText(), {"role_index": self.roleIndex.text()})  # self.update_roles_settings_data()

    def delall_role_settings(self):
        """
        del所有角色设置
        :return:
        """
        try:
            if self.settingsGroupComboBox.currentText() == "":
                QMessageBox.information(self, "警告", "配置组名称不能为空")
                return
            reply = QMessageBox.question(self, "提示", "你确定要清空角色配置吗？", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                ret = test_delete_subgroup(self.dic.get("cookies"), self.settingsGroupComboBox.currentText())
                if ret.get("message"):
                    QMessageBox.information(self, "提示", ret.get("message"))
                else:
                    QMessageBox.information(self, "error", ret.get("error"))
                # delete_all_role_settings(self.settingsGroupComboBox.currentText())
                self.update_roles_settings_data()
            else:
                pass
        except Exception as e:
            print("delall_role_settings:", e)
            print("完整堆栈：")
            traceback.print_exc()
            QMessageBox.information(self, "警告", f"delall_role_settings: {e}")
