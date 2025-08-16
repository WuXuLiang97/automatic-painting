# -*- coding: utf-8 -*-
import win32gui
import win32con
import re


def find_vmware_windows():
    """查找所有类名为 VMUIFrame 的 VMware 窗口"""
    vmware_windows = []

    def enum_windows_callback(hwnd, windows_list):
        # 获取窗口类名
        class_name = win32gui.GetClassName(hwnd)

        # 检查是否是 VMUIFrame 类
        if class_name == "VMUIFrame":
            # 获取窗口标题
            window_title = win32gui.GetWindowText(hwnd)

            # 获取窗口位置和尺寸
            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top

            # 检查窗口是否可见
            is_visible = win32gui.IsWindowVisible(hwnd)

            # 添加到结果列表
            windows_list.append({
                'hwnd': hwnd,
                'title': window_title,
                'class': class_name,
                'position': (left, top),
                'size': (width, height),
                'visible': is_visible
            })

    # 枚举所有窗口
    win32gui.EnumWindows(enum_windows_callback, vmware_windows)

    return vmware_windows


def find_child_windows_by_class(parent_hwnd, class_name_pattern, visible_only=True):
    """
    查找指定父窗口下的子窗口（根据类名）

    :param parent_hwnd: 父窗口句柄
    :param class_name_pattern: 类名模式（字符串或正则表达式）
    :param visible_only: 是否只返回可见窗口
    :return: 匹配的子窗口列表 [{'hwnd': 句柄, 'class': 类名, ...}]
    """
    child_windows = []

    def enum_child_callback(hwnd, param_list):
        # 检查是否可见（如果需要）
        if visible_only and not win32gui.IsWindowVisible(hwnd):
            return True

        # 获取类名
        child_class = win32gui.GetClassName(hwnd)

        # 检查类名是否匹配
        if isinstance(class_name_pattern, str):
            if child_class == class_name_pattern:
                # 获取窗口信息
                title = win32gui.GetWindowText(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                left, top, right, bottom = rect
                width = right - left
                height = bottom - top

                param_list.append({
                    'hwnd': hwnd,
                    'class': child_class,
                    'title': title,
                    'position': (left, top),
                    'size': (width, height),
                    'visible': win32gui.IsWindowVisible(hwnd)
                })
        elif hasattr(class_name_pattern, "match"):  # 正则表达式对象
            if class_name_pattern.match(child_class):
                # 获取窗口信息
                title = win32gui.GetWindowText(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                left, top, right, bottom = rect
                width = right - left
                height = bottom - top

                param_list.append({
                    'hwnd': hwnd,
                    'class': child_class,
                    'title': title,
                    'position': (left, top),
                    'size': (width, height),
                    'visible': win32gui.IsWindowVisible(hwnd)
                })
        elif isinstance(class_name_pattern, (list, tuple, set)):
            if child_class in class_name_pattern:
                # 获取窗口信息
                title = win32gui.GetWindowText(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                left, top, right, bottom = rect
                width = right - left
                height = bottom - top

                param_list.append({
                    'hwnd': hwnd,
                    'class': child_class,
                    'title': title,
                    'position': (left, top),
                    'size': (width, height),
                    'visible': win32gui.IsWindowVisible(hwnd)
                })

        return True  # 继续枚举

    # 枚举子窗口
    win32gui.EnumChildWindows(parent_hwnd, enum_child_callback, child_windows)

    return child_windows


def activate_vmware_window(hwnd):
    """激活指定的 VMware 窗口"""
    # 恢复窗口（如果最小化）
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    # 将窗口置前
    win32gui.SetForegroundWindow(hwnd)
    win32gui.BringWindowToTop(hwnd)


def print_window_info(window, prefix=""):
    """打印窗口信息"""
    if prefix:
        print(f"{prefix}:")

    print(f"  句柄 (HWND): 0x{window['hwnd']:X} ({window['hwnd']})")
    print(f"  类名: {window['class']}")
    print(f"  标题: {window['title']}")
    print(f"  位置: ({window['position'][0]}, {window['position'][1]})")
    print(f"  尺寸: {window['size'][0]}x{window['size'][1]}")
    print(f"  可见: {'是' if window['visible'] else '否'}")
    print("-" * 50)


def print_vmware_windows_info(windows):
    """打印 VMware 窗口信息"""
    if not windows:
        print("未找到任何类名为 'VMUIFrame' 的 VMware 窗口")
        return

    print(f"找到 {len(windows)} 个 VMware 窗口:")
    for i, window in enumerate(windows, 1):
        print(f"\n窗口 #{i}:")
        print_window_info(window)


if __name__ == "__main__":
    # 查找所有 VMware 窗口
    vmware_windows = find_vmware_windows()

    # 打印窗口信息
    print_vmware_windows_info(vmware_windows)

    # 如果有找到窗口，激活第一个
    if vmware_windows:
        try:
            # 激活第一个 VMware 窗口
            parent_hwnd = vmware_windows[0]['hwnd']
            activate_vmware_window(parent_hwnd)
            print(f"\n已激活窗口: {vmware_windows[0]['title']}")

            # 查找该窗口下的特定子窗口
            print("\n查找VMware窗口下的子窗口...")

            # 查找常见的VMware子窗口类名
            child_classes = [
                "MKSEmbedded"
            ]

            # 查找子窗口
            child_windows = find_child_windows_by_class(parent_hwnd, child_classes)

            if child_windows:
                print(f"\n找到 {len(child_windows)} 个子窗口:")
                for i, child in enumerate(child_windows, 1):
                    print(f"\n子窗口 #{i}:")
                    print_window_info(child)
            else:
                print("\n未找到任何子窗口")

            # # 使用正则表达式查找特定模式的子窗口
            # print("\n使用正则表达式查找子窗口...")
            # vmware_pattern = re.compile(r"^VMUI.*")
            # vmware_children = find_child_windows_by_class(parent_hwnd, vmware_pattern)
            #
            # if vmware_children:
            #     print(f"\n找到 {len(vmware_children)} 个以'VMUI'开头的子窗口:")
            #     for i, child in enumerate(vmware_children, 1):
            #         print(f"\n子窗口 #{i}:")
            #         print_window_info(child)
            # else:
            #     print("\n未找到以'VMUI'开头的子窗口")

        except Exception as e:
            print(f"操作过程中出错: {e}")
