import math
import os
import random
import sys
import time
import cv2
from loguru import logger
import numpy as np
from utils.common.string import is_chinese
import timeit
from global_fields import (
    STOP_EVENT,
    fields,
    image_queue,
)
from static_fields import (
    image_data_GRAY,
    image_data_HSV,
)


def get_image(filename, color_space=None):
    """
    不输入参数则默认读取灰度图像, 输入参数则为HSV空间图像
    假设所有图像都是.png格式的
    """
    if not filename.lower().endswith((".png", ".bmp")):
        # 如果文件名没有以.png结尾，则添加它
        filename += ".png"
    if color_space is None:
        """根据文件名从内存中获取对应的图片数据"""
        return image_data_GRAY.get(filename)
    else:
        """根据文件名从内存中获取对应的图片数据"""
        return image_data_HSV.get(filename)


def FindPic_sleep(
    screenshot_np,
    x1,
    y1,
    x2,
    y2,
    img_name,
    sim=0.7,
    mc=False,
    drag=None,
    time_s=None,
    my_sleep=0.1,
    delta_color=([0, 0, 0], [179, 255, 255]),
):
    """
    在指定区域内查找图片，支持超时设置。

    Args:
        delta_color: hsv色彩空间中的最小值，和最大值(lower_color,upper_color)
        x1 (int): 查找区域的左上角 x 坐标。
        y1 (int): 查找区域的左上角 y 坐标。
        x2 (int): 查找区域的右下角 x 坐标。
        y2 (int): 查找区域的右下角 y 坐标。
        img_name (str): 要查找的图片的文件名或路径。
        sim (float, optional): 图片相似度阈值，默认值为 0.7。
        mc (bool, optional): 是否返回多个匹配坐标，默认值为 False。
        drag (Any, optional): 其他可选参数，具体取决于 FindPic 方法的实现。
        time_s (float, optional): 超时时间（秒），超过该时间后停止查找。如果为 None，则只执行一次 FindPic 方法。如果为 0，则无限期等待直到找到图片。
        my_sleep (float, optional): 每次找图间隔多长时间
    Returns:
        list: 包含找到的图片坐标的列表，如果未找到图片或超时则返回空列表。
    # 使用示例
    # 只查找一次
    result = self.FindPic_sleep(x1, y1, x2, y2, 'img.png',0.9,1)

    # 无限期查找图片
    result = self.FindPic_sleep(x1, y1, x2, y2, 'img.png',0.9,1, time_s=0)

    # 超时查找图片
    result = self.FindPic_sleep(x1, y1, x2, y2, 'img.png',0.9,1, time_s=5)
    """
    if time_s is None:
        # 如果 time_s 未提供或为 None，则只查找一次
        return FindPic(
            screenshot_np,
            x1,
            y1,
            x2,
            y2,
            img_name,
            sim=sim,
            mc=mc,
            drag=drag,
            delta_color=delta_color,
        )
    elif time_s == 0:
        # 如果 time_s 为 0，则无限期查找图片，直到找到为止
        while (
            not STOP_EVENT.is_set()
        ):  # 线程检测STOP_EVENT是否为False，如果是则继续循环
            result = FindPic(
                screenshot_np,
                x1,
                y1,
                x2,
                y2,
                img_name,
                sim=sim,
                mc=mc,
                drag=drag,
                delta_color=delta_color,
            )
            if result:
                # 如果找到了图片，返回结果
                return result
            time.sleep(1)  # 每次尝试之间休眠 1 秒

    else:
        # 如果 time_s 大于 0，则循环查找，直到超时
        start_time = time.time()
        while (
            not STOP_EVENT.is_set()
        ):  # 线程检测STOP_EVENT是否为False，如果是则继续循环
            result = FindPic(
                screenshot_np,
                x1,
                y1,
                x2,
                y2,
                img_name,
                sim=sim,
                mc=mc,
                drag=drag,
                delta_color=delta_color,
            )
            if result:
                # 如果找到了图片，返回结果
                return result
            elapsed_time = time.time() - start_time
            if elapsed_time >= time_s:
                # 如果超时，则打印信息并返回空列表
                logger.info(f"已超时，未找到图片：{img_name}。")
                return []
            logger.info(f"在 {time_s - elapsed_time} 秒后超时，未找到图片:{img_name}。")
            time.sleep(my_sleep)  # 每次循环等待 0.5 秒
    if STOP_EVENT.is_set():
        logger.info("搜索已停止。")
        return []


def FindPic(
    screenshot_np,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    img_name,
    sim=0.7,
    mc=False,
    drag=None,
    delta_color=([0, 0, 0], [179, 255, 255]),
):
    """
    FindPic(self,x1, y1, x2, y2,img_name,sim=0.7,use_hsv=False,Multiple_coordinates=False,drag=None)
    找到图就返回[[id,x,y]],找不到图则返回[],这里的id,为第几张图片,从0开始:x,y为找到图的中心坐标+随机偏移 0 到 2 。
    x1 整形数:区域的左上X坐标
    y1 整形数:区域的左上Y坐标
    x2 整形数:区域的右下X坐标
    y2 整形数:区域的右下Y坐标
    img_name 字符串:
        图片名,可以是多个图片,比如"test.png|test2.png|test3.png,要用"|"隔开；图片的路径和名字不能有中文,比如"1.png,test2.png"
    sim 浮点数:
        相似度,取值范围0.1-1.0
    mc:
        布尔值,True或False、1或0 ,默认False,为True或1时返回找到的多个坐标,否则只返回找到的第一个坐标
    drag:
        是否在找到的位置画图并显示,默认不画
        drag==1时画图并显示，彩色图片
        drag==2时画图并显示，过滤颜色后的图片
        drag==3时画图并显示，过滤颜色后的灰度图片
        drag==4时画图并显示，过滤颜色后的二值化图片
    delta_color：
        hsv空间的过滤色彩范围
    返回值：[[0, 338, 232, 320, 210], [0, 339, 332, 321, 310], [0, 338, 431, 321, 410], [0, 337, 531, 320, 510]]
        在返回的多个坐标中：
            每个列表代表找到的一个位置,arr[i][0]代表img_name中的第一张图,arr[i][1]代表img_name中的第二张图
            arr[0][1]arr[0][2]为找到图片的中心（加了随机偏移+2)坐标;arr[0][3]arr[0][4]为找到图片的左上角的坐标
    """
    screenshot_np = None
    start_time = timeit.default_timer()  # 获取当前时间作为开始时间
    # 初始化一个列表来存放返回结果
    arr_ret = []
    screenshot_show_image = screenshot_np

    if screenshot_np is None:
        logger.error("截图获取为空数组")
        return arr_ret
    elif not isinstance(screenshot_np, np.ndarray):
        logger.info("传入的截图不是NumPy数组")
        return arr_ret

    screenshot_np = screenshot_np[y1:y2, x1:x2]

    # 将图像从BGR转换到HSV
    hsv_image = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2HSV)

    # 定义HSV颜色范围
    lower_color = np.array(delta_color[0])
    upper_color = np.array(delta_color[1])

    # 创建一个掩码来只选择落在指定颜色范围内的像素
    mask = cv2.inRange(hsv_image, lower_color, upper_color)

    # 使用掩码从原始BGR图像中提取颜色范围内的像素
    color_filtered_image = cv2.bitwise_and(screenshot_np, screenshot_np, mask=mask)

    # 转换提取的图像到灰度空间（如果模板是灰度的）
    gray_filtered_image = cv2.cvtColor(color_filtered_image, cv2.COLOR_BGR2GRAY)

    # 使用split()方法分割字符串看看传进几个图片
    img_name_array = img_name.split("|")

    for id, img_name in enumerate(img_name_array):

        # 输入图片名返回预加载的图片数据
        template_image = get_image(img_name)
        if template_image is None:
            logger.info(f"模板图片：{img_name}不存在")
            sys.exit(0)
        # 获取图片的尺寸
        h, w = template_image.shape

        # 提取四个角上的像素值
        top_left = template_image[0, 0]  # 左上角
        top_right = template_image[-1, 0]  # 右上角
        bottom_left = template_image[0, -1]  # 左下角
        bottom_right = template_image[-1, -1]  # 右下角
        percentage = None

        # 对比这四个像素值，使用列表推导式和all函数来比较所有像素是否相同
        if all(
            np.array_equal(top_left, pixel)
            for pixel in [top_right, bottom_left, bottom_right]
        ):
            if top_left < 200:
                # 如果四个角上的像素值相同，我们创建一个掩码，其中与左上角像素不同的区域被设置为0（黑色）
                # 假设 templ 是一个形状为 (height, width, 3) 的三通道图像数组
                # 假设 top_left 是一个形状为 (3,) 的数组，包含 RGB 三个通道的值

                # 使用NumPy的向量化操作创建掩码
                mask = (template_image != top_left).any(axis=-1).astype(np.uint8)

                # 应用掩码到模板图像：将掩码中为0的像素在模板图像中对应位置设置为0
                template_image[mask == 0] = 0  # 假设0是模板匹配中不会匹配的值

            else:
                logger.info(
                    "如果是透明图请将透明部分用大漠综合工具设置为黑色，注意透明部分不能为白色"
                )
        else:
            pass
            # logger.info("四个角上的像素值——不相同。")
            # 匹配图像
        if gray_filtered_image.shape[0] < h or gray_filtered_image.shape[1] < w:
            continue
        result = cv2.matchTemplate(gray_filtered_image, template_image, 5)

        # 找出匹配的区域
        loc = np.where(result >= sim)
        """如果多个符合相似度则返回多个的坐标，例如(array([210, 310, 310, 310, 410, 410, 410, 510, 510], dtype=int64),
            array([320, 319, 320, 321, 319, 320, 321, 319, 320], dtype=int64))前面的arrary()是y坐标,后面的arrary()是x坐标"""

        # 使用 loc 中的索引从 result 中获取对应的相似度的值
        values = result[loc[0], loc[1]]
        # logger.info_if_enabled(values)
        # 输出[0.9536035  0.9617588  0.96420443 0.9806926  0.95081407 0.9815434   0.9661575  0.9131024  0.95362145]

        # 初始化一个列表来存放匹配结果,这个列表是存放找到当前图片的坐标，每次迭代重新存放
        xy_array = []
        # 获取匹配的区域坐标
        for pt in zip(*loc[::-1]):
            xy_array.append(pt)

        xy_array = process_coordinates(xy_array)

        # 初始化计数器
        count = 0

        for xy in xy_array:

            # 生成随机坐标偏移量
            pard = random.randint(0, 2)

            # 如果最大相似度大于我们设定的值则把找到的坐标加入存放坐标的数组
            arr_ret = print_and_append_coordinates(
                arr_ret, img_name, values[count], xy, w, h, pard, x1, y1, id
            )

            count += 1

            if drag == 1:
                screenshot_show_image = cv2.cvtColor(
                    screenshot_show_image, cv2.COLOR_BGRA2BGR
                )
                # 如果drag为True,则在目标图像上绘制矩形框标记模板位置
                draw_rectangle_if_needed(screenshot_show_image, xy, w, h, drag)
            elif drag == 2:
                screenshot_show_image = color_filtered_image
                # 如果drag为True,则在目标图像上绘制矩形框标记模板位置
                draw_rectangle_if_needed(screenshot_show_image, xy, w, h, drag)
            elif drag == 3:
                screenshot_show_image = gray_filtered_image
                # 如果drag为True,则在目标图像上绘制矩形框标记模板位置
                draw_rectangle_if_needed(screenshot_show_image, xy, w, h, drag)

            # 如果Multiple_coordinates为False，默认为False则只找到第一个坐标后退出循环
            if not mc:
                break

        # 用全局变量called来判断是否启动多线程显示图片，默认为False
        if fields["called"] is True:
            # 将图片数据放入队列中
            image_queue.put(screenshot_show_image)
        else:
            end_time = timeit.default_timer()  # 获取当前时间作为结束时间
            elapsed_time = end_time - start_time  # 计算代码块执行所花费的时间（秒)
            if drag == 1:
                while True:
                    # 显示帧
                    cv2.imshow("image", screenshot_show_image)
                    # 等待按键
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
            elif drag == 2:
                while True:
                    # 显示帧
                    cv2.imshow("image", color_filtered_image)
                    # 等待按键
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
            elif drag == 3:
                while True:
                    # 显示帧
                    cv2.imshow("image", gray_filtered_image)
                    # 等待按键
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
        # 找到图片就不继续找后边的图了
        if len(loc) > 0:
            if not mc:
                break

    return arr_ret


def process_coordinates(coordinates):
    """
    从给定的坐标列表中移除与其他坐标点距离小于阈值的点。

    :param coordinates: 原始坐标列表
    :param threshold_distance: 相近的距离阈值
    :return: 不包含接近点的坐标列表
    """
    # 创建一个新列表来存储不接近的点
    threshold_distance = 10
    # 使用一个集合来存储需要删除的坐标的索引
    to_remove = set()

    # 遍历所有坐标点
    for i in range(len(coordinates)):
        # 遍历剩余的点，与当前点进行比较
        for j in range(i + 1, len(coordinates)):
            # 计算两点之间的距离
            distance = math.sqrt(
                (coordinates[i][0] - coordinates[j][0]) ** 2
                + (coordinates[i][1] - coordinates[j][1]) ** 2
            )

            # 如果距离小于阈值，则标记需要删除的点
            if distance < threshold_distance:
                to_remove.add(j)

                # 创建一个新列表，只包含未被标记为需要删除的点
    cleaned_coordinates = [
        coordinate
        for index, coordinate in enumerate(coordinates)
        if index not in to_remove
    ]

    return cleaned_coordinates


def print_and_append_coordinates(
    arr_ret,
    img_name,
    maxVal,
    maxLoc,
    template_width,
    template_height,
    pard,
    x1,
    y1,
    id,
):
    """
    打印匹配的图像信息，并将坐标信息添加到给定的数组中。

    参数:
    img_name: str, 匹配的图像名称
    maxVal: float, 相似度值
    maxLoc: tuple, 匹配图像在原图中的位置坐标 (x, y)
    template_width: int, 模板图像的宽度
    template_height: int, 模板图像的高度
    pard: int, 偏移量
    x1, y1: int, 坐标调整值
    arr_ret: list, 存储坐标信息的列表
    id: int, 标识信息

    返回值:
    None
    """
    center_x = maxLoc[0] + template_width / 2
    center_y = maxLoc[1] + template_height / 2
    adjusted_center_x = int(center_x + pard + x1)
    adjusted_center_y = int(center_y + pard + y1)
    logger.info_str = f"找到图片：{img_name},相似度：{maxVal};\n"

    if x1 != 0 or y1 != 0:
        logger.info_str += (
            f"       屏幕上的绝对坐标xx: {maxLoc[0] + x1},y:{maxLoc[1] + y1};"
        )
    else:
        logger.info_str += f"       屏幕上的绝对坐标x: {maxLoc[0]},y:{maxLoc[1]};"
    logger.info_str += (
        f"加上按钮中心坐标后x: {adjusted_center_x},y: {adjusted_center_y}\n"
    )

    arr_ret.append(
        [
            id,
            adjusted_center_x,
            adjusted_center_y,
            maxLoc[0] + x1,
            maxLoc[1] + y1,
            maxVal,
            img_name,
        ]
    )
    return arr_ret


def draw_rectangle_if_needed(
    Color_Image, maxLoc, template_width, template_height, drag
):
    """
    如果drag为True，则在目标图像上绘制矩形框标记模板位置。

    参数:
    Color_Image: numpy.ndarray, 目标图像，应该是一个有效的OpenCV图像（cv2.Mat或兼容的numpy数组）
    maxLoc: tuple, 匹配图像在原图中的位置坐标 (x, y)
    template_width: int, 模板图像的宽度
    template_height: int, 模板图像的高度
    drag: bool, 是否需要绘制矩形框

    返回值:
    None
    """
    if drag:
        x, y = maxLoc
        # 打印调试信息，确保Color_Image是numpy数组且形状合理
        logger.info(type(Color_Image))  # 应该输出 <class 'numpy.ndarray'>
        logger.info(
            Color_Image.shape
        )  # 应该输出图像的形状，如 (height, width, channels)
        # 打印将要绘制的矩形的坐标和颜色
        logger.info(f"{(x, y), (x + template_width, y + template_height), (0, 255, 0)}")
        # 在Color_Image上绘制矩形
        cv2.rectangle(
            Color_Image,
            (x, y),
            (x + template_width, y + template_height),
            (0, 255, 0),
            thickness=2,
        )


def is_colored(skill_img: np.ndarray, threshold=30):
    """
    判断图像是否为彩色的。阈值用于确定彩色和灰色的界限。
    """
    # 转换为灰度图像
    gray = cv2.cvtColor(skill_img, cv2.COLOR_BGR2GRAY)

    # 计算每个像素的绝对差值
    diff = cv2.absdiff(skill_img, cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
    diff_sum = np.sum(diff, axis=2)  # 求和RGB通道的差值
    logger.info(f"mm-is_colored:{np.mean(diff_sum)}")
    # 判断差值是否大于阈值
    return np.mean(diff_sum) > threshold


def template_match(max_img, min_img):
    res = cv2.matchTemplate(max_img, min_img, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val < 0.9:
        return None, None
    x, y = list(max_loc)
    return x, y
