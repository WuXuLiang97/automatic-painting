import sys
import json
import os
from PyQt5.QtWidgets import QApplication, QFrame, QPushButton, QMessageBox, QDialog
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeyEvent

from root_dir import root_path
from view.key_config import Ui_Frame

target_dir = os.path.join(r"C:\Program Files", "json_resources")  # 拼接子目录
target_file = os.path.join(target_dir, "key_config.json")
DEFAULT_CONFIG = {
    'one_key_gather': {'key': 'Tab'},
    'move_character': {'key': 'W'},
    'back_to_selia': {'key': 'R'},
    'challenge_again': {'key': 'F10'},
    'skills': [
        ['Q', 'W', 'E', 'R', 'T', 'Y', 'Ctrl'],
        ['A', 'S', 'D', 'F', 'G', 'H', 'Alt']
    ]
}

# 禁止设置的按键
FORBIDDEN_KEYS = {
    Qt.Key_End: 'End',
    Qt.Key_Home: 'Home',
}


class KeyButton(QPushButton):
    """自定义按钮类，支持根据文本自动调整宽度"""

    def __init__(self, text='未设置', parent=None):
        super().__init__(text, parent)
        self.setMinimumWidth(60)
        self.setMaximumWidth(150)
        self.adjustWidth()

    def setText(self, text):
        super().setText(text)
        self.adjustWidth()

    def adjustWidth(self):
        """根据文本内容自动调整按钮宽度"""
        fm = self.fontMetrics()
        text_width = fm.width(self.text())
        new_width = max(60, min(150, text_width + 30))
        self.setFixedWidth(new_width)


class KeyConfigDialog(QDialog, Ui_Frame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.config_file = target_file
        self.waiting_widget = None

        # 替换原有按钮为自定义按钮
        self.replace_buttons()

        # 初始化技能按键网格
        self.skill_buttons = []
        self.init_skill_grid()

        # 所有可配置的按键按钮列表
        self.all_key_buttons = [
            self.btn_one_key_gather,
            self.btn_move_character,
            self.btn_back_to_selia,
            self.btn_challenge_again

        ]

        # 添加技能按钮到列表
        for row in self.skill_buttons:
            self.all_key_buttons.extend(row)

        # 连接按钮点击事件
        self.btn_one_key_gather.clicked.connect(lambda: self.on_key_button_clicked(self.btn_one_key_gather))
        self.btn_move_character.clicked.connect(lambda: self.on_key_button_clicked(self.btn_move_character))
        self.btn_back_to_selia.clicked.connect(lambda: self.on_key_button_clicked(self.btn_back_to_selia))
        self.btn_challenge_again.clicked.connect(lambda: self.on_key_button_clicked(self.btn_challenge_again))
        # 连接保存按钮
        self.pushButton.clicked.connect(self.save_config)
        self.pushButton2.clicked.connect(self.load_default_config)

        # 设置焦点策略和事件过滤器
        self.setFocusPolicy(Qt.StrongFocus)
        self.installEventFilter(self)

        # 加载配置
        self.load_config()

    def replace_buttons(self):
        """替换UI中的按钮为自定义按钮"""
        gather_geometry = self.btn_one_key_gather.geometry()
        move_geometry = self.btn_move_character.geometry()
        selia_geometry = self.btn_back_to_selia.geometry()
        again_geometry = self.btn_challenge_again.geometry()
        parent = self.btn_one_key_gather.parent()

        self.btn_one_key_gather.deleteLater()
        self.btn_move_character.deleteLater()
        self.btn_back_to_selia.deleteLater()
        self.btn_challenge_again.deleteLater()
        self.btn_one_key_gather = KeyButton('未设置', parent)
        self.btn_one_key_gather.setGeometry(gather_geometry)

        self.btn_move_character = KeyButton('未设置', parent)
        self.btn_move_character.setGeometry(move_geometry)

        self.btn_back_to_selia = KeyButton('未设置', parent)
        self.btn_back_to_selia.setGeometry(selia_geometry)

        self.btn_challenge_again = KeyButton('未设置', parent)
        self.btn_challenge_again.setGeometry(again_geometry)

    def init_skill_grid(self):
        """初始化技能按键网格 2行7列"""
        for row in range(2):
            row_buttons = []
            for col in range(7):
                btn = KeyButton('未设置')
                btn.clicked.connect(lambda checked, b=btn: self.on_key_button_clicked(b))
                self.gridLayout.addWidget(btn, row, col)
                row_buttons.append(btn)
            self.skill_buttons.append(row_buttons)

    def on_key_button_clicked(self, button):
        """按钮被点击时"""
        self.waiting_widget = button
        button.setText('按下按键...')
        self.setFocus()

    def eventFilter(self, obj, event):
        """事件过滤器，用于捕获特殊按键"""
        if event.type() == QEvent.KeyPress and self.waiting_widget:
            return self.handleKeyPress(event)
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        """捕获键盘按键事件"""
        if self.waiting_widget:
            self.handleKeyPress(event)

    def handleKeyPress(self, event):
        """处理按键事件"""
        key = event.key()
        modifiers = event.modifiers()

        # 检查是否是禁止设置的按键
        if key in FORBIDDEN_KEYS:
            QMessageBox.warning(self, '警告', f'按键 {FORBIDDEN_KEYS[key]} 不可设置！')
            self.waiting_widget.setText('未设置')
            self.waiting_widget = None
            return True

        # 获取按键名称
        key_name = self.get_key_info(key, modifiers, event)

        if key_name:
            # 检查按键冲突
            conflict_button = self.check_key_conflict(key_name, self.waiting_widget)
            if conflict_button:
                msg = f'按键 {key_name} 已被 {self.get_button_name(conflict_button)} 使用！\n是否替换？'
                reply = QMessageBox.question(self, '按键冲突', msg,
                                             QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    conflict_button.setText('未设置')
                else:
                    self.waiting_widget.setText('未设置')
                    self.waiting_widget = None
                    return True

            self.waiting_widget.setText(key_name)
            self.waiting_widget = None
            return True

        return False

    def get_key_info(self, key, modifiers, event):
        """获取按键的显示名称"""
        special_keys = {
            Qt.Key_Escape: 'Esc',
            Qt.Key_Space: 'Space',
            Qt.Key_Tab: 'Tab',
            Qt.Key_Return: 'Enter',
            Qt.Key_Enter: 'Enter',
            Qt.Key_Shift: 'Shift',
            Qt.Key_Control: 'Ctrl',
            Qt.Key_Alt: 'Alt',
            Qt.Key_CapsLock: 'CapsLock',
            Qt.Key_Backspace: 'Backspace',
            Qt.Key_Delete: 'Delete',
            Qt.Key_Insert: 'Insert',
            Qt.Key_Home: 'Home',
            Qt.Key_End: 'End',
            Qt.Key_PageUp: 'PageUp',
            Qt.Key_PageDown: 'PageDown',
            Qt.Key_Up: '↑',
            Qt.Key_Down: '↓',
            Qt.Key_Left: '←',
            Qt.Key_Right: '→',
            Qt.Key_Minus: '-',
            Qt.Key_Equal: '=',
            Qt.Key_BracketLeft: '[',
            Qt.Key_BracketRight: ']',
            Qt.Key_Backslash: '\\',
            Qt.Key_Semicolon: ';',
            Qt.Key_Apostrophe: "'",
            Qt.Key_Comma: ',',
            Qt.Key_Period: '.',
            Qt.Key_Slash: '/',
            Qt.Key_QuoteLeft: '`',
        }

        for i in range(24):
            special_keys[Qt.Key_F1 + i] = f'F{i + 1}'

        for i in range(10):
            special_keys[Qt.Key_0 + i] = str(i)

        for i in range(26):
            special_keys[Qt.Key_A + i] = chr(65 + i)

        base_key = special_keys.get(key, None)
        if not base_key:
            key_text = event.text() if hasattr(event, 'text') else ''
            if key_text and key_text.isprintable():
                base_key = key_text.upper()
            else:
                return None

        if key in [Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt]:
            return base_key

        key_parts = []
        if modifiers & Qt.ControlModifier:
            key_parts.append('Ctrl')
        if modifiers & Qt.AltModifier:
            key_parts.append('Alt')
        if modifiers & Qt.ShiftModifier:
            key_parts.append('Shift')

        key_parts.append(base_key)

        return '+'.join(key_parts)

    def check_key_conflict(self, key_name, current_button):
        """检查按键冲突"""
        for button in self.all_key_buttons:
            if button != current_button and button.text() == key_name:
                return button
        return None

    def get_button_name(self, button):
        """获取按钮的功能名称"""
        if button == self.btn_one_key_gather:
            return "一键聚物"
        elif button == self.btn_move_character:
            return "移动角色"
        elif button == self.btn_back_to_selia:
            return "回赛利亚房间"
        elif button == self.btn_challenge_again:
            return "再次挑战"
        else:
            for row_idx, row in enumerate(self.skill_buttons):
                for col_idx, btn in enumerate(row):
                    if btn == button:
                        return f"技能{row_idx + 1}-{col_idx + 1}"
        return "未知按钮"

    def save_config(self):
        """保存配置到文件"""
        # 检查是否有按键冲突（重复按键）
        key_names = {}
        for button in self.all_key_buttons:
            btn_text = button.text()
            if btn_text != '未设置':
                if btn_text in key_names:
                    QMessageBox.warning(
                        self, '错误',
                        f'存在按键冲突：{btn_text} 同时被「{self.get_button_name(key_names[btn_text])}」和「{self.get_button_name(button)}」使用！\n请先解决冲突再保存。'
                    )
                    return False
                key_names[btn_text] = button  # 存储按钮对象，方便提示冲突来源

        # 构造配置字典
        config = {
            'one_key_gather': {'key': self.btn_one_key_gather.text() if self.btn_one_key_gather.text() != '未设置' else ''},
            'move_character': {'key': self.btn_move_character.text() if self.btn_move_character.text() != '未设置' else ''},
            'back_to_selia': {'key': self.btn_back_to_selia.text() if self.btn_back_to_selia.text() != '未设置' else ''},
            'challenge_again': {'key': self.btn_challenge_again.text() if self.btn_challenge_again.text() != '未设置' else ''},
            'skills': []
        }

        # 补充技能按键配置
        for row in self.skill_buttons:
            row_keys = [btn.text() if btn.text() != '未设置' else '' for btn in row]
            config['skills'].append(row_keys)

        try:
            # 1. 确保目录存在（简化逻辑，去掉冗余判断）
            os.makedirs(target_dir, exist_ok=True)
            # 2. 打印调试信息（确认目录和文件路径）
            dir_path = os.path.abspath(target_dir)
            file_path = os.path.abspath(self.config_file)
            print(f"[调试] 目标目录：{dir_path}")
            print(f"[调试] 目标文件：{file_path}")

            # 3. 写入配置文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            # 4. 仅在保存成功时弹窗提示
            QMessageBox.information(self, '成功', f'配置已保存到：\n{file_path}')
            return True

        except Exception as e:
            # 5. 捕获异常并打印详细堆栈（关键：定位具体错误）
            import traceback
            error_detail = traceback.format_exc()
            print(f"[错误] 保存配置失败：\n{error_detail}")
            QMessageBox.critical(
                self, '保存失败',
                f'无法写入配置文件：\n{str(e)}\n\n详细错误信息已打印到控制台，请检查路径权限或日志。'
            )
            return False

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        has_unconfigured = any(button.text() == '未设置' for button in self.all_key_buttons)
        if has_unconfigured:
            reply = QMessageBox.question(self, '提示', '存在未设置的按键，是否保存当前配置？',
                                         QMessageBox.Save | QMessageBox.Cancel)
            if reply == QMessageBox.Save:
                if self.save_config():
                    event.accept()
                else:
                    event.ignore()
            else:
                event.ignore()
        else:
            event.accept()

    def load_config(self):
        """从文件加载配置"""
        if not os.path.exists(self.config_file):
            self.load_default_config()
            return

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if config.get('one_key_gather'):
                data = config['one_key_gather']
                if data.get('key'):
                    self.btn_one_key_gather.setText(data['key'])

            if config.get('move_character'):
                data = config['move_character']
                if data.get('key'):
                    self.btn_move_character.setText(data['key'])

            if config.get('back_to_selia'):
                data = config['back_to_selia']
                if data.get('key'):
                    self.btn_back_to_selia.setText(data['key'])

            if config.get('challenge_again'):
                data = config['challenge_again']
                if data.get('key'):
                    self.btn_challenge_again.setText(data['key'])

            skills = config.get('skills', [])
            for row_idx, row_data in enumerate(skills):
                if row_idx < len(self.skill_buttons):
                    for col_idx, key_data in enumerate(row_data):
                        if col_idx < len(self.skill_buttons[row_idx]):
                            # 直接使用字符串格式
                            if isinstance(key_data, str) and key_data:
                                self.skill_buttons[row_idx][col_idx].setText(key_data)
                            # 兼容旧格式（字典格式）
                            elif isinstance(key_data, dict) and key_data.get('key'):
                                self.skill_buttons[row_idx][col_idx].setText(key_data['key'])
                            else:
                                self.skill_buttons[row_idx][col_idx].setText('未设置')
        except Exception as e:
            print(f'加载配置失败：{str(e)}')
            self.load_default_config()

    def load_default_config(self):
        """加载默认配置"""
        reply = QMessageBox.question(self, '确认', '是否加载默认配置？\n这将覆盖当前的所有设置。',
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.No:
            return

        default = DEFAULT_CONFIG
        self.btn_one_key_gather.setText(default['one_key_gather']['key'])
        self.btn_move_character.setText(default['move_character']['key'])
        self.btn_back_to_selia.setText(default['back_to_selia']['key'])
        self.btn_challenge_again.setText(default['challenge_again']['key'])
        for row_idx, row_data in enumerate(default['skills']):
            if row_idx < len(self.skill_buttons):
                for col_idx, key in enumerate(row_data):
                    if col_idx < len(self.skill_buttons[row_idx]):
                        self.skill_buttons[row_idx][col_idx].setText(key)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = KeyConfigDialog()
    dialog.exec_()
