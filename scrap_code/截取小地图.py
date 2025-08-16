import os
import cv2
import numpy as np


def is_chinese(string):
    """
    检查整个字符串是否包含中文
    :param string: 需要检查的字符串
    :return: bool
    """
    for ch in string:
        if u'\u4e00' <= ch <= u'\u9fff':
            return True
    return False


def my_imread(my_path):
    # 读取图片
    if is_chinese(my_path):
        img = cv2.imdecode(np.fromfile(my_path, dtype=np.uint8), -1)  # 避免路径有中文
    else:
        img = cv2.imread(my_path)
    return img


def crop_images(input_folder, output_folder, crop_area):
    """
    遍历指定文件夹中的所有图片，执行截图操作，并将截取的图片保存到另一个文件夹中。

    :param input_folder: 输入文件夹路径，包含待处理的图片。
    :param output_folder: 输出文件夹路径，用于保存截取的图片。
    :param crop_area: 一个四元组，指定截图区域的坐标 (y_start, x_start, y_end, x_end)。
    """
    # 确保输出文件夹存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 遍历输入文件夹中的所有文件
    for filename in os.listdir(input_folder):
        # 构建完整的文件路径
        file_path = os.path.join(input_folder, filename)

        # 检查文件是否为图片（这里简单以文件扩展名来判断，可以根据需要扩展）
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            # 读取图片
            image = my_imread(file_path)

            # 检查图片是否成功加载
            if image is not None:
                # 执行截图操作
                cropped_image = image[crop_area[0]:crop_area[2], crop_area[1]:crop_area[3]]

                # 构建输出文件的完整路径
                output_path = os.path.join(output_folder, filename)

                # 保存截取的图片
                cv2.imwrite(output_path, cropped_image)
                print(f"Saved cropped image: {output_path}")
            else:
                print(f"Failed to load image: {file_path}")


# 使用示例
# input_folder = r'D:\dnf-ai-master-fengbao_29_1\imgs'
# output_folder = r'D:\dnf-ai-master-fengbao_29_1\min_map'
# # crop_area = (48, 1280 - 6 - 126, 48 + 54, 1280 - 6)  # 注意：这里的坐标顺序是 (y_start, x_start, y_end, x_end)
# crop_area = (52, 1280 - 12 - 126, 52 + 54, 1280 - 12)  # 注意：这里的坐标顺序是 (y_start, x_start, y_end, x_end)
# crop_images(input_folder, output_folder, crop_area)
a = my_imread(r"C:\Users\Administrator\Desktop\ultralytics-8.1.0\datasets_dnf\images\train\6311.png")
cv2.imshow('1', a)
cv2.waitKey(0)
cv2.destroyAllWindows()
