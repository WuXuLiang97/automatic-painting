# -*- coding: utf-8 -*-
import datetime
import logging
from copy import deepcopy

from utils.api import test_view_subgroup_config, test_update_subgroup_config
from utils.common_util import get_date
from core.common import a_mapInfo, occupationInfoMap
from core import global_variable as gv

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """配置管理器类，统一管理角色配置、地图配置的读取和更新"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.all_role_settings = {}
        self.role_index_list = []
        self.current_role_group = None
        self.current_role_index = -1
        
    def set_current_role_group(self, role_group):
        """设置当前角色组"""
        self.current_role_group = role_group
        
    def get_current_role_group(self):
        """获取当前角色组"""
        return self.current_role_group
        
    def set_current_role_index(self, role_index):
        """设置当前角色索引"""
        self.current_role_index = role_index
        
    def get_current_role_index(self):
        """获取当前角色索引"""
        return self.current_role_index
        
    def get_role_index_list(self):
        """获取角色索引列表"""
        return self.role_index_list
        
    def get_all_role_settings(self):
        """获取所有角色设置"""
        return self.all_role_settings
        
    def read_role_config(self, cookies):
        """
        读取当前角色组的配置，并设置当前角色的索引
        
        参数:
            cookies: 用户cookie，用于API调用
            
        返回:
            bool: 是否成功读取配置
        """
        # 清空当前的角色索引列表
        self.role_index_list.clear()
        self.all_role_settings.clear()
        
        # 检查是否设置了角色组
        if not self.current_role_group:
            logger.error("未设置角色组")
            self.current_role_index = -1
            return False
        
        # 获取当前角色组的所有角色设置
        ret = test_view_subgroup_config(cookies, self.current_role_group)
        
        # 检查是否有配置数据
        if not ret or 'configs' not in ret or not ret['configs']:
            logger.warning(f"角色组 {self.current_role_group} 没有配置数据")
            self.current_role_index = -1
            return False
        
        # 处理数据
        list_data = []
        for item in ret['configs']:
            logger.info(item)
            list_data.append(str(item['brush_order']))
            self.all_role_settings[str(item['brush_order'])] = item
            
        # 按刷图顺序排序角色
        self.all_role_settings = dict(sorted(self.all_role_settings.items(), key=lambda x: int(x[0])))
        
        # 如果角色设置为空，则设置当前角色索引为-1并返回
        if len(self.all_role_settings) == 0:
            logger.warning("所有角色设置为空")
            self.current_role_index = -1
            return False
        
        # 遍历所有角色设置，筛选未完成的角色
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
            logger.warning("没有未完成的角色")
            self.current_role_index = -1
            return False
        
        # 将当前角色索引设置为角色索引列表中的第一个索引
        self.current_role_index = self.role_index_list[0]
        logger.info(f"角色索引列表: {self.role_index_list}")
        logger.info(f"当前角色索引: {self.current_role_index}")
        
        return True
        
    def get_current_role_config(self):
        """
        获取当前角色的配置信息
        
        返回:
            dict: 当前角色的配置信息，如果没有则返回None
        """
        if self.current_role_index == -1 or self.current_role_index not in self.all_role_settings:
            logger.warning("当前角色索引无效或不存在")
            return None
        
        return self.all_role_settings[self.current_role_index]
        
    def update_role_config(self, cookies, config_data):
        """
        更新角色配置
        
        参数:
            cookies: 用户cookie，用于API调用
            config_data: 要更新的配置数据
            
        返回:
            bool: 是否更新成功
        """
        if self.current_role_index == -1 or not self.current_role_group:
            logger.warning("当前角色索引无效或角色组未设置")
            return False
        
        try:
            ret = test_update_subgroup_config(cookies, self.current_role_group, self.current_role_index, config_data)
            if ret and not ret.get("error"):
                # 更新成功，刷新本地缓存
                self.read_role_config(cookies)
                return True
            else:
                logger.error(f"更新角色配置失败: {ret.get('error', '未知错误')}")
                return False
        except Exception as e:
            logger.error(f"更新角色配置时发生异常: {str(e)}")
            return False
            
    def update_role_finish_status(self, cookies, leave_pl):
        """
        更新角色完成状态
        
        参数:
            cookies: 用户cookie，用于API调用
            leave_pl: 剩余疲劳值
            
        返回:
            bool: 是否更新成功
        """
        role_settings = self.get_current_role_config()
        if not role_settings:
            return False
            
        # 构造更新数据
        dic_data = {
            'career': role_settings['career'],
            'convert_career': role_settings['convert_career'],
            'height': role_settings['height'],
            'map': role_settings['map'],
            'difficulty': role_settings['difficulty'],
            "brush_map_expire_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'leave_pl': leave_pl
        }
        
        return self.update_role_config(cookies, dic_data)
        
    def get_map_config(self, map_name):
        """
        获取地图配置
        
        参数:
            map_name: 地图名称
            
        返回:
            dict: 地图配置信息，如果没有则返回None
        """
        if map_name not in a_mapInfo:
            logger.warning(f"地图 {map_name} 的配置不存在")
            return None
        
        # 返回地图配置的深拷贝，避免修改原始配置
        return deepcopy(a_mapInfo.get(map_name))
        
    def apply_role_config_to_player(self, player):
        """
        将角色配置应用到玩家对象
        
        参数:
            player: 玩家对象
            
        返回:
            bool: 是否成功应用配置
        """
        role_settings = self.get_current_role_config()
        if not role_settings:
            return False
            
        try:
            # 构造玩家的职业字符串，格式为“职业类型-具体职业”
            player.player_occupation = role_settings['career'] + "-" + role_settings['convert_career']
            logger.info(player.player_occupation)
            
            height = int(role_settings["height"])
            if height != 0:
                player.player_height = height
            else:
                # 根据玩家的职业从occupationInfoMap中获取身高信息
                player.player_height = occupationInfoMap[player.player_occupation].get("height")
            
            # 从角色设置中读取地图名称
            player.map_name = role_settings["map"]
            if player.map_name == "深渊：终末崇拜者":
                gv.sy = True
            else:
                gv.sy = False
                
            # 从角色设置中读取地图等级
            player.map_level = int(role_settings["difficulty"])
            
            # 预留疲劳
            player.pl_value = int(role_settings["leave_pl"])
            
            # 初始化玩家是否获得速度提升的标记为False
            player.has_get_speed = False
            
            # 设置每日任务状态
            player.is_daily_tasks = role_settings["today_task_completed"]
            
            logger.info(f"玩家地图名称: {player.map_name}")
            
            return True
        except Exception as e:
            logger.error(f"应用角色配置到玩家对象时发生异常: {str(e)}")
            return False