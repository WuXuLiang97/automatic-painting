import time
import logging
from PyQt5.QtCore import QObject

logger = logging.getLogger(__name__)

class UIInteractionHandler(QObject):
    """UI交互处理器，负责处理游戏中的各种UI交互操作"""
    
    def __init__(self, player, mm, operator_module):
        super().__init__()
        self.player = player
        self.mm = mm
        self.operator_module = operator_module
    
    def access_account_vault(self, map_name=None):
        """访问账号金库的操作流程
        
        Args:
            map_name: 当前地图名称，用于处理不同地图的特殊逻辑
        
        Returns:
            bool: 是否操作成功
        """
        try:
            logger.info(f"开始访问账号金库，当前地图: {map_name}")
            self.player.send_log("开始访问账号金库")
            
            # 某些地图不支持账号金库操作
            if map_name in ("深渊：终末崇拜者", "跌宕群岛", "妖气追踪"):
                logger.warning(f"地图 {map_name} 不支持账号金库操作")
                return False
            
            # 点击箱子打开仓库
            self.operator_module.move_to(368, 370)
            
            # 风暴逆鳞普通地图的特殊处理
            if map_name == "风暴逆鳞普通":
                time.sleep(1)  # 风暴逆鳞地图需要更长等待时间
                self.operator_module.click()
                time.sleep(0.5)
                
                # 点击上方标签
                self.operator_module.move_to(743, 161)
                time.sleep(0.1)
                
                # 查找账号金库图片并点击
                vault_pos = self.mm.FindPic_sleep(0, 0, 1067, 600, "账号金库.bmp|账号金库a.bmp", 0.9, 1, time_s=5)
                if vault_pos:
                    x, y = vault_pos[0][1], vault_pos[0][2]
                    self.operator_module.move_to(x, y)
                    time.sleep(1)
                    self.operator_module.click()
                    time.sleep(0.1)
                    self.operator_module.click()
                    time.sleep(0.1)
                    
                    # 查找并点击存入按钮
                    deposit_pos = self.mm.FindPic(0, 0, 1067, 600, "存入.bmp", 0.9, 1)
                    if deposit_pos:
                        x, y = deposit_pos[0][1], deposit_pos[0][2]
                        self.operator_module.move_to(x, y)
                        time.sleep(1)
                        self.operator_module.click()
                        time.sleep(0.1)
                        self.operator_module.click()
                        time.sleep(0.1)
                        
                        # 查找并点击一次性转存按钮
                        transfer_pos = self.mm.FindPic(0, 0, 1067, 600, "一次性转存.bmp", 0.9, 1)
                        if transfer_pos:
                            x, y = transfer_pos[0][1], transfer_pos[0][2]
                            self.operator_module.move_to(x, y)
                            time.sleep(0.1)
                            self.operator_module.click()
                            time.sleep(1)
                            
                            # 按下空格确认
                            pyauto.keyPressChar('space')
                            time.sleep(0.1)
                            pyauto.keyPressChar('space')
                            time.sleep(0.1)
                            
                            # 移动到上方标签
                            self.operator_module.move_to(743, 161)
                            time.sleep(0.1)
                            
                            # 处理风暴逆鳞地图的特殊取出操作
                            self._handle_storm_scale_withdrawal(x, y)
            else:
                # 其他地图的标准操作
                time.sleep(0.1)
                self.operator_module.click()
                time.sleep(0.5)
                
                # 查找账号金库图片并点击
                vault_pos = self.mm.FindPic_sleep(0, 0, 1067, 600, "账号金库.bmp|账号金库a.bmp", 0.9, 1, time_s=5)
                if vault_pos:
                    x, y = vault_pos[0][1], vault_pos[0][2]
                    self.operator_module.move_to(x, y)
                    time.sleep(0.1)
                    self.operator_module.click()
                    time.sleep(0.1)
                    
                    # 查找并点击存入按钮
                    deposit_pos = self.mm.FindPic(0, 0, 1067, 600, "存入.bmp", 0.9, 1)
                    if deposit_pos:
                        x, y = deposit_pos[0][1], deposit_pos[0][2]
                        self.operator_module.move_to(x, y)
                        time.sleep(0.1)
                        self.operator_module.click()
                        time.sleep(0.1)
                        self.operator_module.click()
                        time.sleep(0.1)
                        
                        # 查找并点击一次性转存按钮
                        transfer_pos = self.mm.FindPic(0, 0, 1067, 600, "一次性转存.bmp", 0.9, 1)
                        if transfer_pos:
                            x, y = transfer_pos[0][1], transfer_pos[0][2]
                            self.operator_module.move_to(x, y)
                            time.sleep(0.1)
                            self.operator_module.click()
                            time.sleep(1)
                            
                            # 按下空格确认
                            pyauto.keyPressChar('space')
                            time.sleep(0.1)
                            pyauto.keyPressChar('space')
                            time.sleep(0.1)
                            
                            # 移动到上方标签
                            self.operator_module.move_to(743, 161)
                            time.sleep(0.1)
            
            logger.info("账号金库操作完成")
            self.player.send_log("账号金库操作完成")
            return True
        except Exception as e:
            logger.error(f"访问账号金库时发生异常: {str(e)}")
            self.player.send_log(f"访问账号金库异常: {str(e)}")
            return False
    
    def _handle_storm_scale_withdrawal(self, qx, qy):
        """处理风暴逆鳞地图的特殊取出操作"""
        try:
            # 查找并点击放入/取出按钮区域
            ret = self.mm.FindPic_sleep(327, qy, 447, 541, "放入.bmp", 0.9, 1, time_s=2)
            if ret:
                x1, y1, x2, y2 = ret[0][1], ret[0][2] - 10, ret[0][1] + 100, ret[0][2] + 30
                # 查找并点击取出按钮
                take_pos = self.mm.FindPic_sleep(x1, y1, x2, y2, "取出.bmp", 0.9, 1, time_s=2)
                if take_pos:
                    x, y = take_pos[0][1], take_pos[0][2]
                    self.operator_module.move_to(x, y)
                    time.sleep(0.1)
                    self.operator_module.click()
                    time.sleep(0.1)
                    
                    # 查找并点击金库物品
                    vault_item_pos = self.mm.FindPic_sleep(0, 0, 1067, 600, "金库1.bmp", 0.9, 1, time_s=5)
                    if vault_item_pos:
                        x, y = vault_item_pos[0][1], vault_item_pos[0][2]
                        self.operator_module.move_to(x, y + 30)
                        time.sleep(0.1)
                        self.operator_module.click()
                        time.sleep(0.1)
                        
                        # 处理数量输入
                        count_pos = self.mm.FindPic_sleep(0, 0, 1067, 600, "数量.bmp", 0.9, 1, time_s=2)
                        if count_pos:
                            # 生成随机数量
                            import random
                            random_number = random.randint(2000, 2100)
                            random_number_str = str(random_number)
                            
                            # 输入数量
                            for st in random_number_str:
                                pyauto.keyPressChar(st)
                                time.sleep(random.uniform(0.1, 0.15))
                            
                            # 等待输入完成
                            time.sleep(random.uniform(1, 1.55))
                            
                            # 再次点击物品确认
                            self.operator_module.move_to(x, y + 30)
                            time.sleep(0.1)
                            self.operator_module.click()
                            time.sleep(1)
                            
                            # 按下ESC关闭窗口
                            pyauto.keyPressChar("esc")
                            time.sleep(0.1)
        except Exception as e:
            logger.error(f"处理风暴逆鳞地图取出操作时发生异常: {str(e)}")
    
    def _handle_put_items(self):
        """处理放入物品到账号金库的操作"""
        try:
            # 查找并点击放入按钮
            put_pos = self.mm.FindPic(110, 372, 208, 403, "放入.bmp", 0.9)
            if put_pos:
                self.operator_module.move_to(put_pos[0], put_pos[1])
                time.sleep(0.05)
                self.operator_module.click()
                time.sleep(0.5)
        except Exception as e:
            logger.error(f"处理放入物品时发生异常: {str(e)}")
    
    def _handle_take_items(self):
        """处理从账号金库取出物品的操作"""
        try:
            # 查找并点击取出按钮
            take_pos = self.mm.FindPic(110, 372, 208, 403, "取出.bmp", 0.9)
            if take_pos:
                self.operator_module.move_to(take_pos[0], take_pos[1])
                time.sleep(0.05)
                self.operator_module.click()
                time.sleep(0.5)
                
                # 查找并点击金库物品
                vault_item_pos = self.mm.FindPic(273, 301, 462, 331, "金库1.bmp", 0.9)
                if vault_item_pos:
                    self.operator_module.move_to(vault_item_pos[0], vault_item_pos[1])
                    time.sleep(0.05)
                    self.operator_module.click()
                    time.sleep(0.5)
        except Exception as e:
            logger.error(f"处理取出物品时发生异常: {str(e)}")
    
    def close_current_window(self):
        """关闭当前窗口"""
        try:
            # 查找关闭按钮并点击
            close_pos = self.mm.find_close_button()
            if close_pos:
                self.operator_module.click(close_pos)
                time.sleep(0.5)
                return True
            return False
        except Exception as e:
            logger.error(f"关闭窗口时发生异常: {str(e)}")
            return False
    
    def click_confirm_button(self):
        """点击确认按钮"""
        try:
            # 查找确认按钮并点击
            confirm_pos = self.mm.find_confirm_position()
            if confirm_pos:
                self.operator_module.click(confirm_pos)
                time.sleep(0.5)
                return True
            return False
        except Exception as e:
            logger.error(f"点击确认按钮时发生异常: {str(e)}")
            return False