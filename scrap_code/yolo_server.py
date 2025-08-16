from flask import Flask, request, jsonify
import cv2
import base64
import numpy as np

app = Flask(__name__)


@app.route('/upload_base64_image', methods=['POST'])
def upload_base64_image():
    # 从请求体中获取Base64编码的图片字符串
    base64_img_str = request.json.get('image')

    if base64_img_str is None:
        return jsonify({'error': 'No image data provided'}), 400

        # 移除Base64编码字符串中的头信息（如果有的话），通常是'data:image/jpeg;base64,'
    # 注意：这里假设头信息是'data:image/jpeg;base64,'，但你应该根据实际需要调整
    imgdata = base64.b64decode(base64_img_str.split(',')[1])

    # 使用numpy将解码后的字节流转换为uint8类型的数组
    nparr = np.frombuffer(imgdata, np.uint8)

    # 使用OpenCV的imdecode函数将numpy数组解码为图像
    # 注意：cv2.IMREAD_COLOR表示以彩色模式读取图像
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is not None:
        # 在这里，我们只是返回图像的尺寸作为示例
        # 你可以根据需要添加更多的图像处理逻辑
        return jsonify({'width': img.shape[1], 'height': img.shape[0]}), 200
    else:
        return jsonify({'error': 'Failed to decode image from Base64 string'}), 400


if __name__ == '__main__':
    app.run(debug=True)