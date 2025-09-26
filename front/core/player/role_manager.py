import datetime
import logging
from PyQt5.QtCore import pyqtSignal, QObject
from core import global_variable as gv
from utils.screenshot_util import screenshot_util
from utils.minimap_util import miniMapUtil
from view.occupation_info import occupationInfoMap
from core.common import a_mapInfo
from utils.common_util import get_date
from utils.api import test_view_subgroup_config
import datetime

logger = logging.getLogger(__name__)

class RoleManager(QObject):
    role_table_message = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.player = None
        self.send_log = None
        self.operator_module = None
        self.current_role_group = None
        self.current_role_index = -1
        self.role_index_list = []
        self.all_role_settings = {}
        
    def read_role_config(self):
        """
        读取当前角色组的配置，并设置当前角色的索引。
        
        首先清空当前的角色索引列表，然后获取当前角色组的所有角色设置。
        如果角色设置为空，则将当前角色索引设置为-1并返回。
        遍历所有角色设置，排除已完成的角色（即完成时间等于当前日期的角色），
        将剩余角色的索引添加到角色索引列表中。
        如果角色索引列表为空，则将当前角色索引设置为-1并返回。
        否则，将当前角色索引设置为角色索引列表中的第一个索引，
        并打印角色索引列表和当前角色索引，最后读取当前角色的配置。
        """
        # 清空当前的角色索引列表
        self.role_index_list.clear()

        # 获取新数据
        list_data = []
        # 获取当前角色组的所有角色设置
        ret = test_view_subgroup_config(self.player.dic.get("cookies"), self.current_role_group)
        # 检查是否有配置数据
        if not ret or 'configs' not in ret or not ret['configs']:
            self.current_role_index = -1
            return

        # 处理数据
        for item in ret['configs']:
            logger.info(item)
            list_data.append(str(item['brush_order']))
            self.all_role_settings[str(item['brush_order'])] = item
        # 按刷图顺序排序角色
        self.all_role_settings = dict(sorted(self.all_role_settings.items(), key=lambda x: int(x[0])))

        # 如果角色设置为空，则设置当前角色索引为-1并返回
        if len(self.all_role_settings) == 0:
            self.current_role_index = -1
            return

        # 遍历所有角色设置
        for role_index in self.all_role_settings:
            logger.info(f"疲劳阈值:{self.all_role_settings[role_index].get('leave_pl')}")
            # 转换为日期对象进行比较
            expire_date = datetime.datetime.strptime(self.all_role_settings[role_index].get("brush_map_expire_time"), '%Y-%m-%d %H:%M:%S')
            if expire_date.hour < 6:
                previous_day = expire_date - datetime.timedelta(days=1)
                expire_date = previous_day.strftime("%Y-%m-%d")
            else:
                expire_date = expire_date.strftime("%Y-%m-%d")
            logger.info(f"expire_date:{expire_date}")
            # 如果角色的完成时间等于当前日期，则跳过该角色
            if get_date() == expire_date:
                continue  # 否则，将角色索引添加到角色索引列表中
            self.role_index_list.append(role_index)

        # 如果角色索引列表为空，则设置当前角色索引为-1并返回
        if len(self.role_index_list) == 0:
            self.current_role_index = -1
            return
        # 将当前角色索引设置为角色索引列表中的第一个索引
        self.current_role_index = self.role_index_list[0]
        self.role_table_message.emit()

        # 打印角色索引列表和当前角色索引
        logger.info(self.role_index_list)
        logger.info(self.current_role_index)

        # 读取当前角色的配置
        self.read_current_role_config()
        
    def read_current_role_config(self):
        """
        读取当前角色的配置信息，并更新玩家对象的相应属性。
        
        此方法从当前角色的设置中获取职业、身高、地图名称和地图等级等信息，
        并将这些信息更新到玩家对象中。同时，还会设置小地图的名称。
        """
        # 从所有角色设置中根据当前角色索引获取当前角色的设置
        role_settings = self.all_role_settings[self.current_role_index]

        # 构造玩家的职业字符串，格式为“职业类型-具体职业”
        self.player.player_occupation = role_settings['career'] + "-" + role_settings['convert_career']
        
        # 更新玩家对象的其他属性
        if hasattr(self.player.player, 'player_occupation'):
            self.player.player.player_occupation = self.player.player_occupation
        
        # 设置地图信息
        self.player.map_name = role_settings['map_name']
        self.player.map_level = role_settings['map_level']
        
        # 发送日志
        if self.send_log:
            self.send_log(f"当前执行到第{self.current_role_index}个角色")
        
    def select_role(self):
        """
        选择角色的逻辑实现
        """
        while self.player.brush_running:
            # 选择角色状态
            select_role_status = self.operator_module.select_role(self.player.waiting_for_the_text_to_appear, self.current_role_index)
            if select_role_status:
                break
                
    def get_date(self):
        """
        获取当前日期，考虑6点为日期切换点
        """
        return get_date()