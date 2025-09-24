import os
import json
import cv2
import sys
# 允许从项目根导入 root_dir 等
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
from root_dir import root_path  # noqa: E402
from server.ocr_handler import OCRHandler  # noqa: E402

def main():
    img_path = os.path.join(root_path, 'revice.png')
    if not os.path.exists(img_path):
        print(f'图片不存在: {img_path}')
        return
    ocr = OCRHandler()
    img = cv2.imread(img_path)
    if img is None:
        print('读取图片失败')
        return
    results = ocr.process(img)
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
