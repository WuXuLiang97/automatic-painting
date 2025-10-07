class Map_Handler:
    def __init__(self, player_thread):
        self.player_thread = player_thread

   
    def move_to_next_room(self):
        """
        进入门并尝试移动到门的位置。

        该方法会在游戏或应用程序运行时持续尝试找到门的位置并移动到那里。如果遇到特定条件（如玩家位置无法确定、执行时间过长等），则会执行不同的逻辑。

        注意：该方法假设已经定义了其他方法和属性，如self.brush_running, self.ghost_state, self.get_yolo_res(), self.player_pos等。
        """

        start_time = time.time()  # 记录方法开始执行的时间
        frame_time = time.time()
        logger.info("<开始找门>")  # 打印开始信息
        # 定义变量
        next_direction = "right"  # 默认的移动方向为向右
        already_move = False  # 标记是否已经尝试过左右移动
        up_and_down_move = False
        player_pos_none_count = 0  # 玩家位置为None的计数
        door__pos_none_count = 0  # 门位置为None的计数
        attack = False
        down = False
        if self.player.map_name != "深渊：终末崇拜者":
            # 获取小地图数据
            self.get_min_map_yolo_res()
            current_room = self.player.player_room_id
            logger.info(f"\n<开始找门>\n\t当前房间：{current_room}")
        # 只要游戏在运行且不是幽灵状态，就持续尝试
        while self.brush_running and not self.ghost_state:
            # 如果执行时间过长，则进入幽灵状态并返回
            if time.time() - start_time > 30:
                self.ghost_state = True
                return
            self.get_yolo_res()  # enter_door获取YOLO检测结果
            if time.time() - start_time > 10 and not attack:
                if self.player_pos.x is None:
                    continue

                move_info = self.compute_move_info(self.player_pos, Point(562, 392), 0, 0)
                if move_info is None:
                    continue
                # 移动人物
                self.movement_recorder.left_right_up_down_move_by(move_info, already_move)
                attack = True
                for bj in range(2):
                    if bj == 0:
                        pyauto.keyDownChar("right")
                        time.sleep(0.05)
                        pyauto.keyUpChar("right")
                        time.sleep(0.05)
                    else:
                        pyauto.keyDownChar("left")
                        time.sleep(0.05)
                        pyauto.keyUpChar("left")
                        time.sleep(0.05)
                    game_img = screenshot_util.get_game_screenshot()  # 获取当前游戏屏幕的截图
                    logger.info("找门超时，随便放个技能把怪清理掉")
                    skill = skill_util.get_release_skill(game_img,mode='normal')  # 获取释放普通怪物的技能
                    if skill == "x":  # 如果技能是"x"（平a）
                        pyauto.keyDownChar("x")
                        time.sleep(random.uniform(0.9, 1.2))
                        pyauto.keyUpChar("x")
                        time.sleep(0.05)
                        continue  # 跳过后续代码，继续下一次循环
                    if skill is not None:  # 如果技能不是None
                        if self.player.player_occupation == "弓箭手-缪斯" and skill == "q":
                            pyauto.releaseallkey()
                            time.sleep(0.05)
                            if random.random() < 0.5:
                                if random.random() < 0.5:
                                    pyauto.keyPressChar("q")
                                    time.sleep(0.1)
                                    pyauto.keyPressChar("a")
                                    time.sleep(0.1)
                                else:
                                    pyauto.keyPressChar("w")
                                    time.sleep(0.1)
                                    pyauto.keyPressChar("a")
                                    time.sleep(0.1)
                            else:
                                if random.random() < 0.5:
                                    pyauto.keyPressChar("e")
                                    time.sleep(0.1)
                                else:
                                    pyauto.keyPressChar("a")
                                    time.sleep(0.1)
                        else:
                            logger.info(f"使用技能：{skill}")
                            pyauto.keyPressChar(skill)
                            time.sleep(0.1)

                        start_time_k = time.time()  # 记录当前时间作为开始时间
                        while self.brush_running and not self.ghost_state:  # 进入内层循环等待技能释放完成
                            end_time = time.time()  # 记录当前时间作为结束时间
                            execution_time = end_time - start_time_k  # 计算从开始到当前的执行时间
                            if execution_time > 5 and skill != "ctrl":  # 如果执行时间超过5秒
                                logger.info(f"等待技能释放结束超时")
                                while self.brush_running and not self.ghost_state:
                                    logger.info("技能初始化")
                                    init_status = skill_util.init(screenshot_util.get_game_screenshot(), self.player.player_occupation)
                                    if init_status:
                                        break
                                break  # 退出循环
                            elif execution_time > 10 and skill == "ctrl":
                                logger.info(f"等待技能释放大招结束超时")
                                break  # 退出循环
                            # logger.info('进入内层循环等待技能释放完成')
                            game_img = screenshot_util.get_game_screenshot()  # 更新截图
                            # self.get_yolo_res(game_img)  # 使用技能的时候也推理
                            if self.has_rewards:
                                break  # 退出内层循环
                            release_completed = skill_util.skill_status(game_img)
                            # logger.info("进入内层循环等待技能释放完成,是否已经释放完毕：{}".format(release_completed))
                            if release_completed:  # 检查技能是否已释放完成
                                time.sleep(0.2)  # 稍微等待一下以确保技能确实释放完成
                                break  # 退出内层循环
                            time.sleep(0.2)  # 注意：这里没有else语句来处理技能为None的情况，因为前面的if skill is not None已经涵盖了这种情况——

            # 如果检测到怪物、物品或满足特定条件，则处理
            logger.info("确定门检查怪物数量：{}\t是否有奖励：{}\t是否有继续：{}"
                        "".format(len(self.monsters), self.has_rewards, self.has_continue))
            if len(self.goods) > 0:
                current_room_id = self.player.player_room_id
                pickup_count = self.room_item_pickup_counts.get(current_room_id, 0)
                logger.info(f"找门发现物品，当前房间：{current_room_id}拾取次数：{pickup_count}")
                if pickup_count < 10:
                    logger.info(f"小于10次return去拾取物品")
                    return
                else:
                    logger.info(f"大于10次继续找门过图")
            if len(self.monsters) > 0 or self.has_rewards or self.has_continue:

                if self.has_rewards or self.has_continue:
                    self.process_boss_room()
                return

            # 如果玩家位置为None，则尝试左右移动
            if self.player_pos.x is None or self.player_pos.y is None:

                logger.info("player_pos is none")
                player_pos_none_count += 1
                if player_pos_none_count > 5:
                    player_pos_none_count = 0
                    # 玩家位置恢复
                    self.movement_recorder.spiral_search(self.get_player_position, duration=2)  # self.movement_recorder.up_down_move("down", 0.2)  # self.player_left_right_move()
                continue
            # 清除障碍
            self.clearingobstacles()
            # 获取小地图数据
            self.get_min_map_yolo_res()
            door_pos = None
            logger.info(f"self.player.map_name:{self.player.map_name}")
            if self.player.map_name != "深渊：终末崇拜者":
                # 如果房间ID为None，则跳过本次循环
                if self.player.player_room_id is None:
                    logger.info("enter_door player_room_id is None")
                    continue
                # 打印房间ID
                logger.info(f"ROOM_Id:{self.player.player_room_id}")

                # 查找门的位置
                door_pos = self.find_door_pos(down)
            else:
                if len(self.doors) > 0:
                    door_pos = self.doors[0]
            logger.info(f"door_pos:{type(door_pos)}")
            logger.info(door_pos)
            # 如果没有找到门的位置，则根据当前位置和移动方向尝试左右移动
            if isinstance(door_pos, Point):
                logger.info(f"door_pos:{door_pos.x}, {door_pos.y}")
                if 0 < door_pos.x < 150:
                    door_pos.x = 1
                elif 1067 > door_pos.x > 1067 - 150:
                    door_pos.x = 1100
                frame1_detections = (self.player_pos.x, self.player_pos.y)

                st = time.time()
                if abs(self.player_pos.x - door_pos.x) > 200:
                    move_info = self.compute_move_info(self.player_pos, door_pos, 0, 0)  # 计算到最近货物的移动信息
                    logger.info("向门奔跑：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                    self.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动

                else:
                    move_info = self.compute_move_info_walk(self.player_pos, door_pos, 0, 0)  # 计算到最近货物的移动信息
                    logger.info("向门步行：{}\t{}\t{}\t{}".format(move_info.leftRightDirection, move_info.xTime, move_info.upDownDirection, move_info.yTime))
                    self.movement_recorder.left_right_up_down_move_by(move_info, False)  # 根据移动信息移动
                # 不是深渊
                if self.player.map_name != "深渊：终末崇拜者":
                    current_room_id = self.player.player_room_id
                    moves_count = self.Number_of_moves_to_the_next_room.get(current_room_id, 0)
                    if self.player.player_room_id is not None:
                        if current_room_id not in self.Number_of_moves_to_the_next_room:
                            self.Number_of_moves_to_the_next_room[current_room_id] = 0  # 手动初始化
                        self.Number_of_moves_to_the_next_room[current_room_id] += 1  # 现在可以安全执行
                        logger.info(f"当前房间 {current_room_id}移动次数+1")
                        logger.info(f"当前房间{current_room_id}移动次数: {moves_count}")
                self.to_door_count += 1
                logger.info(f"朝门移动耗时：{time.time() - st}秒")
                already_move = False
                time.sleep(0.1)
                ret = self.mm.FindPic(0, 0, 1067, 600, "未拾取.bmp", 0.8, delta_color=([23, 0, 0], [30, 93, 222]))
                if ret:
                    logger.info("有未拾取物品，等待3秒过门")
                    time.sleep(3)
                # 释放所有按键并重置技能状态
                pyauto.releaseallkey()
                # 设置首次攻击怪物的标志
                self.is_first_attack_monster = True
                if self.player.map_name != "深渊：终末崇拜者":
                    current_room_id = self.player.player_room_id
                    moves_count = self.Number_of_moves_to_the_next_room.get(current_room_id, 0)
                    if moves_count > 5 and current_room == current_room_id:
                        logger.info(f"当前房间找门移动次数：{moves_count}\t记录房间：{current_room}\t当前房间：{current_room_id}")
                        already_move = False
                        if not up_and_down_move:
                            logger.info("尝试向上移动")
                            self.movement_recorder.up_down_move("up", 1)
                            up_and_down_move = True
                        else:
                            logger.info("尝试向下移动")
                            self.movement_recorder.up_down_move("down", 1)
                            up_and_down_move = False
                        self.move_handler.try_move()
                        logger.info(f"解除卡点重置为0")
                        # 解除卡点重置为0
                        self.Number_of_moves_to_the_next_room[current_room_id] = 0  # 手动初始化


            if isinstance(door_pos, str) and door_pos == "down":
                down = True
                logger.info("门在下面，往下移动1秒")
                self.movement_recorder.up_down_move("down", 1)

            else:
                frame1_detections = (self.player_pos.x, self.player_pos.y)
                if next_direction == "right" and self.player_pos.x > 750:
                    logger.info("现在方向向右，且玩家X轴坐标{}大于750，弹起前进的方向，现在向左走".format(int(self.player_pos.x)))
                    self.movement_recorder.already_left_right_move("left")
                    next_direction = "left"
                    already_move = True
                if next_direction == "left" and self.player_pos.x < 375:
                    logger.info("现在方向向左，且玩家X轴坐标{}小于450，弹起前进的方向，现在向右走".format(int(self.player_pos.x)))
                    self.movement_recorder.already_left_right_move("right")
                    next_direction = "right"
                    already_move = True
                if not already_move:
                    logger.info("没有移动过，现在移动方向为：{}".format(next_direction))
                    self.movement_recorder.already_left_right_move(next_direction)
                    already_move = True

                if time.time() - frame_time > 5:
                    frame_time = time.time()
                    self.get_yolo_res()  # 重新获取YOLO结果，可能是为了更新玩家位置或货物位置
                    if self.player_pos.x is None:
                        logger.info("第二帧没有识别到玩家")
                        continue
                    frame2_detections = (self.player_pos.x, self.player_pos.y)

                    frames = [frame1_detections, frame2_detections]
                    logger.info("检测人物frames:{}".format(frames))
                    # 设置一个位置变化的阈值（这里以像素为单位）
                    movement_threshold = 5  # 如果x或y方向上的变化超过10像素，则认为物体在移动
                    # 跟踪人物并检测运动
                    last_position = None
                    for frame_idx, (x, y) in enumerate(frames):
                        # 检查当前位置是否为None
                        if (x is None) or (y is None):
                            logger.info(f"在帧 {frame_idx + 1} 中，人物位置数据缺失。")
                            break
                        # 如果是第一帧，则没有上一个位置可以比较，直接跳过
                        if last_position is None:
                            last_position = (x, y)
                            continue
                        # 计算当前位置与上一个位置的变化
                        current_position = (x, y)
                        dx, dy = abs(current_position[0] - last_position[0]), abs(current_position[1] - last_position[1])

                        # 判断是否移动
                        if dx > movement_threshold or dy > movement_threshold:
                            logger.info(f"在帧 {frame_idx + 1} 中，人物移动了。")
                        else:
                            logger.info(f"在帧 {frame_idx + 1} 中，人物是静止的。")
                            already_move = False
                            if not up_and_down_move:
                                logger.info("尝试向上移动")
                                self.movement_recorder.up_down_move("up", 1)
                                up_and_down_move = True
                            else:
                                logger.info("尝试向下移动")
                                self.movement_recorder.up_down_move("down", 1)
                                up_and_down_move = False
                                self.move_handler.try_move()

                continue
            logger.info("结束找门")

    def find_door_pos(self, down):
        """
        寻找玩家当前房间内的门的位置。

        首先检查玩家是否在有效的地图中，并且该地图有对应的房间信息。
        然后，根据玩家当前所在的房间ID，查找该房间内的门的位置。
        如果找到符合条件的门，则返回该门的位置；否则返回None。

        Returns:
            DoorPosition: 符合条件的门的位置对象，如果未找到则返回None。
        """
        logger.info("开始找门")
        if not self.is_valid_map():
            logger.info("结束找门（无效地图）")
            return None
        logger.info(f"boss房位置:{self.boss_room_id}")
        priority_direction = 'right'
        # 查找问号房间的路径
        map_direction = None
        # 遍历输出A星地图数据
        for room_list in self.room_info_map:
            logger.info(room_list)
        if self.boss_room_id:
            map_direction = self.find_door_direction()

        if map_direction is None:
            logger.info("map_direction 为空")
            return None  # 如果没有找到当前房间的信息，则返回None
        # 得到房间门筛选信息
        room_info = a_DictInfo.get(self.player.map_name).get(map_direction)
        logger.info(room_info)
        logger.info(f"开始遍历所有门")
        # 遍历所有门的位置，寻找在当前房间内的门
        for door_pos in self.doors:
            logger.info(f"当前遍历的door_pos:{(door_pos.x, door_pos.y)}")
            if (room_info['min_x'] < door_pos.x < room_info['max_x'] and  # 门的x坐标在房间x坐标范围内
                    room_info['min_y'] < door_pos.y <= room_info['max_y']):  # 门的y坐标在房间y坐标范围内
                logger.info("已找到门，结束找门")
                if map_direction == "up":
                    logger.info("向上的门")
                    door_pos.y = door_pos.y - 50
                return door_pos  # 返回找到的门的位置
        if map_direction == "down":
            # 记录人物当前坐标
            logger.info(f"人物坐标: ({self.player_pos.x}, {self.player_pos.y})")

            # 处理门位置数据
            sorted_doors = sorted(self.doors, key=lambda door: door.y)

            # 遍历并记录所有门位置
            for door in self.doors:
                logger.info(f"门位置: ({door.x}, {door.y})")

            # 检查是否有可用门位置
            if not sorted_doors:
                logger.warning("未找到任何门位置数据（self.doors为空）")
                return map_direction

            # 根据方向返回对应门位置
            if down:
                bottom_door = sorted_doors[-1]
                logger.info(f"返回最下方的门位置: ({bottom_door.x}, {bottom_door.y})")
                return bottom_door
            else:
                return map_direction

        logger.info("结束找门,没有找到门")
        return map_direction  # 如果没有找到符合条件的门，则返回None
     
    def find_door_direction(self):
        """
        寻找玩家当前房间内的门的方向，优先寻找问号房和精英房，其次寻找Boss房

        Returns:
            str: 门的方向描述
            None: 未找到符合条件的门
        """
        # 1. 检查缓存
        if self.player.player_room_id in self.direction_dic:
            cached_direction = self.direction_dic[self.player.player_room_id]
            self.door_direction = cached_direction
            logger.info(f"从缓存获取门方向: {cached_direction}")
            return cached_direction

        logger.info("开始寻找门方向...")

        # 2. 搜索问号房和精英房
        query_elite_timeout = 0.5  # 搜索问号/精英房的最大时间
        start_time = time.time()

        while (self.brush_running and
               not self.ghost_state and
               time.time() - start_time < query_elite_timeout):

            time.sleep(0.05)  # 减少CPU使用

            try:
                self.get_min_map_yolo_res()
            except Exception as e:
                logger.info(f"更新小地图信息异常: {str(e)}")

            # 优先处理问号房
            if self.query_room_id:
                direction = self.find_path_to_query_room()
                if direction:
                    logger.info(f"找到问号房方向: {direction}")
                    self.door_direction = direction
                    return direction

            # 其次处理精英房
            if self.elite_room_id:
                direction = self.find_path_to_elite_room()
                if direction:
                    logger.info(f"找到精英房方向: {direction}")
                    self.door_direction = direction
                    return direction

        # 3. 搜索Boss房（如果满足条件）

        if not self.query_room_id and not self.elite_room_id:
            min_rooms = MAP_MIN_ROOMS.get(self.player.map_name, 2)
            logger.info(f"最少房间要求为：{min_rooms}")
            if self.boss_room_id and self.player.player_room_id:
                # 初始化最小距离为无穷大，以及最近的坐标
                min_distance = float('inf')
                # 计算当前坐标与target的距离的平方（避免使用sqrt以提高效率）
                distance_squared = (self.boss_room_id[0] - self.player.player_room_id[0]) ** 2 + (self.boss_room_id[1] - self.player.player_room_id[1]) ** 2
                # 如果当前距离的平方小于已知的最小距离的平方，则更新最小距离和最近的坐标
                if distance_squared < min_distance:
                    min_distance = distance_squared
                    if min_distance == 1:
                        logger.info(f"玩家与boss房距离为1")
                if self.getOpenedRoomsCount() >= min_rooms and min_distance == 1:
                    boss_direction = self.find_path_to_boss_room()
                    if boss_direction:
                        logger.info(f"找到{self.player.map_name} Boss方向: {boss_direction}")
                        self.door_direction = boss_direction
                        return boss_direction

        # # 4. 最后尝试找最近房间
        # nearest_direction = self.find_path_to_nearest_room_to_boss()
        # if nearest_direction:
        #     logger.info(f"找到最近房间方向: {nearest_direction}")
        #     return nearest_direction

        logger.info("未找到任何门方向")
        self.door_direction = ''
        return None
