import json
import queue
import socket
import struct
import threading
import traceback
import cv2
import win32gui

from core.capture import Capture

# 创建 Event 对象
STOP_EVENT = threading.Event()
# 创建一个队列用于存储图片数据
image_queue = queue.Queue()


def get_hwnd():
    dnf_hwnd = win32gui.FindWindow('地下城与勇士', '地下城与勇士：创新世纪')
    if dnf_hwnd != 0:
        print("地下城与勇士：创新世纪窗口的句柄:", dnf_hwnd)
    return dnf_hwnd


# 显示图像的线程函数
def show_images_thread():
    # 创建一个名为'Image Display'的窗口（但注意函数中的窗口名实际上是'img'）
    cv2.namedWindow(f"Client", cv2.WINDOW_AUTOSIZE)

    # 尝试设置窗口的位置（x, y），但注意cv2.setWindowProperty对于全屏属性的设置可能不是这里想要的
    # 如果你想要设置窗口为非全屏且移动位置，应该确保不设置全屏属性，或者正确设置它之后再移动窗口
    # 这里我们简单地移动窗口到一个指定位置
    cv2.moveWindow(f"Client", 1280, 0)  # 将窗口移动到屏幕上的(850, 0)位置

    while not STOP_EVENT.is_set():  # 如果键盘按下F12会退出脚本
        # 从队列中获取图片数据，如果队列为空则阻塞
        frame = image_queue.get()

        # 如果接收到特定的结束信号（例如None），则退出循环
        if frame is None:
            break

        # 显示图片
        cv2.imshow(f"Client", frame)

        # 等待按键，如果是'q'则退出循环（但注意这里的'q'检查可能不是必需的，因为我们已经有了结束信号）
        # 然而，保留这个检查可以让用户通过按键来提前退出显示
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 销毁窗口（虽然在这个例子中，当线程结束时窗口通常会自动关闭）
    cv2.destroyWindow(f"Client")


hwnd = get_hwnd()

server_ip = '192.168.248.1'
server_port = 12345
server_address = (server_ip, server_port)
# 启动显示图像的线程
display_thread = threading.Thread(target=show_images_thread, daemon=True)
display_thread.start()
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(server_address)
    print(s)

    while True:
        try:
            game_image = Capture(hwnd, 0, 0, 1067, 600)  # 确保Capture函数和hwnd都已正确定义和初始化
            img_bytes = cv2.imencode('.jpg', game_image)[1].tobytes()
            image_size = len(img_bytes)
            message_type_image = 1
            message_header = struct.pack('!BI', message_type_image, image_size)
            s.sendall(message_header)
            s.sendall(img_bytes)
            image_queue.put(game_image)
            """从服务器接收消息，并解码为适当的数据结构"""
            try:
                # 接收消息头（消息类型和消息长度）
                header_data = s.recv(5)  # 1字节类型 + 4字节长度
                if not header_data:
                    raise ConnectionError(f"接收的消息头连接中断")
            except socket.error as e:
                print(f"接收的消息头：{e}")
                # 打印完整的堆栈跟踪信息
                traceback.print_exc()
                s.close()
                break

            message_type, message_length = struct.unpack('!BI', header_data)
            print(f"receive_message_from_server: 消息类型={message_type}, 消息长度={message_length}")

            # 接收消息内容
            message_content = b''
            # 循环直到接收到的数据长度达到预期的message_length
            while len(message_content) < message_length:
                # 从连接中接收最多4096字节的数据
                # 注意：这里的4096是一个常见的缓冲区大小，但可以根据需要进行调整
                try:
                    packet = s.recv(4096)
                    # 检查是否成功接收到数据
                    if not packet:
                        # 如果没有接收到任何数据（即packet为空），则可能连接已经关闭或出现了错误
                        raise ConnectionError("接收数据时连接中断")
                except socket.error as e:
                    print(f"接收的消息头：{e}")
                    # 打印完整的堆栈跟踪信息
                    traceback.print_exc()
                    s.close()
                    s = None
                    break

                # 将接收到的数据包添加到message_content中
                message_content += packet

            # 根据消息类型处理消息内容
            if message_type == 2:  # 假设1表示图像识别结果的JSON列表
                response_data = json.loads(message_content.decode('utf-8'))
                print(response_data)
        except Exception as e:
            print("Error during loop:", e)
            traceback.print_exc()
            break  # 或者根据需要采取其他错误处理措施

finally:
    s.close()  # 确保socket被关闭
    cv2.destroyAllWindows()  # 关闭所有OpenCV窗口
