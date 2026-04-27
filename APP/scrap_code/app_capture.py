import datetime
import os
import sys
from time import sleep

import cv2
import win32gui
from PyQt5.QtCore import QThread, pyqtSignal, QByteArray, QPoint, QSize
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QApplication, QMainWindow

from core.capture import Capture
from view.jietu import Ui_Form

# 注意：通常窗口标题是可变的，而类名可能更稳定，但这里你给出了相反的情况
hwnd = win32gui.FindWindow('地下城与勇士', '地下城与勇士：创新世纪')
if hwnd != 0:
    print("地下城与勇士：创新世纪窗口的句柄:", hwnd)
else:
    print("地下城与勇士：创新世纪窗口")

folder_path = r'imgs'
capture_ui_config__path = r"cjson_resources/apture_ui_config.json"
jieutui_config__path = r"json_resources/jieutui_config.json"
# 检查文件夹是否存在
if not os.path.exists(folder_path):
    # 文件夹不存在，创建文件夹
    os.makedirs(folder_path)
    print(f"文件夹 {folder_path} 已创建。")
else:
    # 文件夹已存在
    print(f"文件夹 {folder_path} 已存在。")
# 路径和编号记录文件
counter_file = os.path.join(folder_path, "last_counter.txt")

# 读取上一次的编号，如果不存在则设置为1
if os.path.exists(counter_file):
    with open(counter_file, 'r') as f:
        count = int(f.read().strip())
else:
    count = 0

import os
import json


def create_config_file(filename, default_settings):
    """
    检查指定的配置文件是否存在，如果不存在则创建该文件，并写入默认设置。

    参数:
    filename (str): 配置文件的名称。
    default_settings (dict): 默认的配置设置。
    """
    if not os.path.exists(filename):
        with open(filename, 'w') as file:
            json.dump(default_settings, file, indent=4)
        print(f"{filename} 文件已创建。")
    else:
        print(f"{filename} 文件已存在。")


def init_ui_ip():
    # 创建 jieutui_config.json 文件
    create_config_file(jieutui_config__path, {
        "x": 0,
        "y": 0,
        "x1": 1067,
        "y1": 600,
        "interval": 100
    })


# 调用函数初始化配置
init_ui_ip()


class CAPTURE(QThread):
    message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.x = None
        self.y = None
        self.x1 = None
        self.y1 = None
        self.interval = 0
        self.running = True

    def run(self):
        global count
        try:
            # 循环截图
            while self.running:
                count += 1
                filename = os.path.join(folder_path, f"{count}.png")
                # 假设 capture.Capture 是正确的方法来获取截图
                # 这里用 None 代替，你需要替换为实际的截图代码
                print((self.x, self.y, self.x1, self.y1))
                pic = Capture(hwnd, self.x, self.y, self.x1, self.y1)
                # pic = pic[48:48 + 54, 1280 - 6 - 126:1280 - 6]
                # 假设 pic 已经是 cv2 的图像格式
                # pic = cv2.imread('some_image.png')  # 临时用图片替换截图
                cv2.imwrite(filename, pic)  # 假设 pic 已经是有效的图像数据
                self.send_log(filename)
                # 更新编号文件
                with open(counter_file, 'w') as f:
                    f.write(str(count))
                sleep(self.interval * 0.001)
        except BaseException as e:
            print(f'Error:{e}')

    def stop(self):
        self.running = False

    def send_log(self, log):
        self.message.emit(log)


class MYAPP(Ui_Form, QMainWindow):  # 假设 Ui_Form 是一个 QWidget 子类，这里我们额外继承 QMainWindow
    def __init__(self):
        super(MYAPP, self).__init__()  # 注意这里需要调用 Ui_Form 和 QMainWindow 的构造函数
        self.setupUi(self)  # 假设 setupUi 是 Ui_Form 中定义的方法
        self.loadSettings(capture_ui_config__path)

        # 绑定文本改变事件（文本内容发生变化时触发）
        self.textEdit.textChanged.connect(self.on_text_changed)
        self.textEdit_2.textChanged.connect(self.on_text_changed)
        self.textEdit_4.textChanged.connect(self.on_text_changed)
        self.textEdit_5.textChanged.connect(self.on_text_changed)
        self.textEdit_6.textChanged.connect(self.on_text_changed)
        self.pushButton.clicked.connect(self.on_button_clicked)
        self.pushButton_2.clicked.connect(self.on_button_clicked)
        self.capture = CAPTURE()
        self.capture.message.connect(self.update_log)  # 连接消息信号到更新日志的方法
        self.load_configuration()

    def on_text_changed(self):
        sender_obj = self.sender()

        # 加载设置（考虑将这一步移动到其他地方，例如程序启动时或设置保存按钮的点击事件中）
        with open(jieutui_config__path, 'r') as file:
            settings = json.load(file)

        try:
            if sender_obj == self.textEdit:
                self.capture.x = int(self.textEdit.toPlainText())
                settings["x"] = self.capture.x
            elif sender_obj == self.textEdit_2:
                self.capture.interval = int(self.textEdit_2.toPlainText())
                settings["interval"] = self.capture.interval
            elif sender_obj == self.textEdit_4:
                self.capture.y = int(self.textEdit_4.toPlainText())
                settings["y"] = self.capture.y
            elif sender_obj == self.textEdit_5:
                self.capture.x1 = int(self.textEdit_5.toPlainText())
                settings["x1"] = self.capture.x1
            elif sender_obj == self.textEdit_6:
                self.capture.y1 = int(self.textEdit_6.toPlainText())
                settings["y1"] = self.capture.y1

            # 保存设置（考虑将这一步移动到其他地方）
            with open(jieutui_config__path, 'w') as file:
                json.dump(settings, file, indent=4)

        except ValueError:
            print("Invalid input. Please enter a valid integer.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def load_configuration(self):
        with open(jieutui_config__path, 'r') as file:
            settings = json.load(file)
            # 更新文本编辑控件
        self.textEdit.setText(str(settings.get("x", 0)))
        self.textEdit_2.setText(str(settings.get("interval", 100)))
        self.textEdit_4.setText(str(settings.get("y", 0)))
        self.textEdit_5.setText(str(settings.get("x1", 100)))
        self.textEdit_6.setText(str(settings.get("y1", 100)))

        self.capture.x = int(self.textEdit.toPlainText())
        self.capture.y = int(self.textEdit_4.toPlainText())
        self.capture.x1 = int(self.textEdit_5.toPlainText())
        self.capture.y1 = int(self.textEdit_6.toPlainText())
        self.capture.interval = int(self.textEdit_2.toPlainText())

    def on_button_clicked(self):
        sender_obj = self.sender()  # 使用 self.sender() 获取发送者
        if sender_obj == self.pushButton:
            self.capture.start()
            self.pushButton.setEnabled(False)
        elif sender_obj == self.pushButton_2:
            self.capture.stop()
            self.pushButton.setEnabled(True)

    def update_log(self, log):
        # 获取当前时间并格式化
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%H:%M:%S")

        # 构造新的日志消息，包括时间戳和日志内容
        new_log_line = f"{formatted_time} - {log}\n"

        # 获取当前日志框的内容
        current_text = self.textEdit_3.toPlainText()

        # 将新的日志消息追加到当前内容
        new_text = current_text + new_log_line

        # 更新日志框的内容
        self.textEdit_3.setPlainText(new_text)

        # 滚动到最底部
        self.textEdit_3.moveCursor(QTextCursor.End)

    def closeEvent(self, event):
        self.saveSettings(capture_ui_config__path)

    def saveSettings(self, filename):
        # 保存窗口的设置到文件
        geometry = self.saveGeometry().toBase64().data().decode()
        settings = {
            'geometry': geometry,
            'x': self.x(),
            'y': self.y(),
            'width': self.width(),
            'height': self.height()
        }
        with open(filename, 'w') as file:
            json.dump(settings, file, indent=4)

    def loadSettings(self, filename):
        # 尝试从文件中加载窗口的设置
        try:
            with open(filename, 'r') as file:
                settings = json.load(file)
                self.restoreGeometry(QByteArray.fromBase64(settings['geometry'].encode()))
                self.move(QPoint(settings['x'], settings['y']))
                self.resize(QSize(settings['width'], settings['height']))
        except FileNotFoundError:
            # 如果文件不存在，则使用默认设置
            pass
        except json.JSONDecodeError:
            # 如果文件存在但格式不正确，则使用默认设置并可能给出警告
            print("Warning: Config file is corrupted or not in JSON format.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MYAPP()
    main.show()
    sys.exit(app.exec())
