import os
import time

import cv2
import torch

from root_dir import root_path

# from yolo.models.experimental import attempt_load
# from yolo.utils.general import check_img_size, check_suffix, non_max_suppression, scale_coords, xyxy2xywh
# from yolo.utils.plots import Annotator, colors
# from yolo.utils.torch_utils import load_classifier, select_device, time_sync
# from yolo.utils.augmentations import letterbox

# FILE = Path(__file__).resolve()
# ROOT = FILE.parents[0]  # YOLOv5 root directory
# if str(ROOT) not in sys.path:
#     sys.path.append(str(ROOT))  # add ROOT to PATH
# ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative


LOCAL_RANK = int(os.getenv('LOCAL_RANK', -1))


class YoloV8:
    def __init__(self):
        # 读取模型，这里传入训练好的模型
        self.min_map_model = None
        self.model = None
        self.x, self.y = (1280, 720)
        self.re_x, self.re_y = (1280, 720)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.min_map_conf_thres = 0.5
        self.conf_thres = 0.3
        self.iou_thres = 0.5

    def loadModel(self):
        from ultralytics import YOLO

        self.model = YOLO(r"D:\server_env\app\yolo\model_data\best.pt")
        # self.model = YOLO(os.path.join(root_path, "yolo", "model_data", "best_0605.pt"))
        self.min_map_model = YOLO(os.path.join(root_path, "yolo", "model_data", "min_map_best.pt"))

    def detect(self, game_image):
        """
        # 返回数据类型：列表（list），其中每个元素是一个包含六个元素的元组（tuple）
        # 例子：
        [
        ('dog', 50, 100, 200, 250, 0.95),  # ('类别名', x1, y1, x2, y2, 置信度)
        ('cat', 30, 80, 150, 180, 0.80),
        # 更多检测到的目标...
        ]
        :param game_image:
        :return:
        """
        # 模型预测，save=True 的时候表示直接保存yolov8的预测结果
        metrics = self.model.predict(game_image, show=True, save=False, device=self.device, iou=self.iou_thres, conf=self.conf_thres, verbose=False)
        # 如果想自定义的处理预测结果可以这么操作，遍历每个预测结果分别的去处理
        res = []
        for m in metrics:
            names = m.names
            # 获取每个boxes的结果
            box = m.boxes
            if len(box):
                for i, det in enumerate(box):
                    label = names[int(det.cls)]
                    confidence = det.conf.item()
                    # print(f"label:{label}\tdet.cls:{det.cls}")
                    x1, y1, x2, y2 = det.xyxy[0].tolist()
                    res.append((label, x1, y1, x2, y2, confidence))
        return res

    def min_map_detect(self, game_image):
        """
        # 返回数据类型：列表（list），其中每个元素是一个包含六个元素的元组（tuple）
        # 例子：
        [
        ('dog', 50, 100, 200, 250, 0.95),  # ('类别名', x1, y1, x2, y2, 置信度)
        ('cat', 30, 80, 150, 180, 0.80),
        # 更多检测到的目标...
        ]
        :param game_image:
        :return:
        """
        # 模型预测，save=True 的时候表示直接保存yolov8的预测结果
        metrics = self.min_map_model.predict(game_image, show=True, save=False, device=self.device, iou=self.iou_thres, conf=self.min_map_conf_thres, verbose=False)
        # 如果想自定义的处理预测结果可以这么操作，遍历每个预测结果分别的去处理
        res = []
        for m in metrics:
            names = m.names
            # 获取每个boxes的结果
            box = m.boxes
            if len(box):
                for i, det in enumerate(box):
                    label = names[int(det.cls)]
                    confidence = det.conf.item()
                    # print(f"label:{label}\tdet.cls:{det.cls}")
                    x1, y1, x2, y2 = det.xyxy[0].tolist()
                    res.append((label, x1, y1, x2, y2, confidence))
        return res


# class Yolo:
#     def __init__(self):
#         self.device = None
#         self.weights = str(ROOT) + '/model_data/best0831.pt'
#         self.model = None
#         self.load_model_status = False
#         self.half = False
#         self.imgsz = [640, 640]
#         self.names = None
#         self.view_img = True
#         self.stride = 32
#         self.x, self.y = (1280, 720)
#         self.re_x, self.re_y = (1280, 720)
#
#     def loadModel(self):
#         print("yolo_main loadModel")
#         self.device = select_device('0')
#         self.model = attempt_load(self.weights, map_location=self.device)
#         # Initialize
#         self.half &= self.device.type != 'cpu'  # half precision only supported on CUDA
#         # Load model
#         w = str(self.weights[0] if isinstance(self.weights, list) else self.weights)
#         classify, suffix, suffixes = False, Path(w).suffix.lower(), ['.pt', '.onnx', '.tflite', '.pb', '']
#         check_suffix(w, suffixes)  # check weights have acceptable suffix
#         pt, onnx, tflite, pb, saved_model = (suffix == x for x in suffixes)  # backend booleans
#         stride, self.names = 64, [f'class{i}' for i in range(1000)]  # assign defaults
#         stride = int(self.model.stride.max())  # model stride
#         self.names = self.model.module.names if hasattr(self.model, 'module') else self.model.names  # get class names
#         if self.half:
#             self.model.half()  # to FP16
#         if classify:  # second-stage classifier
#             modelc = load_classifier(name='resnet50', n=2)  # initialize
#             modelc.load_state_dict(torch.load('resnet50.pt', map_location=self.device)['model']).to(self.device).eval()
#         imgsz = check_img_size(self.imgsz, s=stride)  # check image size
#
#         # Dataloader
#         bs = 1  # batch_size
#         vid_path, vid_writer = [None] * bs, [None] * bs
#
#         # Run inference
#         if pt and self.device.type != 'cpu':
#             self.model(torch.zeros(1, 3, *imgsz).to(self.device).type_as(next(self.model.parameters())))  # run once
#         self.load_model_status = True
#         print("yolo_main loadModel success")
#
#     def get_load_model_status(self):
#         return self.load_model_status
#
#     def detect(self, game_image):
#         dt, seen = [0.0, 0.0, 0.0], 0
#         img = letterbox(game_image, self.imgsz, stride=self.stride, auto=True)[0]
#         img = img.transpose((2, 0, 1))[::-1]  # HWC to CHW, BGR to RGB
#         img = np.ascontiguousarray(img)
#         t1 = time_sync()
#         img = torch.from_numpy(img).to(self.device)
#         img = img.half() if self.half else img.float()  # uint8 to fp16/32
#         img = img / 255.0  # 0 - 255 to 0.0 - 1.0
#         if len(img.shape) == 3:
#             img = img[None]  # expand for batch dim
#         t2 = time_sync()
#         dt[0] += t2 - t1
#
#         # Inference
#         pred = self.model(img, augment=False, visualize=False)[0]
#         t3 = time_sync()
#         dt[1] += t3 - t2
#
#         # NMS
#         classes = None
#         pred = non_max_suppression(pred, 0.25, 0.45, classes, False, max_det=1000)
#         dt[2] += time_sync() - t3
#         boxs = []
#         res = []
#         # Process predictions
#         for i, det in enumerate(pred):  # per image
#             seen += 1
#             s, im0 = '', game_image.copy()
#             s += '%gx%g ' % img.shape[2:]  # print string
#             gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
#             annotator = Annotator(im0, line_width=1, example=str(self.names))
#             if len(det):
#                 # Rescale boxes from img_size to im0 size
#                 det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()
#
#                 # Print results
#                 for c in det[:, -1].unique():
#                     n = (det[:, -1] == c).sum()  # detections per class
#                     s += f"{n} {self.names[int(c)]}{'s' * (n > 1)}, "  # add to string
#
#                 # Write results
#                 for *xyxy, conf, cls in reversed(det):
#                     xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
#                     # print(xywh)
#
#                     if self.view_img:
#                         c = int(cls)  # integer class
#                         label = f'{self.names[c]} {conf:.2f}'
#                         annotator.box_label(xyxy, label, color=colors(c, True))
#                         line = (cls, *xywh)  # label format
#                         box = ('%g ' * len(line)).rstrip() % line
#                         box = box.split(' ')
#                         boxs.append(box)
#                 if len(boxs):
#                     for i, det in enumerate(boxs):
#                         cls, x_center, y_center, width, height = det
#                         label = self.names[int(cls)]
#                         x_center, width = self.re_x * float(x_center), self.re_x * float(width)
#                         y_center, height = self.re_y * float(y_center), self.re_y * float(height)
#                         top_left = (int(x_center - width / 2.), int(y_center - height / 2.))
#                         bottom_right = (int(x_center + width / 2.), int(y_center + height / 2.))
#                         res.append((label, top_left[0], top_left[1], bottom_right[0], bottom_right[1]))
#                         color = (0, 0, 255)  # RGB
#                         cv2.rectangle(game_image, top_left, bottom_right, color, thickness=1)
#                         txt_color = (255, 255, 255)
#                         cv2.putText(game_image, label, top_left, cv2.FONT_HERSHEY_SIMPLEX, 0.4, txt_color, thickness=1)
#             # print(f'{s}Done. ({t3 - t2:.3f}s)')
#             # cv2.namedWindow('windows', cv2.WINDOW_NORMAL)
#             # cv2.resizeWindow('windows', self.re_x, self.re_y)
#             # cv2.imshow('windows', game_image)
#             # cv2.waitKey(1)
#             # if cv2.waitKey(0) & 0xFF == ord('q'):
#             #     cv2.destroyWindow()
#
#         # Print results
#         # t = tuple(x / seen * 1E3 for x in dt)  # speeds per image
#         # print(f'Speed: %.1fms pre-process, %.1fms inference, %.1fms NMS per image at shape {(1, 3, *imgsz)}' % t)
#         return res


if __name__ == '__main__':
    from core.capture import Capture
    from mm import get_hwnd

    d_yolo = YoloV8()
    d_yolo.loadModel()
    hwnd = get_hwnd()
    # game_img = Capture(hwnd, 0, 0, 1076, 600)
    # 将BGR图像转换为RGB图像

    # game_img = cv2.imread(r"D:\automatic-painting\imgs\3548.png")
    # game_img_rgb = cv2.cvtColor(game_img, cv2.COLOR_BGR2RGB)
    # d_yolo.detect(r"D:\automatic-painting\imgs\3548.png")
    # d_yolo.detect(r"D:\automatic-painting\imgs\3815.png")
    # stat_t = time.time()
    while True:
        #
        #     if time.time() - stat_t > 5:
        #         game_img = cv2.imread(r"D:\automatic-painting\imgs\3548.png")
        #         d_yolo.detect(game_img)
        #     else:
        game_img = Capture(hwnd, 0, 0, 1076, 600)
        # 将BGR图像转换为RGB图像
        # game_img_rgb = cv2.cvtColor(game_img, cv2.COLOR_BGR2RGB)
        d_yolo.detect(game_img)
