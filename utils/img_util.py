from typing import Tuple, cast, Optional, List

import cv2
import numpy as np
from numpy import ndarray
from numpy import random


def show0(img: ndarray):
    """
    显示一张图片，并无限期等待按键，直到有按键操作才继续执行。

        :param img: (ndarray): 需要显示的图像数组。
    """
    cv2.imshow("img", img)
    cv2.waitKey(0)


def show1(img: ndarray):
    """
    显示一张图片，并等待1毫秒。常用于在循环中实时显示视频流或动态图像。

        :param img: (ndarray): 需要显示的图像数组。
    """
    cv2.imshow("img", img)
    cv2.waitKey(1)


def end():
    """
    关闭所有由OpenCV创建的窗口。
    """
    cv2.destroyAllWindows()


def crop_image_wh(image: ndarray, region: Tuple[int, int, int, int]) -> ndarray:
    """
    根据指定的起始坐标(x, y)以及宽度和高度来安全地裁剪图像。

    此函数能自动处理边界情况，将裁剪区域限制在图像的实际尺寸内，防止索引越界。
    如果指定的区域完全在图像之外，将返回一个空图像。

        :param image: (ndarray): 原始图像。
        :param region: (Tuple[int, int, int, int]): 期望的裁剪区域，格式为 (x, y, width, height)。
        :return: (ndarray): 裁剪后的图像。如果裁剪区域无效，则返回一个空数组。
    """
    img_h, img_w, _ = image.shape
    x, y, w, h = region

    # 1. 将裁剪的起始点和结束点限制在图像边界之内
    # 起始点 (x1, y1) 不能小于0
    x1 = max(0, x)
    y1 = max(0, y)

    # 结束点 (x2, y2) 不能大于图像的宽高
    x2 = min(img_w, x + w)
    y2 = min(img_h, y + h)

    # 2. 如果计算出的区域是无效的（例如，起始点在结束点之后），NumPy切片会自动返回一个空数组。
    return image[y1:y2, x1:x2]


def crop_image_xy(image: ndarray, region: Tuple[int, int, int, int]) -> ndarray:
    """
    根据左上角和右下角坐标 (x1, y1, x2, y2) 来安全地裁剪图像。

    此函数能自动处理边界情况，将裁剪区域限制在图像的实际尺寸内，防止索引越界。
    如果指定的区域完全在图像之外，或区域无效（如x1>=x2），将返回一个空图像。

        :param image: (ndarray): 原始图像。
        :param region: (Tuple[int, int, int, int]): 期望的裁剪区域，格式为 (x1, y1, x2, y2)，
                                                  代表左上角的x,y和右下角的x,y。
        :return: (ndarray): 裁剪后的图像。如果裁剪区域无效，则返回一个空数组。
    """
    img_h, img_w = image.shape[:2]
    x1, y1, x2, y2 = region

    # 1. 将裁剪坐标限制在图像边界之内
    # 起始点 (start_x, start_y) 不能小于0
    start_x = max(0, x1)
    start_y = max(0, y1)

    # 结束点 (end_x, end_y) 不能大于图像的宽高
    end_x = min(img_w, x2)
    end_y = min(img_h, y2)

    # 2. 如果计算出的区域无效，NumPy的切片操作会自动返回一个空数组。
    return image[start_y:end_y, start_x:end_x]


def process_image_for_color_detection(image: ndarray, color_bounds: Tuple[ndarray, ndarray]) -> ndarray:
    """
    为颜色检测处理图像，包括：转换为HSV色彩空间、应用颜色掩码、执行形态学操作以优化掩码。

        :param image: (ndarray): 输入图像
        :param color_bounds: (Tuple[ndarray, ndarray]): 颜色范围的下界和上界(HSV格式)。
        :return: (ndarray): 处理后的二值化图像掩码，目标颜色区域为白色。
    """
    # 1. 转换到HSV色彩空间
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 2. 应用颜色范围生成掩码
    lower_bound, upper_bound = color_bounds
    mask = cv2.inRange(hsv_image, lower_bound, upper_bound)

    # 3. 形态学操作：先膨胀连接邻近的白色区域，再腐蚀去除小的噪声点。
    kernel = np.ones((5, 5), np.uint8)
    mask_dilated = cv2.dilate(mask, kernel, iterations=2)
    mask_processed = cv2.erode(mask_dilated, kernel, iterations=1)

    return mask_processed


def find_white_area_y_percentage(binary_image: ndarray, threshold_ratio: float = 0.5):
    """
    分析二值图像，从上至下找到第一个不满足白色像素占比阈值的行，从而计算顶部连续白色区域在Y轴上的占比。

        :param binary_image: (ndarray): 二值图像，白色(255)为前景，黑色(0)为背景。
        :param threshold_ratio: (float): 用于判断分界线的阈值比例。某行白色像素数占总宽度的比例若低于此值，则认为不是顶部白色区域的一部分。
        :return: (tuple): (白色区域Y轴占比, 分界线y坐标, 图像高度)。
    """
    h, w = binary_image.shape[:2]

    # 2. 寻找分界线
    boundary_y = h  # 默认为图像高度，表示整个图像都是白色区域
    white_pixel_count_threshold = w * threshold_ratio

    # 3. 从上到下遍历每一行
    for y in range(h):
        # 计算该行白色像素（非零像素）的数量
        white_pixels = cv2.countNonZero(binary_image[y, :])

        # 4. 当白色像素数量首次低于阈值时，记录下该行的y坐标并跳出循环
        if white_pixels < white_pixel_count_threshold:
            boundary_y = y
            break

    # 5. 计算占比
    percentage = (boundary_y / h) * 100

    return percentage, boundary_y, h


def match_template(target: ndarray, template: ndarray, threshold: float = 0.8) -> bool:
    """
    在目标图像中进行模板匹配，并根据置信度阈值返回是否匹配成功。

        :param target: (ndarray): 待搜索的目标图像。
        :param template: (ndarray): 用于搜索的模板图像。
        :param threshold: (float): 匹配的置信度阈值，范围[0.0, 1.0]。
        :return: (bool): 如果找到的最佳匹配置信度大于等于阈值，返回True，否则返回False。
    """
    has_match = cv2.matchTemplate(target, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(has_match)

    return max_val >= threshold


def match_template_binary(target: ndarray, template: ndarray, threshold: float = 0.8) -> bool:
    """
    对目标图片进行二值化处理后，再进行模板匹配。模板本身需要是二值图像。

        :param target: (ndarray): 待搜索的目标图像（将被自动二值化）。
        :param template: (ndarray): 用于搜索的二值模板图像。
        :param threshold: (float): 匹配的置信度阈值，范围[0.0, 1.0]。
        :return: (bool): 如果找到的最佳匹配置信度大于等于阈值，返回True，否则返回False。
    """
    # 将目标图像二值化
    #    a. 首先，将彩色区域转换为单通道灰度图。
    target_patch_gray = cv2.cvtColor(target, cv2.COLOR_BGR2GRAY)

    #    b. 接着，对灰度图进行二值化，以突出特征并减少光照变化的影响。
    #       这一步产出的 `target_patch_binary` 是单通道的二值图像。
    _, binary_target = cv2.threshold(target_patch_gray, 127, 255, cv2.THRESH_BINARY)
    # 模板匹配
    has_match = cv2.matchTemplate(binary_target, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(has_match)

    return max_val >= threshold


def find_all_template_binary(img: ndarray,
                             templates_with_thresholds: List[Tuple[ndarray, float]]
                             ) -> List[Optional[Tuple[int, int]]]:
    """
    通用多模板匹配函数

    :param img: 待搜索的原始图像
    :param templates_with_thresholds: 一个包含元组的列表，每个元组为 (模板图片, 匹配阈值)
    :return: 一个与输入模板列表等长的结果列表，成功为 (x, y) 坐标，失败为 None
    """
    results: List[Optional[Tuple[int, int]]] = []
    img_copy = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, img_copy = cv2.threshold(img_copy, 127, 255, cv2.THRESH_BINARY)

    for template, threshold in templates_with_thresholds:
        res = cv2.matchTemplate(img_copy, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val > threshold:
            results.append(max_loc)
        else:
            results.append(None)
    return results


def match_template_with_mask(target_image: np.ndarray,
                             template: np.ndarray,
                             mask: np.ndarray,
                             method: int = cv2.TM_CCOEFF_NORMED,
                             threshold: float = 0.8,
                             region: Optional[Tuple[int, int, int, int]] = None
                             ) -> bool:
    """
    使用掩码进行模板匹配，只返回是否匹配成功。掩码可以指定模板中哪些部分需要参与匹配。

        :param target_image: (np.ndarray): 待搜索的目标图像。
        :param template: (np.ndarray): 模板图像 (BGR格式)。
        :param mask: (np.ndarray): 掩码图像 (灰度图)，非零区域表示参与匹配。
        :param method: (int): OpenCV模板匹配方法。
        :param region: (Optional[Tuple[int, int, int, int]]): 可选的搜索区域 (x, y, w, h)。
        :param threshold: (float): 置信度阈值。
        :return: (bool): 如果找到的最佳匹配置信度大于等于阈值，返回True。
    """
    confidence, _ = find_template_with_mask(target_image, template, mask, region, method)
    return confidence >= threshold


def load_template_with_mask(template_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    加载带透明通道的模板图片(如PNG)，并自动分离出BGR图像和对应的掩码。

        :param template_path: (str): 模板图片的文件路径。
        :return: (Tuple[np.ndarray, np.ndarray]): 一个元组，包含(BGR模板图像, 掩码图像)。
        :raises FileNotFoundError: 如果图片路径无效。
    """
    # 使用IMREAD_UNCHANGED加载包含alpha通道的图片，支持中文路径
    template_rgba = cv2.imdecode(np.fromfile(template_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)

    if template_rgba is None:
        raise FileNotFoundError(f"无法加载模板图片: {template_path}")

    # 检查是否有alpha通道
    if template_rgba.shape[2] == 4:
        template_bgr = template_rgba[:, :, :3]
        alpha_channel = template_rgba[:, :, 3]
        # 创建掩码：alpha > 0的像素为255（参与匹配），否则为0（不参与匹配）
        mask = np.where(alpha_channel > 0, 255, 0).astype(np.uint8)

        return template_bgr, mask
    else:
        # 如果没有alpha通道，创建全白的掩码，即整个模板都参与匹配
        template_bgr = template_rgba
        mask = np.ones(template_bgr.shape[:2], dtype=np.uint8) * 255
        print(f"模板图片没有透明通道，使用完整掩码")
        return template_bgr, mask


def load_template_binary(template_path: str) -> np.ndarray:
    """
    加载模板图片并将其转换为二值图像。

        :param template_path: (str): 模板图片的文件路径。
        :return: (np.ndarray): 二值化的模板图像。
        :raises FileNotFoundError: 如果图片路径无效。
    """
    # 使用IMREAD_UNCHANGED加载图片，支持中文路径
    template_img = cv2.imdecode(np.fromfile(template_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)

    if template_img is None:
        raise FileNotFoundError(f"无法加载模板图片: {template_path}")

    # 如果是4通道图像，转换为3通道
    if len(template_img.shape) == 3 and template_img.shape[2] == 4:
        template_img = template_img[:, :, :3]

    # 转换为灰度图
    if len(template_img.shape) == 3:
        template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
    else:
        template_gray = template_img

    # 二值化处理
    _, template_binary = cv2.threshold(template_gray, 127, 255, cv2.THRESH_BINARY)

    print(f"二值化模板图片尺寸: {template_binary.shape}")

    return template_binary


def find_template_with_mask(target_image: np.ndarray,
                            template: np.ndarray,
                            mask: np.ndarray,
                            region: Optional[Tuple[int, int, int, int]] = None,
                            method: int = cv2.TM_CCOEFF_NORMED
                            ) -> Tuple[float, Tuple[int, int]]:
    """
    使用掩码在目标图像中进行模板匹配，并返回最佳匹配的置信度和坐标。

        :param target_image: (np.ndarray): 待搜索的目标图像。
        :param template: (np.ndarray): 模板图像 (BGR格式)。
        :param mask: (np.ndarray): 掩码图像 (灰度图)。
        :param region: (Optional[Tuple[int, int, int, int]]): 可选的搜索区域 (x, y, w, h)。
        :param method: (int): OpenCV模板匹配方法。
        :return: (Tuple[float, Tuple[int, int]]): 一个元组，包含(最高置信度, (最佳匹配位置的左上角x, y坐标))。
    """
    search_area = target_image
    offset_x, offset_y = 0, 0

    # 如果指定了搜索区域，则裁剪图像
    if region:
        x, y, w, h = region
        search_area = crop_image_wh(target_image, region)
        offset_x, offset_y = x, y
        # 如果裁剪后的区域为空，则无法进行匹配
        if search_area.size == 0:
            return 0.0, (-1, -1)

    result = cv2.matchTemplate(search_area, template, method, mask=mask)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    best_match_loc: Tuple[int, int]
    # 根据匹配方法的不同，最佳匹配的位置和置信度也不同
    if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
        # 对于平方差方法，值越小匹配越好
        relative_loc = cast(Tuple[int, int], min_loc)
        confidence = 1 - min_val if method == cv2.TM_SQDIFF_NORMED else min_val
    else:
        # 对于相关性系数方法，值越大匹配越好
        relative_loc = cast(Tuple[int, int], max_loc)
        confidence = max_val

    # 将相对坐标转换为绝对坐标
    absolute_x = relative_loc[0] + offset_x
    absolute_y = relative_loc[1] + offset_y
    best_match_loc = (absolute_x, absolute_y)

    return confidence, best_match_loc


def find_template_all_with_mask(target_image: np.ndarray,
                                template: np.ndarray,
                                mask: np.ndarray,
                                confidence_threshold: float = 0.8,
                                method: int = cv2.TM_CCOEFF_NORMED) -> list[tuple[float, tuple[int, int]]]:
    """
    使用掩码在目标图像中进行模板匹配，并返回所有超过置信度阈值的匹配结果。

        :param target_image: (np.ndarray): 待搜索的目标图像。
        :param template: (np.ndarray): 模板图像 (BGR格式)。
        :param mask: (np.ndarray): 掩码图像 (灰度图)。
        :param confidence_threshold: (float): 置信度阈值，默认为0.8。
        :param method: (int): OpenCV模板匹配方法。
        :return: (list[tuple[float, tuple[int, int]]]): 一个列表，包含所有满足条件的匹配结果。
                                                      每个结果是一个元组，格式为 (置信度, (左上角x, y坐标))。
    """
    result = cv2.matchTemplate(target_image, template, method, mask=mask)

    locations = np.where(result >= confidence_threshold)

    matches = []
    for pt in zip(*locations[::-1]):  # 转换为 (x, y) 格式
        confidence = result[pt[1], pt[0]]
        matches.append((confidence, pt))

    return matches


def find_all_template_with_mask(img: ndarray,
                                templates_with_details: List[Tuple[ndarray, ndarray, float]]) -> List[
    Optional[Tuple[int, int]]]:
    """
    使用掩码在图像中进行多模板匹配。

    此函数遍历一个包含模板、掩码和阈值的列表，对每个模板在目标图像中寻找最佳匹配点。
    与 `find_all_template` 不同，此版本利用掩码来精确控制匹配区域，适用于需要忽略模板某些部分（如透明背景）的场景。

    :param img: 待搜索的原始图像 (BGR格式)。
    :param templates_with_details: 一个包含元组的列表，每个元组格式为 (模板图像, 掩码图像, 匹配阈值)。
    :return: 一个与输入模板列表等长的结果列表。如果某个模板的最高匹配置信度超过其阈值，
             则对应位置为最佳匹配点的 (x, y) 坐标；否则为 None。
    """
    results: List[Optional[Tuple[int, int]]] = []

    # 不需要对img进行预处理，因为带掩码的匹配通常在原始彩色图像上进行
    for template, mask, threshold in templates_with_details:
        # 使用掩码进行模板匹配
        res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED, mask=mask)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val > threshold:
            results.append(max_loc)
        else:
            results.append(None)

    return results


def four2three(img) -> np.ndarray:
    # 确保输入图像是3通道BGR格式（兼容VNC的4通道RGBA图像）
    if len(img.shape) == 3 and img.shape[2] == 4:
        img = img[:, :, :3]  # 去掉alpha通道，转换为BGR
    return img


def find_any_match_random(image, template, threshold, num_samples=200):
    """
    通过随机采样快速查找图像中的任意一个匹配项。

    参数:
    - image: 待搜索的原始图像 (建议灰度图)。
    - template: 模板图像 (建议灰度图)。
    - threshold: 匹配的阈值 (e.g., 0.9 for TM_CCOEFF_NORMED)。
    - num_samples: 随机采样的最大次数。

    返回:
    - 如果找到，返回一个元组 (top_left, bottom_right, score)。
    - 如果未找到，返回 None。
    """
    image_h, image_w = image.shape[:2]
    template_h, template_w = template.shape[:2]

    # 定义一个合理的采样区域大小，比模板稍大一些
    # 这样可以确保模板匹配有足够的上下文，并且能覆盖住目标
    roi_w = int(template_w * 1.5)
    roi_h = int(template_h * 1.5)

    # 确定可以随机选择的坐标范围
    max_rand_x = image_w - roi_w
    max_rand_y = image_h - roi_h

    if max_rand_x < 0 or max_rand_y < 0:
        print("错误：图像尺寸小于采样区域尺寸。请尝试全局扫描。")
        # 可以回退到标准方法
        # res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        # ...
        return None

    for i in range(num_samples):
        # 1. 随机选择一个区域的左上角
        rand_x = random.randint(0, max_rand_x)
        rand_y = random.randint(0, max_rand_y)

        # 2. 提取这个随机的小区域 (ROI)
        roi = image[rand_y: rand_y + roi_h, rand_x: rand_x + roi_w]

        # 3. 在这个小ROI上进行模板匹配
        # 如果ROI比模板还小，跳过（虽然上面的逻辑保证了不会发生）
        if roi.shape[0] < template_h or roi.shape[1] < template_w:
            continue

        result = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # 4. 检查是否找到满足阈值的匹配
        if max_val >= threshold:
            print(f"在第 {i + 1} 次随机采样中找到匹配! 得分: {max_val:.4f}")

            # 计算在原始大图中的全局坐标
            global_top_left = (rand_x + max_loc[0], rand_y + max_loc[1])
            global_bottom_right = (global_top_left[0] + template_w, global_top_left[1] + template_h)

            return (global_top_left, global_bottom_right, max_val)

    print(f"在 {num_samples} 次随机采样后仍未找到匹配项。")
    return None
