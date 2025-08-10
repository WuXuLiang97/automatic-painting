#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

import cv2
import numpy as np

current_path = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
root_path = os.path.abspath(os.path.join(current_path, '../'))


class SiftUtil:
    def __init__(self):
        self.sift = cv2.SIFT_create()
        # 创建FLANN匹配器
        self.matcher = cv2.FlannBasedMatcher()
        self.max_map_img = None
        self.min_map_img = None

    def set_max_img(self, max_img):
        self.max_map_img = max_img

    def set_min_img(self, img):
        self.min_map_img = img

    def get_sift_loc(self, max_img, min_img):
        self.set_max_img(max_img)
        self.set_min_img(min_img)
        # 在图像中检测特征点和计算描述符
        key_points1, descriptors1 = self.sift.detectAndCompute(self.max_map_img, None)
        key_points2, descriptors2 = self.sift.detectAndCompute(self.min_map_img, None)

        # 使用 KNN 匹配得到最佳匹配结果
        k = 2  # 取前两个最佳匹配
        matches = self.matcher.knnMatch(descriptors1, descriptors2, k)

        # 进行匹配结果筛选
        good_matches = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

        # 提取匹配点对的位置
        points1 = np.float32([key_points1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        points2 = np.float32([key_points2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # 计算图2在图1中的变换矩阵
        M, mask = cv2.findHomography(points2, points1, cv2.RANSAC, 5.0)

        # 返回X,Y坐标
        return M[0, 2], M[1, 2]


sift_util = SiftUtil()

