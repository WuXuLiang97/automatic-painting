import os
import cv2
import numpy as np
import onnxruntime as ort
from typing import List, Tuple
from root_dir import root_path

# 模型与字典路径
DET_MODEL_DIR = os.path.join(root_path, "PP-OCRv5_mobile_det")
REC_MODEL_DIR = os.path.join(root_path, "PP-OCRv5_mobile_rec")
DET_ONNX_PATH = os.path.join(DET_MODEL_DIR, "det.onnx")
REC_ONNX_PATH = os.path.join(REC_MODEL_DIR, "rec.onnx")
REC_KEYS_PATH = os.path.join(REC_MODEL_DIR, "keys.txt")

# 超参（可按需调整）
DET_BIN_THRESH = 0.2
DET_BOX_THRESH = 0.50
DET_UNCLIP_RATIO = 1.60   # 简化外扩（几何放缩）
PADDLE_SCORE_THRESH = 0.85  # Paddle 风格评分阈值，低于此值的文本可忽略
MAX_REC_WIDTH = 320        # 保护性限制，防极宽文本占用内存
# 新增：检测阶段希望的最小放大后最大边（小于此值的图片先放大，避免过小导致丢字）
MIN_DET_SIDE = 256  # 可根据实际再调，如 192/224/256

class OCRHandler:
    """ONNXRuntime OCR: DB 检测 + CTC 识别 (仅依赖 det.onnx / rec.onnx / keys.txt)
    process(image: np.ndarray) -> List[{text, box(4点), score}]
    """

    def __init__(self, det_dir: str = DET_MODEL_DIR, rec_dir: str = REC_MODEL_DIR, debug: bool = False, print_result: bool = False):
        self.debug = debug
        self.print_result = print_result  # 新增：控制是否打印最终结果
        providers = ["CPUExecutionProvider"]
        if not os.path.isfile(DET_ONNX_PATH):
            raise FileNotFoundError(f"缺少检测模型: {DET_ONNX_PATH}")
        if not os.path.isfile(REC_ONNX_PATH):
            raise FileNotFoundError(f"缺少识别模型: {REC_ONNX_PATH}")
        if not os.path.isfile(REC_KEYS_PATH):
            raise FileNotFoundError(f"缺少字典文件: {REC_KEYS_PATH}")
        self.det_session = ort.InferenceSession(DET_ONNX_PATH, providers=providers)
        self.rec_session = ort.InferenceSession(REC_ONNX_PATH, providers=providers)
        self.charset = self._load_keys(REC_KEYS_PATH)
        self.blank_idx = 0  # CTC blank
        # 识别模型期望高度（NCHW 中 H）
        rec_in_meta = self.rec_session.get_inputs()[0]
        shape = rec_in_meta.shape  # 形如 ['DynamicDimension.0', 3, 48, 'DynamicDimension.1']
        self.rec_img_h = 48
        if len(shape) == 4 and isinstance(shape[2], int) and shape[2] > 0:
            self.rec_img_h = shape[2]
        if self.debug:
            print(f"[OCR] rec input height={self.rec_img_h} shape={shape}")

    # ------------ 工具 ------------
    def _load_keys(self, path: str) -> List[str]:
        with open(path, 'r', encoding='utf-8') as f:
            return [l.rstrip('\r\n') for l in f]

    # ------------ 检测预处理 ------------
    def _resize_det(self, img: np.ndarray, limit_side_len=960, min_side_len: int = MIN_DET_SIDE) -> Tuple[np.ndarray, float, float]:
        """检测前尺寸调整：
        - 若最大边 < min_side_len:  等比例放大到 min_side_len（再对齐 32）
        - 若最大边 > limit_side_len: 等比例缩小到 limit_side_len（再对齐 32）
        - 否则保持原尺寸（再对齐 32，最少 32）
        返回: resized, ratio_h, ratio_w （用于还原坐标）
        """
        h, w = img.shape[:2]
        max_side = max(h, w)
        # 计算缩放比例
        if max_side < min_side_len:
            ratio = min_side_len / max_side
        elif max_side > limit_side_len:
            ratio = limit_side_len / max_side
        else:
            ratio = 1.0
        new_w = int(w * ratio + 0.5)
        new_h = int(h * ratio + 0.5)
        # 对齐到 32 倍数（DB 模型通常下采样 32）
        new_w = max(32, (new_w + 31) // 32 * 32)
        new_h = max(32, (new_h + 31) // 32 * 32)
        if new_w == w and new_h == h:
            resized = img
        else:
            resized = cv2.resize(img, (new_w, new_h))
            
        return resized, new_h / h, new_w / w

    def _preprocess_det(self, img: np.ndarray):
        resized, rh, rw = self._resize_det(img)
        x = resized.astype('float32') / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        x = (x - mean) / std
        x = x.transpose(2, 0, 1)[None, ...]
        # 原先误写入 4D 张量，这里不再保存 det_input.png；若仍需可反归一化再写
        return x, {'ratio_h': rh, 'ratio_w': rw}

    # ------------ 检测后处理 ------------
    def _postprocess_det(self, prob_map: np.ndarray, meta: dict) -> List[np.ndarray]:
        bin_map = (prob_map > DET_BIN_THRESH).astype(np.uint8) * 255
        
        contours, _ = cv2.findContours(bin_map, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        h, w = prob_map.shape
        boxes = []
        for cnt in contours:
            if cnt.shape[0] < 4:
                continue
            rect = cv2.minAreaRect(cnt)
            pts = cv2.boxPoints(rect)
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(mask, [pts.astype(int)], 1)
            score = cv2.mean(prob_map, mask)[0]
            if score < DET_BOX_THRESH:
                continue
            expanded = self._expand_polygon(pts, DET_UNCLIP_RATIO)
            expanded[:, 0] /= meta['ratio_w']
            expanded[:, 1] /= meta['ratio_h']
            ordered = self._order_points_clockwise(expanded)
            boxes.append(ordered.astype(np.int32))
        if self.debug:
            print(f"[DET] contours={len(contours)} keep={len(boxes)}")
        return boxes

    def _expand_polygon(self, pts: np.ndarray, ratio: float) -> np.ndarray:
        cx, cy = pts[:, 0].mean(), pts[:, 1].mean()
        return (pts - [cx, cy]) * ratio + [cx, cy]

    def _order_points_clockwise(self, pts: np.ndarray) -> np.ndarray:
        pts = pts[np.argsort(pts[:, 1])]
        top = pts[:2][np.argsort(pts[:2, 0])]
        bottom = pts[2:][np.argsort(pts[2:, 0])[::-1]]
        return np.vstack([top, bottom])

    # ------------ 识别预处理 ------------
    def _crop_and_normalize_rec(self, img: np.ndarray, box: np.ndarray, target_w: int = None) -> np.ndarray:
        p = box.astype(np.float32)
        w1 = np.linalg.norm(p[0]-p[1]); w2 = np.linalg.norm(p[2]-p[3])
        h1 = np.linalg.norm(p[0]-p[3]); h2 = np.linalg.norm(p[1]-p[2])
        w = max(1, int(max(w1, w2))); h = max(1, int(max(h1, h2)))
        dst = np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]], dtype=np.float32)
        M = cv2.getPerspectiveTransform(p, dst)
        crop = cv2.warpPerspective(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        scale = self.rec_img_h / crop.shape[0]
        new_w = max(1, int(crop.shape[1] * scale))
        if target_w is not None:
            new_w = min(new_w, target_w)
        if new_w > MAX_REC_WIDTH:
            new_w = MAX_REC_WIDTH
        resized = cv2.resize(crop, (new_w, self.rec_img_h))
        x = resized.astype('float32') / 255.0
        x = (x - 0.5) / 0.5
        x = x.transpose(2, 0, 1)  # [3,H,W]
        if target_w is not None and new_w < target_w:
            pad = np.zeros((3, self.rec_img_h, target_w - new_w), dtype=np.float32)
            x = np.concatenate([x, pad], axis=2)
        return x[None, ...]

    # ------------ CTC 解码 ------------
    def _ctc_decode(self, logits: np.ndarray):
        """返回 (text, paddle_score, char_probs)
        自适应输出形状：
        - 典型 PP-OCR ONNX: [B, T, C]
        - 有些导出: [B, C, T]
        Paddle 评分: 取去重/去 blank 后字符概率平均值。
        若模型输出已是概率分布（每步求和≈1），则直接用；否则 softmax。
        """
        if logits.ndim != 3:
            return "", 0.0, []
        B, A, B2 = logits.shape
        # 判定哪个维是类别数 (= len(charset)+1)
        num_classes = len(self.charset) + 1  # + blank
        if A == num_classes:
            # [B, C, T]
            seq = logits[0].transpose(1, 0)  # -> [T, C]
        elif B2 == num_classes:
            # [B, T, C]
            seq = logits[0]  # [T, C]
        else:
            # 回退到假设第二维是时间步
            if logits.shape[1] < logits.shape[2]:
                seq = logits[0]
            else:
                seq = logits[0].transpose(1, 0)
        # 检测是否已 softmax：随机抽 5 行检查行和是否接近 1
        sample_rows = seq[:min(5, seq.shape[0])]
        row_sums = sample_rows.sum(axis=1)
        if np.allclose(row_sums, 1.0, atol=1e-3):
            probs = seq  # 已是概率
        else:
            # 数值稳定 softmax
            m = seq.max(axis=1, keepdims=True)
            e = np.exp(seq - m)
            probs = e / e.sum(axis=1, keepdims=True)
        idxs = probs.argmax(axis=1)
        prev = -1
        chars, confs = [], []
        for i, ix in enumerate(idxs):
            if ix == self.blank_idx or ix == prev:  # blank 或重复
                prev = ix
                continue
            if ix > 0 and (ix - 1) < len(self.charset):
                chars.append(self.charset[ix - 1])
                confs.append(float(probs[i, ix]))
            prev = ix
        if not chars:
            return "", 0.0, []
        paddle_score = float(np.mean(confs))  # Paddle 风格：平均概率
        return ''.join(chars), paddle_score, confs

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        m = x.max(axis=1, keepdims=True)
        e = np.exp(x - m)
        return e / e.sum(axis=1, keepdims=True)

    # ------------ 主流程 ------------
    def process(self, image: np.ndarray):
        if image is None or image.size == 0:
            return []
        det_input, meta = self._preprocess_det(image)
        det_out = self.det_session.run(None, {self.det_session.get_inputs()[0].name: det_input})
        prob = det_out[0]
        if prob.ndim == 4:
            if prob.shape[1] == 1:
                prob_map = prob[0, 0]
            elif prob.shape[-1] == 1:
                prob_map = prob[0, ..., 0]
            else:
                prob_map = prob[0, 0]
        else:
            prob_map = prob

        boxes = self._postprocess_det(prob_map, meta)

        rec_in = self.rec_session.get_inputs()[0]
        shape = rec_in.shape
        fixed_w = None
        if len(shape) == 4 and isinstance(shape[3], int) and shape[3] > 0:
            fixed_w = shape[3]
        if self.debug:
            print(f"[REC] input={rec_in.name} shape={shape} fixed_w={fixed_w}")

        results = []
        for i, box in enumerate(boxes):
            try:
                rec_input = self._crop_and_normalize_rec(image, box, target_w=fixed_w)
                if self.debug:
                    print(f"[REC] box#{i} shape={rec_input.shape}")
                logits = self.rec_session.run(None, {rec_in.name: rec_input})[0]
                text, paddle_score, char_confs = self._ctc_decode(logits)
                if self.debug:
                    print(f"[REC] box#{i} text='{text}' paddle_score={paddle_score:.4f}")
                if text:
                    results.append({
                        'text': text,
                        'box': box.tolist(),
                        'paddle_score': round(paddle_score, 4),  # 严格对齐 Paddle
                        'score': round(paddle_score, 4),          # 兼容旧字段
                        'char_probs': [round(c, 4) for c in char_confs]
                    })
            except Exception as e:
                if self.debug:
                    print(f"[REC][ERR] box#{i}: {e}")
                continue
        # if self.print_result and results:
        #     print("[OCR][RESULT] 共识别{}条:".format(len(results)))
        #     for idx, r in enumerate(results):
        #         print(f"  {idx+1}. text='{r['text']}' paddle_score={r['paddle_score']}" )
        # return results
        rec_texts = ''.join([r['text'] for r in results if r['paddle_score'] >= PADDLE_SCORE_THRESH])
        return rec_texts
