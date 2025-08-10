import cv2
import numpy as np


def nothing(x):
    pass


# 创建一个窗口和滑动条
cv2.namedWindow('HSV Color Filter')
cv2.resizeWindow('HSV Color Filter', 800, 600)

# 创建HSV阈值滑动条
cv2.createTrackbar('HMin', 'HSV Color Filter', 0, 179, nothing)
cv2.createTrackbar('SMin', 'HSV Color Filter', 0, 255, nothing)
cv2.createTrackbar('VMin', 'HSV Color Filter', 0, 255, nothing)
cv2.createTrackbar('HMax', 'HSV Color Filter', 179, 179, nothing)
cv2.createTrackbar('SMax', 'HSV Color Filter', 255, 255, nothing)
cv2.createTrackbar('VMax', 'HSV Color Filter', 255, 255, nothing)

# 设置初始阈值（这里设置为蓝色范围）
cv2.setTrackbarPos('HMin', 'HSV Color Filter', 90)
cv2.setTrackbarPos('SMin', 'HSV Color Filter', 100)
cv2.setTrackbarPos('VMin', 'HSV Color Filter', 100)
cv2.setTrackbarPos('HMax', 'HSV Color Filter', 130)
cv2.setTrackbarPos('SMax', 'HSV Color Filter', 255)
cv2.setTrackbarPos('VMax', 'HSV Color Filter', 255)

# 打开摄像头或加载图像
# cap = cv2.VideoCapture(0)  # 打开摄像头
# 或者加载本地图像
image = cv2.imread(r'D:\automatic-painting\map_depot\9.png')  # 替换为你的图像路径
if image is None:
    print("无法加载图像，请检查路径")
    exit()

while True:
    # 读取一帧图像
    # ret, frame = cap.read()
    # if not ret:
    #     break

    # 使用加载的图像
    frame = image.copy()

    # 获取当前滑动条位置
    h_min = cv2.getTrackbarPos('HMin', 'HSV Color Filter')
    s_min = cv2.getTrackbarPos('SMin', 'HSV Color Filter')
    v_min = cv2.getTrackbarPos('VMin', 'HSV Color Filter')
    h_max = cv2.getTrackbarPos('HMax', 'HSV Color Filter')
    s_max = cv2.getTrackbarPos('SMax', 'HSV Color Filter')
    v_max = cv2.getTrackbarPos('VMax', 'HSV Color Filter')

    # 创建HSV范围数组
    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, s_max, v_max])

    # 将图像转换为HSV颜色空间
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # 创建掩码
    mask = cv2.inRange(hsv, lower, upper)

    # 将不在范围内的区域设为黑色
    result = cv2.bitwise_and(frame, frame, mask=mask)

    # 显示原始图像、掩码和结果
    cv2.imshow('Original', frame)
    cv2.imshow('Mask', mask)
    cv2.imshow('Result', result)

    # 按ESC键退出
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC键
        break

# 释放资源
# cap.release()
cv2.destroyAllWindows()
