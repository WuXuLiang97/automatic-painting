class WaitHandler:
    def __init__(self, player_thread):
        # 设定每日开始时间为早上6点
        self.start_hour = 6
        self.player_thread = player_thread

        
    def calculate_wait_time(self):
        """计算距离次日早上六点需要等待的秒数"""
        now = datetime.datetime.now()

        # 计算今天早上六点的时间
        today_6am = now.replace(hour=self.start_hour, minute=random.randint(5,10), second=random.randint(1,58), microsecond=0)

        # 如果当前时间已经过了今天六点，则目标时间是明天六点
        if now >= today_6am:
            tomorrow_6am = today_6am + datetime.timedelta(days=1)
            wait_seconds = (tomorrow_6am - now).total_seconds()
        else:
            # 如果还没到今天六点，则等待到今天六点
            wait_seconds = (today_6am - now).total_seconds()

        return wait_seconds


        
    def wait_until_next_start(self):
        """等待到下一个开始时间（早上六点）"""
        wait_seconds = self.calculate_wait_time()

        # 转换等待时间为小时、分钟、秒，便于阅读
        hours, remainder = divmod(int(wait_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)

        self.player_thread.send_log(f"本日任务已完成，将在 {hours}小时{minutes}分钟{seconds}秒后（即次日{self.start_hour}点）继续运行")

        # 进入等待状态
        time.sleep(wait_seconds)

        # 等待结束后重置任务状态
        self.player_thread.today_task_completed = False
        self.player_thread.send_log("等待结束，准备开始新的任务周期")
