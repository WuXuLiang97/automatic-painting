"""
技能计算
"""
import os
from typing import Tuple, List

import numpy as np

# 定义黄色范围（扩展了范围以包含偏黄颜色）
# lower_yellow = np.array([15, 100, 100])  # 降低下限以包含偏黄颜色
lower_yellow = np.array([15, 100, 100])  # 降低下限以包含偏黄颜色
upper_yellow = np.array([45, 255, 255])  # 增加上限以包含更多黄色变体
"""
技能判断相关类
"""
# 技能区域，381，534 - 408，534（408，561） - 594，534（594，592）
# 横向：一个技能27个像素，7个技能189像素。实际截取213。有6个间隙，每个间隙4
# 纵向：一个技能27个像素，2个技能54像素。实际截取58。有1个间隙，每个间隙4

import cv2
import numpy as np

debug_ing = False

def get_saturated_ratio(img) -> float:
    """
    计算图片饱和度，把饱和度高于阈值的像素区域作为百分比返回
    :param img: 传入的图像块 (BGR格式)
    :return: 高饱和度区域的像素百分比
    """
    # 检查图像是否为空或尺寸过小
    if img is None or img.shape[0] == 0 or img.shape[1] == 0:
        return 0.0

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    s_channel = hsv[:, :, 1]

    # 设定饱和度阈值
    saturation_threshold = 90
    mask = s_channel > saturation_threshold

    # 计算高饱和度像素点的数量并除以总像素点数
    ratio = np.sum(mask) / (img.shape[0] * img.shape[1])
    return ratio


def analyze_yellow_area(img) -> float:
    """
    分析图片中的黄色（或偏黄）面积
    """
    global lower_yellow, upper_yellow
    # 读取图像并转换到HSV颜色空间
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # 获取图像尺寸
    height, width = hsv.shape[:2]
    total_pixels = height * width

    # 创建黄色掩膜
    yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # 计算黄色区域像素数
    yellow_pixels = cv2.countNonZero(yellow_mask)

    # 计算黄色区域占比
    yellow_ratio = yellow_pixels / total_pixels

    # return {
    #     # 图片总像素
    #     "yellow_pixels": yellow_pixels,
    #     # 黄色区域像素
    #     "total_pixels": total_pixels,
    #     # 黄色区域占比
    #     "yellow_ratio": yellow_ratio
    # }
    return yellow_ratio


def analyze_gray_scale(image, threshold=0.7) -> Tuple[bool, float]:
    """
    分析图片的灰度程度

    参数:
        image_path: 图片文件路径
        threshold: 判断为偏灰的阈值，范围0-1，默认0.7

    返回:
        元组 (is_gray, gray_score)，其中：
        - is_gray: 布尔值，表示图片是否偏灰
        - gray_score: 灰度评分，0-1之间，值越高表示越接近灰色
    """
    # 转换到HSV颜色空间
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    # 饱和度越低，颜色越接近灰色
    # 计算平均饱和度并归一化到0-1范围（原始饱和度范围0-255）
    avg_saturation = np.mean(s)
    normalized_saturation = avg_saturation / 255.0

    # 灰度评分：1减去归一化的饱和度（值越高表示越灰）
    gray_score = 1 - normalized_saturation

    # 判断是否偏灰
    is_gray = gray_score >= threshold

    return is_gray, gray_score


def process_image_blocks(image, threshold=0.1) -> List[bool]:
    """
    对输入的图片进行逻辑截取、分区、计算饱和度，并根据阈值判断结果。

    :param image: 使用cv2.imread()读取的原始图片对象
    :param threshold: 判断阈值，默认值为0.1
    :return: 一个包含14个布尔值的列表，元素表示对应方块计算结果是否大于等于阈值
    """
    print("处理技能开始")
    # 1. 定义截取的逻辑参数
    start_x = 381
    start_y = 534
    block_size = 27  # 方块的边长
    gap = 4  # 方块之间的间隔
    num_rows = 2  # 行数
    num_cols = 7  # 每行的方块数

    # 用于保存最终计算结果的列表
    saturation_results = []
    # 用于在可视化图片上绘制矩形
    if debug_ing:
        visualization_image = image.copy()
    block_counter = 1  # 方块计数器，用于命名文件

    # 遍历两行七列
    for row in range(num_rows):
        for col in range(num_cols):
            # 计算当前方块的左上角坐标 (x1, y1)
            x1 = start_x + col * (block_size + gap)
            y1 = start_y + row * (block_size + gap)

            # 计算当前方块的右下角坐标 (x2, y2)
            x2 = x1 + block_size
            y2 = y1 + block_size

            # 【核心】使用切片获取方块区域，这是最高效的方式
            # 它创建的是一个视图(view)，而不是数据的副本(copy)
            # 在实际业务代码中，这将直接用于计算，无需额外内存开销
            block_roi = image[y1:y2, x1:x2]


            if debug_ing:
                output_dir_test = r"E:\test"
                if not os.path.exists(output_dir_test):
                    os.makedirs(output_dir_test)
                    print(f"创建测试目录: {output_dir_test}")

                # 2. todo: (测试用) 将截取的方块保存到指定目录
                file_name = f"{block_counter:02d}.png"  # 格式化为 01, 02, ...
                file_path = os.path.join(output_dir_test, file_name)
                cv2.imwrite(file_path, block_roi)

            # 3. 对每个方块进行计算
            ratio = analyze_yellow_area(block_roi)
            # ratio = analyze_gray_scale(block_roi)
            # 根据阈值判断结果并添加到列表
            saturation_results.append(ratio >= threshold)

            # todo: (测试用) 打印每个方块的结果
            if debug_ing:
                print(f"方块 {block_counter:02d} (坐标: {x1, y1, x2, y2}): 评分 = {ratio}, 是否大于等于阈值 = {ratio >= threshold}")

                # 在可视化图片上绘制方块的边框，方便验证
                cv2.rectangle(visualization_image, (x1, y1), (x2, y2), (0, 255, 0), 1)
                # 在方块上标记序号
                cv2.putText(visualization_image, str(block_counter), (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)


            block_counter += 1

    # 保存带有标记的可视化图片

    if debug_ing:
        cv2.imshow("visualization", visualization_image)
        cv2.waitKey(0)

    return saturation_results


# --- 主程序入口 ---
if __name__ == '__main__':
    debug_ing = True
    # 替换成你自己的图片路径
    image_path = "resources/dnf4.png"

    # 读取图片
    original_image = cv2.imread(image_path)

    if original_image is None:
        print(f"错误：无法读取图片，请检查路径 '{image_path}' 是否正确。")
    else:
        print("\n开始处理图片...")
        # 调用核心函数进行处理
        final_results = process_image_blocks(original_image)

        print("\n--- 计算结果汇总 ---")
        print(final_results)
