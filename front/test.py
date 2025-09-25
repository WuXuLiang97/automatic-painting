import cv2
import time

def test_capture_card():
    # 1. 遍历可能的索引，找有效设备
    valid_idx = None
    for idx in range(6):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)  # 强制 DirectShow 后端
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None and frame.any():
                valid_idx = idx
                print(f"找到有效索引：{idx}，默认分辨率：{frame.shape}")
            cap.release()
            if valid_idx is not None:
                break
    if valid_idx is None:
        print("未找到有效采集卡设备，请检查硬件连接")
        return

    # 2. 用有效索引打开采集卡
    cap = cv2.VideoCapture(valid_idx, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("无法打开采集卡")
        return

    # 3. 用默认分辨率（先不强制设置，避免不兼容）
    print(f"当前分辨率：{cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")

    # 4. 读取并显示画面（运行 10 秒）
    st = time.time()
    while time.time() - st < 10:
        ret, frame = cap.read()
        if ret and frame is not None and frame.any():
            cv2.imshow("Capture Card Preview", frame)
            # 关键：waitKey 不能为 0（会卡住），设为 1 保证实时显示
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("未读到画面（可能信号中断）")
            time.sleep(0.5)

    # 5. 释放资源
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_capture_card()