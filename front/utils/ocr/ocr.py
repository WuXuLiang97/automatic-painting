import cv2
from loguru import logger
import numpy as np

from utils.common.image import get_image


def screenshot_OCR_str(
    image, x1, y1, x2, y2, templates_dict, sim, get_colour=None, drag=None
):
    """
    优化后的数字识别方法，专注于识别数字字符

    :param templates_dict: 字典格式的数字模板 {数字字符: [模板文件名列表]}
        示例: {'0': ['0_1.bmp', '0_2.bmp'], '1': ['1.bmp'], ...}
    """
    # 捕获指定区域的屏幕截图
    try:
        screenshot_np = image 
        if isinstance(screenshot_np, np.ndarray):
            pass
        else:
            logger.info("图片不是numpy数组")
            return ""
        region = screenshot_np[y1:y2, x1:x2]
        # 保存原始图像用于调试
        if drag is not None:
            cv2.imwrite("debug_original.png", region)
            logger.info(f"保存原始图像到 debug_original.png")
    except Exception as e:
        logger.info(f"捕获屏幕区域时出错: {e}")
        return ""

    # 颜色空间转换
    if get_colour is not None:
        try:
            processed_img = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        except Exception as e:
            logger.info(f"颜色空间转换错误: {e}")
            return ""
    else:
        try:
            processed_img = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        except Exception as e:
            logger.info(f"灰度转换错误: {e}")
            return ""

    # 预处理目标图像 - 获取裁剪后的数字区域
    try:
        _, target_components = image_pretreatment(
            processed_img, get_colour=get_colour, drag=drag
        )
        logger.info(f"找到 {len(target_components)} 个数字区域")
    except Exception as e:
        logger.info(f"图像预处理错误: {e}")
        return ""

    # 处理模板图像 - 支持每个数字多个模板
    templates = {}  # {数字字符: 模板图像列表}
    logger.info(f"开始加载模板...")

    for digit_char, filenames in templates_dict.items():
        logger.info(f"处理数字 '{digit_char}' 的模板")
        digit_templates = []

        for filename in filenames:
            try:
                logger.info(f"  加载模板: {filename}")

                # 加载模板图像
                template_img = get_image(filename, color_space=get_colour)
                if template_img is None:
                    logger.info(f"    警告: 模板文件 '{filename}' 未找到")
                    continue

                # 预处理模板 - 只取第一个有效的连通组件
                _, template_components = image_pretreatment(
                    template_img, get_colour=get_colour, drag=None
                )

                # 只取第一个有效组件（数字模板）
                if template_components and template_components[0].size > 0:
                    digit_templates.append(template_components[0])
                    logger.info(
                        f"    模板 '{filename}' 尺寸: {template_components[0].shape}"
                    )

                    # 调试显示
                    if drag is not None:
                        cv2.imshow(
                            f"Template: {digit_char} - {filename}",
                            template_components[0],
                        )
                        cv2.waitKey(1)  # 短暂显示
                else:
                    logger.info(f"    警告: 模板 '{filename}' 未找到有效组件")
            except Exception as e:
                logger.info(f"    处理模板 '{filename}' 时出错: {e}")

        if digit_templates:
            templates[digit_char] = digit_templates
            logger.info(
                f"  数字 '{digit_char}' 加载了 {len(digit_templates)} 个有效模板"
            )
        else:
            logger.info(f"  警告: 数字 '{digit_char}' 未找到任何有效模板")

    # 识别结果
    recognized_digits = []
    logger.info(f"开始匹配 {len(target_components)} 个数字区域...")

    # 遍历目标图像中的每个数字区域
    for i, digit_region in enumerate(target_components):
        if digit_region is None or digit_region.size == 0:
            logger.info(f"数字区域 {i} 无效 - 跳过")
            continue

        logger.info(f"处理数字区域 {i} - 尺寸: {digit_region.shape}")

        # 调试显示
        if drag is not None:
            cv2.imshow(f"Digit Region {i}", digit_region)
            cv2.waitKey(1)  # 短暂显示

        best_match = None
        best_similarity = 0

        # 与所有数字模板进行匹配
        for digit_char, digit_templates in templates.items():
            for template_idx, template_img in enumerate(digit_templates):
                # 检查模板尺寸是否适合目标区域
                if (
                    template_img.shape[0] > digit_region.shape[0]
                    or template_img.shape[1] > digit_region.shape[1]
                ):
                    # logger.info(f"  模板 '{digit_char}_{template_idx}' 太大 - 跳过")
                    continue

                try:
                    # 调整模板尺寸以匹配目标区域（如果需要）
                    if template_img.shape != digit_region.shape:
                        resized_template = cv2.resize(
                            template_img,
                            (digit_region.shape[1], digit_region.shape[0]),
                        )
                        # logger.info(f"  调整模板 '{digit_char}_{template_idx}' 尺寸")
                    else:
                        resized_template = template_img

                    # 模板匹配
                    result = cv2.matchTemplate(
                        digit_region, resized_template, cv2.TM_CCOEFF_NORMED
                    )
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                    # logger.info(f"  匹配 '{digit_char}' (模板{template_idx}): 相似度 = {max_val:.4f}")

                    # 更新最佳匹配
                    if max_val > best_similarity:
                        best_similarity = max_val
                        best_match = digit_char

                        # 调试显示匹配结果
                        if drag is not None and max_val >= sim:
                            h, w = resized_template.shape
                            top_left = max_loc
                            bottom_right = (top_left[0] + w, top_left[1] + h)

                            # 创建带匹配框的副本
                            match_vis = digit_region.copy()
                            cv2.rectangle(match_vis, top_left, bottom_right, 128, 2)
                            cv2.imshow(
                                f"Match: {digit_char} ({max_val:.2f})", match_vis
                            )
                            cv2.waitKey(1)
                except Exception as e:
                    logger.info(f"  匹配模板 '{digit_char}_{template_idx}' 时出错: {e}")

        # 保存有效匹配
        if best_match and best_similarity >= sim:
            logger.info(f"  最佳匹配: '{best_match}' (相似度 = {best_similarity:.4f})")
            recognized_digits.append(best_match)
        else:
            logger.info(f"  未找到有效匹配 (最高相似度 = {best_similarity:.4f})")

    # 返回识别结果
    result = "".join(recognized_digits)
    logger.info(f"最终识别结果: '{result}'")

    # 关闭调试窗口
    if drag is not None:
        cv2.destroyAllWindows()

    return result


def image_pretreatment(image, get_colour=None, drag=None):
    """
    优化后的图像预处理方法，专注于数字识别
    """
    # 如果是彩色图像但未指定颜色范围，转换为灰度
    if len(image.shape) == 3 and get_colour is None:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # HSV颜色处理
    if get_colour is not None:
        try:
            # 确保是HSV图像
            if len(image.shape) == 2 or image.shape[2] != 3:
                logger.info("警告: 非HSV图像，跳过颜色处理")
            else:
                hsv_lower = np.array(get_colour[0])
                hsv_upper = np.array(get_colour[1])

                # 创建掩码
                mask = cv2.inRange(image, hsv_lower, hsv_upper)

                # 应用掩码
                colored_image = cv2.bitwise_and(image, image, mask=mask)
                image = cv2.cvtColor(colored_image, cv2.COLOR_BGR2GRAY)
        except Exception as e:
            logger.info(f"HSV处理错误: {e}")

    # 二值化
    try:
        _, binary_image = cv2.threshold(
            image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
    except Exception as e:
        logger.info(f"二值化错误: {e}")
        return [], []

    # # 形态学操作 - 优化数字识别
    # try:
    #     kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    #     cleaned_image = cv2.morphologyEx(binary_image, cv2.MORPH_OPEN, kernel)
    #     cleaned_image = cv2.morphologyEx(cleaned_image, cv2.MORPH_CLOSE, kernel)
    # except Exception as e:
    #     logger.info(f"形态学操作错误: {e}")
    #     cleaned_image = binary_image

    # 调试显示
    if drag is not None:
        cv2.imshow("binary_image", binary_image)
        cv2.waitKey(0)
        # cv2.imshow('Original', image)
        # cv2.waitKey(500)
        # cv2.imshow('Binary', binary_image)
        # cv2.waitKey(500)

    # 查找连通组件
    try:
        num_components, labels, stats, centroids = cv2.connectedComponentsWithStats(
            binary_image, connectivity=8
        )
        logger.info(f"找到 {num_components - 1} 个连通组件")
    except Exception as e:
        logger.info(f"连通组件分析错误: {e}")
        return [], []

    # 存储组件信息
    components = []
    cropped_components = []

    # 遍历所有组件（跳过背景）
    for i in range(1, num_components):
        try:
            # 提取组件区域
            x, y, w, h = (
                stats[i, cv2.CC_STAT_LEFT],
                stats[i, cv2.CC_STAT_TOP],
                stats[i, cv2.CC_STAT_WIDTH],
                stats[i, cv2.CC_STAT_HEIGHT],
            )
            # 放宽尺寸限制（允许更小的组件）
            if w < 2 or h < 2:  # 仅过滤极小噪声（根据实际数字尺寸调整）
                logger.info(f"  跳过小组件: {w}x{h}")
                continue
            # # 过滤掉太小的组件（可能是噪声）
            # if w < 5 or h < 5:
            #     logger.info(f"  跳过小组件: {w}x{h} (位置: {x},{y})")
            #     continue

            logger.info(f"  组件 {i}: {w}x{h} (位置: {x},{y})")

            # 创建组件掩码
            component_mask = np.zeros_like(binary_image)
            component_mask[labels == i] = 255

            # 提取完整组件图像
            component_image = cv2.bitwise_and(
                binary_image, binary_image, mask=component_mask
            )
            components.append(component_image)

            # 裁剪组件区域
            cropped = binary_image[y : y + h, x : x + w]
            cropped_components.append(cropped)

            # 调试显示
            if drag is not None:
                cv2.imshow(f"Component {i}", cropped)
                cv2.waitKey(0)
        except Exception as e:
            logger.info(f"处理组件 {i} 时出错: {e}")

    # 按X坐标排序（从左到右）
    try:
        sorted_indices = sorted(
            range(len(components)), key=lambda i: stats[i + 1, cv2.CC_STAT_LEFT]
        )
        sorted_components = [components[i] for i in sorted_indices]
        sorted_cropped = [cropped_components[i] for i in sorted_indices]
    except Exception as e:
        logger.info(f"排序错误: {e}")
        sorted_components = components
        sorted_cropped = cropped_components

    return sorted_components, sorted_cropped
