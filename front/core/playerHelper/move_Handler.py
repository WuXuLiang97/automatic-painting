class MoveHandler:
    def __init__(self, player_thread):
        self.player_thread = player_thread


        
    def try_move(self):
        if self.player_thread.player_pos.x > 1067 / 2:
            if abs(self.player_thread.player_pos.x - 244) < 200:
                move_info = self.player_thread.compute_move_info_walk(self.player_thread.player_pos, Point(244, 468), 0, 0)  # 计算到最近货物的移动信息
                self.player_thread.send_log("卡点了，尝试移动：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                self.player_thread.movement_recorder.left_right_up_down_move_walk_by(move_info, False)  # 根据移动信息移动
            else:
                move_info = self.player_thread.compute_move_info(self.player_thread.player_pos, Point(244, 468), 0, 0)  # 计算到最近货物的移动信息
                self.player_thread.send_log("卡点了，尝试跑步：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                self.player_thread.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动
        else:
            if abs(self.player_thread.player_pos.x - 244) < 200:
                move_info = self.player_thread.compute_move_info_walk(self.player_thread.player_pos, Point(848, 468), 0, 0)  # 计算到最近货物的移动信息
                self.player_thread.send_log("卡点了，尝试移动：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                self.player_thread.movement_recorder.left_right_up_down_move_walk_by(move_info, False)  # 根据移动信息移动
            else:
                move_info = self.player_thread.compute_move_info(self.player_thread.player_pos, Point(848, 468), 0, 0)  # 计算到最近货物的移动信息
                self.player_thread.send_log("卡点了，尝试跑步：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                self.player_thread.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动

