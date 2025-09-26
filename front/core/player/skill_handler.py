import time
import random
from ..utils import logger, gv
from ..utils.skill_util import skill_util
from ..utils.image_detection import ImageDetection

class SkillHandler:
    def __init__(self):
        """初始化技能处理器"""
        self.player = None  # 玩家引用，在PlayerThread中设置
        self.mm = None  # 鼠标管理器引用，在PlayerThread中设置
        self.send_log = None  # 日志发送函数，在PlayerThread中设置
        self.operator_module = None  # 操作模块引用，在PlayerThread中设置
        
        # 技能配置
        self.skill_config = {
            "boss_skills": [],  # BOSS技能列表
            "normal_skills": [],  # 普通技能列表
            "buff_skills": [],  # Buff技能列表
            "occupation_skills": {},  # 职业特定技能
        }
        
        # 技能状态
        self.skills_initialized = False
        self.buff_released = False
        self.last_buff_time = 0
        
        # 技能使用冷却时间
        self.skill_cooldowns = {}
        
        # 图片检测
        self.image_detection = ImageDetection()
    
    def apply_config(self, config_data):
        """应用配置数据"""
        if not config_data:
            return
        
        # 更新技能配置
        if "skill_config" in config_data:
            self.skill_config.update(config_data["skill_config"])
        
        # 更新职业技能
        if "occupation_skills" in config_data:
            self.skill_config["occupation_skills"].update(config_data["occupation_skills"])
    
    def initialize_skills(self):
        """初始化技能"""
        try:
            if self.skills_initialized:
                return True
            
            if not self.player or not self.player.player_occupation:
                logger.warning("未设置玩家职业，无法初始化技能")
                return False
            
            logger.info(f"初始化技能，职业：{self.player.player_occupation}")
            
            # 使用skill_util初始化技能
            game_image = self._get_game_screenshot()
            init_status = skill_util.init(game_image, self.player.player_occupation)
            
            if init_status:
                self.skills_initialized = True
                logger.info("技能初始化成功")
            else:
                logger.warning("技能初始化失败")
            
            return init_status
        except Exception as e:
            logger.error(f"初始化技能异常: {str(e)}")
            return False
    
    def release_buff(self):
        """释放Buff"""
        try:
            if self.buff_released and time.time() - self.last_buff_time < 300:  # 5分钟内不重复释放
                return True
            
            logger.info("释放Buff")
            
            # 检查是否初始化技能
            if not self.skills_initialized:
                if not self.initialize_skills():
                    logger.warning("技能未初始化，无法释放Buff")
                    return False
            
            # 释放基础Buff
            self._release_basic_buff()
            
            # 释放职业特定Buff
            self._release_occupation_buff()
            
            # 更新Buff状态
            self.buff_released = True
            self.last_buff_time = time.time()
            
            logger.info("Buff释放完成")
            return True
        except Exception as e:
            logger.error(f"释放Buff异常: {str(e)}")
            return False
    
    def _release_basic_buff(self):
        """释放基础Buff"""
        try:
            # 这里应该有释放基础Buff的逻辑
            # 例如按键释放Buff技能
            pass
        except Exception as e:
            logger.error(f"释放基础Buff异常: {str(e)}")
    
    def _release_occupation_buff(self):
        """释放职业特定Buff"""
        try:
            if not self.player or not self.player.player_occupation:
                return
            
            # 获取职业特定Buff
            occupation_buff = self.skill_config["occupation_skills"].get(self.player.player_occupation, {})
            
            if not occupation_buff:
                return
            
            # 释放职业特定Buff
            # 例如缪斯/q技能组合、召唤师方向键+空格连招等
            pass
        except Exception as e:
            logger.error(f"释放职业特定Buff异常: {str(e)}")
    
    def attack_monster(self):
        """攻击怪物"""
        try:
            logger.info("攻击怪物")
            
            # 检查是否初始化技能
            if not self.skills_initialized:
                if not self.initialize_skills():
                    logger.warning("技能未初始化，无法攻击怪物")
                    return False
            
            # 检查是否有怪物
            if not self.player or not self.player.monsters:
                logger.warning("没有检测到怪物")
                return False
            
            # 判断是否为BOSS房间
            if self.player.is_boss:
                return self._attack_boss()
            else:
                return self._attack_normal_monster()
        except Exception as e:
            logger.error(f"攻击怪物异常: {str(e)}")
            return False
    
    def _attack_boss(self):
        """攻击BOSS"""
        try:
            logger.info("攻击BOSS")
            
            # 这里应该有攻击BOSS的逻辑
            # 例如释放BOSS特定技能组合
            
            # 使用BOSS技能
            self._use_boss_skills()
            
            # 检查BOSS是否被击败
            # if self._is_boss_defeated():
            #     logger.info("BOSS已被击败")
            #     return True
            
            return True
        except Exception as e:
            logger.error(f"攻击BOSS异常: {str(e)}")
            return False
    
    def _attack_normal_monster(self):
        """攻击普通怪物"""
        try:
            logger.info("攻击普通怪物")
            
            # 这里应该有攻击普通怪物的逻辑
            # 例如释放普通技能
            
            # 使用普通技能
            self._use_normal_skills()
            
            return True
        except Exception as e:
            logger.error(f"攻击普通怪物异常: {str(e)}")
            return False
    
    def _use_boss_skills(self):
        """使用BOSS技能"""
        try:
            # 这里应该有使用BOSS技能的逻辑
            # 例如按键释放BOSS技能
            pass
        except Exception as e:
            logger.error(f"使用BOSS技能异常: {str(e)}")
    
    def _use_normal_skills(self):
        """使用普通技能"""
        try:
            # 这里应该有使用普通技能的逻辑
            # 例如按键释放普通技能
            pass
        except Exception as e:
            logger.error(f"使用普通技能异常: {str(e)}")
    
    def _is_boss_defeated(self):
        """检查BOSS是否被击败"""
        try:
            # 这里应该有检查BOSS是否被击败的逻辑
            # 例如检测BOSS血量、检测胜利动画等
            return False
        except Exception as e:
            logger.error(f"检查BOSS是否被击败异常: {str(e)}")
            return False
    
    def _get_game_screenshot(self):
        """获取游戏截图"""
        try:
            # 这里应该有获取游戏截图的逻辑
            # 例如调用截图工具获取截图
            return None
        except Exception as e:
            logger.error(f"获取游戏截图异常: {str(e)}")
            return None
    
    def check_skill_cooldown(self, skill_name):
        """检查技能冷却"""
        try:
            if skill_name not in self.skill_cooldowns:
                return True
            
            return time.time() >= self.skill_cooldowns[skill_name]
        except Exception as e:
            logger.error(f"检查技能冷却异常: {str(e)}")
            return False
    
    def set_skill_cooldown(self, skill_name, cooldown_time):
        """设置技能冷却"""
        try:
            self.skill_cooldowns[skill_name] = time.time() + cooldown_time
        except Exception as e:
            logger.error(f"设置技能冷却异常: {str(e)}")
    
    def reset_skill_status(self):
        """重置技能状态"""
        try:
            self.skills_initialized = False
            self.buff_released = False
            self.last_buff_time = 0
            self.skill_cooldowns = {}
        except Exception as e:
            logger.error(f"重置技能状态异常: {str(e)}")
    
    def process_skill_message(self, message):
        """处理技能消息"""
        try:
            # 这里应该有处理技能消息的逻辑
            # 例如解析消息并执行相应的技能操作
            pass
        except Exception as e:
            logger.error(f"处理技能消息异常: {str(e)}")