import cv2
import numpy as np
import time


def find_colored_components(image_path, hsv_lower, hsv_upper,
                            min_width, max_width, min_height, max_height,
                            min_area=0, morph_kernel_size=3):
    """
    优化版：使用自定义HSV范围查找连通组件

    参数:
    image_path: 图像路径或numpy数组
    hsv_lower: HSV下界 [H_min, S_min, V_min]
    hsv_upper: HSV上界 [H_max, S_max, V_max]
    min_width, max_width: 宽度范围
    min_height, max_height: 高度范围
    min_area: 最小面积
    morph_kernel_size: 形态学操作核大小

    返回:
    valid_components: 符合条件组件的外接矩形列表
    mask: 生成的二值掩码
    processing_time: 处理时间(毫秒)
    """
    start_time = time.time()

    # 读取图像
    if isinstance(image_path, str):
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")
    else:
        image = image_path

    # 转换为HSV
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 创建HSV掩码
    if hsv_lower[0] <= 1 and hsv_upper[0] >= 178:
        # 处理红色范围 (0°和180°)
        mask1 = cv2.inRange(hsv_image, np.array([0, hsv_lower[1], hsv_lower[2]]),
                            np.array([hsv_upper[0], hsv_upper[1], hsv_upper[2]]))
        mask2 = cv2.inRange(hsv_image, np.array([180 - hsv_upper[0], hsv_lower[1], hsv_lower[2]]),
                            np.array([179, hsv_upper[1], hsv_upper[2]]))
        mask = cv2.bitwise_or(mask1, mask2)
    else:
        # 普通范围
        mask = cv2.inRange(hsv_image, np.array(hsv_lower), np.array(hsv_upper))

    # 形态学操作 - 使用更高效的方式
    kernel = np.ones((morph_kernel_size, morph_kernel_size), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # 查找连通组件 (使用更高效的方式)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)

    # 预计算条件边界
    width_ok = (min_width <= stats[1:, cv2.CC_STAT_WIDTH]) & (stats[1:, cv2.CC_STAT_WIDTH] <= max_width)
    height_ok = (min_height <= stats[1:, cv2.CC_STAT_HEIGHT]) & (stats[1:, cv2.CC_STAT_HEIGHT] <= max_height)
    area_ok = stats[1:, cv2.CC_STAT_AREA] >= min_area

    # 组合所有条件
    valid_indices = np.where(width_ok & height_ok & area_ok)[0] + 1

    # 提取有效组件
    valid_components = []
    for i in valid_indices:
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]
        valid_components.append((x, y, w, h))

    processing_time = (time.time() - start_time) * 1000  # 转换为毫秒

    return valid_components, mask, processing_time


# 使用示例
if __name__ == "__main__":
    # 自定义HSV范围
    hsv_lower = [0, 240, 150]  # H:0, S:250, V:150
    hsv_upper = [1, 255, 255]  # H:1, S:255, V:217

    # 尺寸筛选条件
    min_width, max_width = 10, 200
    min_height, max_height = 3, 6
    min_area = 10
    image_path = r'D:\automatic-painting\imgs\777.png'

    # 查找组件并计时
    start_total = time.time()
    components, mask, proc_time = find_colored_components(
        image_path,
        hsv_lower, hsv_upper,
        min_width, max_width, min_height, max_height,
        min_area=min_area
    )
    total_time = (time.time() - start_total) * 1000

    # 可视化结果
    image = cv2.imread(image_path)
    output = image.copy()

    for (x, y, w, h) in components:
        cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 2)
        print(f"位置: ({x}, {y}), 尺寸: {w}x{h}")

    # 显示处理时间
    time_text = f"处理时间: {proc_time:.2f}ms (总时间: {total_time:.2f}ms)"
    cv2.putText(output, time_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    # 显示结果
    cv2.imshow("Original", image)
    cv2.imshow("Color Mask", mask)
    cv2.imshow("Detected Components", output)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print(f"找到 {len(components)} 个符合条件的组件")
    print(time_text)
