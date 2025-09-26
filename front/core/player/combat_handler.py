import time
import random
from utils.logging_setup import logger
from core import global_variable as gv
from utils.skill_util import SkillUtil
from core.utils.image_detection import ImageDetection

class CombatHandler:
    def __init__(self):
        """初始化战斗处理器"""
        self.player = None  # 玩家引用，在PlayerThread中设置
        self.mm = None  # 鼠标管理器引用，在PlayerThread中设置
        self.send_log = None  # 日志发送函数，在PlayerThread中设置
        self.operator_module = None  # 操作模块引用，在PlayerThread中设置
        
        # 战斗状态
        self.is_in_combat = False
        self.current_combat_time = 0
        self.last_combat_time = 0
        self.ghost_state = False
        
        # 技能相关
        self.skill_util = SkillUtil()
        self.buff_cooldowns = {}
        self.attack_cooldowns = {}
        self.special_skill_cooldowns = {}
        
        # 战斗配置
        self.combat_config = {
            "basic_buff_interval": 300,  # 基础Buff间隔（秒）
            "special_buff_interval": 600,  # 特殊Buff间隔（秒）
            "combat_timeout": 60,  # 战斗超时时间（秒）
            "skill_cast_delay": 0.2,  # 技能释放延迟（秒）
            "max_attack_count": 10,  # 最大攻击次数
            "boss_room_timeout": 120,  # BOSS房间处理超时时间（秒）
        }
        
        # 图片检测
        self.image_detection = ImageDetection()
        
        # 职业设置
        self.character_class = ""  # 角色职业
        self.character_height = 0  # 角色身高
    
    def apply_config(self, config_data):
        """应用配置数据"""
        if not config_data:
            return
        
        # 更新战斗配置
        if "combat_config" in config_data:
            self.combat_config.update(config_data["combat_config"])
            
    def process_boss_room(self):
        """
        处理Boss房间的逻辑。
        
        如果当前处于Boss房间（self.player.is_boss为True），则执行以下逻辑：
        1. 记录开始时间。
        2. 在刷子（brush_running）运行且非幽灵状态（ghost_state）时循环执行：
           a. 计算已执行时间。
           b. 如果执行时间超过超时设置，则设置幽灵状态（ghost_state）为True并退出循环。
           c. 如果怪物列表（monsters）不为空，则附加一个怪物。
           d. 如果怪物列表为空，则尝试处理通过（process_pass）的逻辑，如果成功，则退出循环。
           e. 无论是否附加怪物或处理通过，都执行获取YOLO结果的逻辑（get_yolo_res）。
        """
        if not self.player or not self.player.is_boss:
            return
        
        logger.info("BOSS房处理")
        start_time = time.time()  # 记录当前时间作为开始时间
        
        while self.player.brush_running and not self.player.ghost_state:
            end_time = time.time()  # 记录当前时间作为结束时间
            execution_time = end_time - start_time  # 计算从开始到当前的执行时间
            
            if execution_time > self.combat_config["boss_room_timeout"]:
                self.player.ghost_state = True  # 设置幽灵状态为True
                logger.info("BOSS房处理超时")
                break  # 退出循环
            
            # 检查是否有怪物
            if (len(self.player.monsters) > 0 or 
                self.player.map_name == "深渊：终末崇拜者" and 
                self.player.is_boss and not self.player.has_continue):
                # 攻击怪物
                if hasattr(self.player, 'attach_monster'):
                    self.player.attach_monster()
            else:
                # 处理通过逻辑
                if hasattr(self.player, 'process_pass'):
                    if (self.player.map_name == "深渊：终末崇拜者" or not self.player.doors):
                        process_status = self.player.process_pass()
                        if process_status:
                            logger.info("BOSS房处理结束")
                            break
                    else:
                        logger.info("BOSS房处理结束")
                        return
            
            # 获取YOLO结果
            if hasattr(self.player, 'get_yolo_res'):
                self.player.get_yolo_res()
    
    def release_buff(self):
        """释放Buff"""
        try:
            if not self.player or not self.operator_module or not self.skill_util:
                logger.warning("战斗组件未初始化完全，无法释放Buff")
                return False
            
            logger.info("释放Buff")
            
            current_time = time.time()
            
            # 检查并释放基础Buff
            if "basic_buff" not in self.buff_cooldowns or \
               current_time - self.buff_cooldowns["basic_buff"] > self.combat_config["basic_buff_interval"]:
                
                # 使用技能工具释放基础Buff
                self.skill_util.cast_basic_buff()
                
                # 更新冷却时间
                self.buff_cooldowns["basic_buff"] = current_time
                
                logger.info("已释放基础Buff")
            
            # 检查并释放特殊Buff
            if "special_buff" not in self.buff_cooldowns or \
               current_time - self.buff_cooldowns["special_buff"] > self.combat_config["special_buff_interval"]:
                
                # 使用技能工具释放特殊Buff
                self.skill_util.cast_special_buff()
                
                # 更新冷却时间
                self.buff_cooldowns["special_buff"] = current_time
                
                logger.info("已释放特殊Buff")
            
            # 根据职业释放特定Buff
            self._release_class_specific_buff()
            
            return True
        except Exception as e:
            logger.error(f"释放Buff异常: {str(e)}")
            return False
    
    def _release_class_specific_buff(self):
        """释放职业特定Buff"""
        try:
            if not self.character_class:
                return
            
            # 根据不同职业释放特定Buff
            if self.character_class == "战士":
                self.skill_util.cast_warrior_buff()
            elif self.character_class == "法师":
                self.skill_util.cast_mage_buff()
            elif self.character_class == "射手":
                self.skill_util.cast_archer_buff()
            elif self.character_class == "刺客":
                self.skill_util.cast_assassin_buff()
            elif self.character_class == "牧师":
                self.skill_util.cast_priest_buff()
        except Exception as e:
            logger.error(f"释放职业特定Buff异常: {str(e)}")
    
    def attack_monster(self):
        """攻击怪物"""
        try:
            if not self.player or not self.operator_module or not self.skill_util:
                logger.warning("战斗组件未初始化完全，无法攻击怪物")
                return False
            
            # 检查是否处于幽灵状态
            if self.ghost_state:
                logger.warning("处于幽灵状态，无法攻击怪物")
                return False
            
            # 更新战斗状态
            self.is_in_combat = True
            self.current_combat_time = time.time()
            
            # 释放Buff（如果需要）
            self.release_buff()
            
            # 检测怪物
            monsters = self._detect_monsters()
            
            if not monsters:
                logger.warning("未检测到怪物")
                self.is_in_combat = False
                return False
            
            # 选择目标怪物
            target_monster = self._select_target_monster(monsters)
            
            if not target_monster:
                logger.warning("未选择到目标怪物")
                self.is_in_combat = False
                return False
            
            # 攻击怪物
            attack_success = self._attack_target_monster(target_monster)
            
            if attack_success:
                logger.info("成功攻击怪物")
            else:
                logger.warning("攻击怪物失败")
                
            # 更新最后战斗时间
            self.last_combat_time = time.time()
            
            return attack_success
        except Exception as e:
            logger.error(f"攻击怪物异常: {str(e)}")
            self.is_in_combat = False
            return False
    
    def _detect_monsters(self):
        """检测怪物"""
        try:
            # 这里应该有检测怪物的逻辑
            # 例如使用图像识别检测游戏画面中的怪物
            
            # 模拟检测到的怪物列表
            monsters = [{"id": 1, "x": 400, "y": 300, "type": "普通", "health": 100}]
            
            return monsters
        except Exception as e:
            logger.error(f"检测怪物异常: {str(e)}")
            return []
    
    def _select_target_monster(self, monsters):
        """选择目标怪物"""
        try:
            if not monsters:
                return None
            
            # 这里应该有选择目标怪物的逻辑
            # 例如优先选择BOSS、精英怪或最近的怪物
            
            # 简化版：返回第一个怪物
            return monsters[0]
        except Exception as e:
            logger.error(f"选择目标怪物异常: {str(e)}")
            return None
    
    def _attack_target_monster(self, target_monster):
        """攻击目标怪物"""
        try:
            if not target_monster:
                return False
            
            # 检查怪物类型并使用相应的攻击策略
            if target_monster["type"] == "BOSS":
                return self._attack_boss(target_monster)
            elif target_monster["type"] == "精英":
                return self._attack_elite(target_monster)
            else:
                return self._attack_normal_monster(target_monster)
        except Exception as e:
            logger.error(f"攻击目标怪物异常: {str(e)}")
            return False
    
    def _attack_boss(self, boss):
        """攻击BOSS"""
        try:
            logger.info(f"攻击BOSS: {boss['id']}")
            
            # 使用技能工具攻击BOSS
            self.skill_util.cast_boss_skill()
            
            # 等待技能释放延迟
            time.sleep(self.combat_config["skill_cast_delay"])
            
            return True
        except Exception as e:
            logger.error(f"攻击BOSS异常: {str(e)}")
            return False
    
    def _attack_elite(self, elite):
        """攻击精英怪"""
        try:
            logger.info(f"攻击精英怪: {elite['id']}")
            
            # 使用技能工具攻击精英怪
            self.skill_util.cast_elite_skill()
            
            # 等待技能释放延迟
            time.sleep(self.combat_config["skill_cast_delay"])
            
            return True
        except Exception as e:
            logger.error(f"攻击精英怪异常: {str(e)}")
            return False
    
    def _attack_normal_monster(self, monster):
        """攻击普通怪物"""
        try:
            logger.info(f"攻击普通怪物: {monster['id']}")
            
            # 使用技能工具攻击普通怪物
            self.skill_util.cast_normal_skill()
            
            # 等待技能释放延迟
            time.sleep(self.combat_config["skill_cast_delay"])
            
            return True
        except Exception as e:
            logger.error(f"攻击普通怪物异常: {str(e)}")
            return False
    
    def clearingobstacles(self):
        """清除障碍物"""
        try:
            if not self.player or not self.operator_module or not self.skill_util:
                logger.warning("战斗组件未初始化完全，无法清除障碍物")
                return False
            
            logger.info("清除障碍物")
            
            # 使用技能工具清除障碍物
            self.skill_util.clear_obstacle()
            
            # 等待技能释放延迟
            time.sleep(self.combat_config["skill_cast_delay"])
            
            logger.info("成功清除障碍物")
            return True
        except Exception as e:
            logger.error(f"清除障碍物异常: {str(e)}")
            return False
    
    def receive_ghost_state_message(self, message):
        """接收幽灵状态消息"""
        try:
            # 解析幽灵状态消息
            if isinstance(message, dict):
                self.ghost_state = message.get("ghost_state", False)
            else:
                # 尝试解析字符串消息
                self.ghost_state = "true" in str(message).lower()
            
            # 更新幽灵状态
            if self.ghost_state:
                logger.info("角色进入幽灵状态")
                self.is_in_combat = False
            else:
                logger.info("角色退出幽灵状态")
        except Exception as e:
            logger.error(f"接收幽灵状态消息异常: {str(e)}")
    
    def reset_combat_state(self):
        """重置战斗状态"""
        try:
            self.is_in_combat = False
            self.current_combat_time = 0
            self.last_combat_time = 0
            self.ghost_state = False
        except Exception as e:
            logger.error(f"重置战斗状态异常: {str(e)}")
    
    def check_combat_timeout(self):
        """检查战斗是否超时"""
        try:
            if not self.is_in_combat:
                return False
            
            current_time = time.time()
            
            # 检查战斗是否超时
            if current_time - self.current_combat_time > self.combat_config["combat_timeout"]:
                logger.warning("战斗超时")
                self.is_in_combat = False
                return True
            
            return False
        except Exception as e:
            logger.error(f"检查战斗是否超时异常: {str(e)}")
            return False
    
    def get_combat_status(self):
        """获取战斗状态"""
        try:
            status = {
                "is_in_combat": self.is_in_combat,
                "current_combat_time": self.current_combat_time,
                "last_combat_time": self.last_combat_time,
                "ghost_state": self.ghost_state,
                "character_class": self.character_class,
                "character_height": self.character_height,
                "buff_cooldowns": self.buff_cooldowns,
                "attack_cooldowns": self.attack_cooldowns,
                "special_skill_cooldowns": self.special_skill_cooldowns
            }
            
            return status
        except Exception as e:
            logger.error(f"获取战斗状态异常: {str(e)}")
            return {}
    
    def update_skill_cooldowns(self):
        """更新技能冷却时间"""
        try:
            current_time = time.time()
            
            # 更新Buff冷却时间
            for buff_type, cooldown_time in list(self.buff_cooldowns.items()):
                if current_time - cooldown_time > self.combat_config["basic_buff_interval"]:
                    del self.buff_cooldowns[buff_type]
            
            # 更新攻击冷却时间
            for skill_type, cooldown_time in list(self.attack_cooldowns.items()):
                # 这里应该根据不同技能设置不同的冷却时间
                if current_time - cooldown_time > 1:  # 假设技能冷却时间为1秒
                    del self.attack_cooldowns[skill_type]
            
            # 更新特殊技能冷却时间
            for skill_type, cooldown_time in list(self.special_skill_cooldowns.items()):
                # 这里应该根据不同特殊技能设置不同的冷却时间
                if current_time - cooldown_time > 10:  # 假设特殊技能冷却时间为10秒
                    del self.special_skill_cooldowns[skill_type]
        except Exception as e:
            logger.error(f"更新技能冷却时间异常: {str(e)}")