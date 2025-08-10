import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import re
import configparser
import os

# 配置文件路径
CONFIG_FILE = "route_manager.ini"


def delete_route(target="0.0.0.0", mask="0.0.0.0", gateway="192.168.3.1", permanent=False):
    """删除指定路由（支持永久路由）"""
    try:
        # 构建命令 - 永久路由需要特殊处理
        if permanent:
            # 获取永久路由的持久ID
            persistent_id = get_persistent_id(target, mask, gateway)
            if persistent_id:
                command = f"route delete {target} mask {mask} {gateway} -p"
            else:
                return False, f"⚠️ 未找到匹配的永久路由: {target}/{mask} -> {gateway}"
        else:
            command = f"route delete {target} mask {mask} {gateway}"

        # 执行命令
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='gbk',
            shell=True
        )

        if result.returncode == 0:
            return True, f"✅ 已成功删除{'永久' if permanent else ''}路由: {target}/{mask} -> {gateway}"
        else:
            return False, f"⚠️ 路由删除失败: {target}/{mask} -> {gateway}\n错误信息: {result.stderr.strip()}"
    except Exception as e:
        return False, f"❌ 执行删除命令时发生错误: {str(e)}"


def add_route(target="0.0.0.0", mask="0.0.0.0", gateway="192.168.3.1", metric=1, permanent=False):
    """添加新路由（支持永久路由）"""
    try:
        # 构建命令
        persistent_flag = "-p" if permanent else ""
        command = f"route add {target} mask {mask} {gateway} metric {metric} {persistent_flag}"

        # 执行命令
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='gbk',
            shell=True
        )

        if result.returncode == 0:
            return True, f"✅ 已成功添加{'永久' if permanent else ''}路由: {target}/{mask} -> {gateway} (跃点数 {metric})"
        else:
            return False, f"❌ 路由添加失败: {target}/{mask} -> {gateway}\n错误信息: {result.stderr.strip()}"
    except Exception as e:
        return False, f"❌ 执行添加命令时发生错误: {str(e)}"


def print_ipv4_routes():
    """获取IPv4路由表（包含永久路由信息）"""
    try:
        result = subprocess.run(
            "route print -4",
            capture_output=True,
            text=True,
            encoding='gbk',
            shell=True
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, f"❌ 无法获取路由表\n错误信息: {result.stderr.strip()}"
    except Exception as e:
        return False, f"❌ 执行路由表命令时发生错误: {str(e)}"


def get_persistent_routes():
    """获取所有永久路由信息"""
    try:
        result = subprocess.run(
            "route print -4",
            capture_output=True,
            text=True,
            encoding='gbk',
            shell=True
        )

        if result.returncode != 0:
            return []

        # 解析永久路由 - 修复解析逻辑
        routes = []
        lines = result.stdout.splitlines()
        persistent_section = False

        for line in lines:
            # 查找永久路由部分
            if "永久路由" in line:
                persistent_section = True
                continue

            if persistent_section:
                # 跳过标题行
                if "网络地址" in line and "网络掩码" in line and "网关地址" in line:
                    continue

                # 跳过空行
                if not line.strip():
                    continue

                # 使用正则表达式分割多个空格
                parts = re.split(r'\s{2,}', line.strip())

                # 确保有足够的数据列
                if len(parts) >= 3:
                    # 格式: 网络地址 网络掩码 网关地址 跃点数 接口
                    route_info = {
                        'target': parts[0],
                        'mask': parts[1],
                        'gateway': parts[2],
                        'metric': parts[3] if len(parts) > 3 else "",
                        'interface': parts[4] if len(parts) > 4 else ""
                    }
                    routes.append(route_info)

        return routes
    except Exception as e:
        print(f"解析永久路由时出错: {str(e)}")
        return []


def get_persistent_id(target, mask, gateway):
    """获取永久路由的持久ID"""
    persistent_routes = get_persistent_routes()
    for idx, route in enumerate(persistent_routes, 1):
        if (route['target'] == target and
                route['mask'] == mask and
                route['gateway'] == gateway):
            return idx
    return None


def is_admin():
    """检查是否以管理员权限运行"""
    if sys.platform == "win32":
        try:
            return subprocess.run(
                "net session >nul 2>&1",
                shell=True
            ).returncode == 0
        except:
            return False
    return True  # 非Windows系统暂时返回True


class ConfigManager:
    """配置文件管理类"""

    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = configparser.ConfigParser()

        # 如果配置文件不存在，则创建默认配置
        if not os.path.exists(self.config_file):
            self.create_default_config()
        else:
            self.config.read(self.config_file)

    def create_default_config(self):
        """创建默认配置文件"""
        self.config['SETTINGS'] = {
            'gateway': '192.168.1.1',
            'target': '0.0.0.0',
            'mask': '0.0.0.0',
            'metric': '1',
            'permanent': 'False'
        }
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def save_settings(self, settings):
        """保存设置到配置文件"""
        self.config['SETTINGS'] = settings
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)

    def load_settings(self):
        """从配置文件加载设置"""
        if not os.path.exists(self.config_file):
            self.create_default_config()

        self.config.read(self.config_file)
        return dict(self.config['SETTINGS'])


class RouteManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("高级路由管理工具")
        self.root.geometry("900x650")
        self.root.resizable(True, True)

        # 设置应用图标
        try:
            self.root.iconbitmap(sys.executable)
        except:
            pass

        # 检查管理员权限
        if not is_admin():
            messagebox.showerror("权限错误", "路由操作需要管理员权限！\n请以管理员身份运行此程序。")
            self.root.destroy()
            return

        # 初始化配置管理器
        self.config_manager = ConfigManager()

        # 加载配置
        self.settings = self.config_manager.load_settings()

        # 设置主题风格
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TButton', padding=6)
        self.style.configure('Title.TLabel', font=('Arial', 12, 'bold'))

        # 创建主框架
        self.create_widgets()

        # 初始加载路由表
        self.refresh_routes()
        # 初始加载永久路由
        self.refresh_permanent_routes()

        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        """窗口关闭时保存当前设置"""
        # 收集当前设置
        current_settings = {
            'gateway': self.gateway_var.get(),
            'target': self.target_var.get(),
            'mask': self.mask_var.get(),
            'metric': str(self.metric_var.get()),
            'permanent': str(self.permanent_var.get())
        }

        # 保存到配置文件
        self.config_manager.save_settings(current_settings)

        # 关闭窗口
        self.root.destroy()

    def create_widgets(self):
        """创建界面组件"""
        # 标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(title_frame, text="Windows 路由管理工具", style='Title.TLabel').pack(pady=10)

        # 创建选项卡
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)

        # 路由表选项卡
        self.tab_routes = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_routes, text='路由表')

        # 操作路由选项卡
        self.tab_actions = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_actions, text='路由操作')

        # 永久路由选项卡
        self.tab_permanent = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_permanent, text='永久路由')

        # 填充路由表选项卡
        self.create_routes_tab()

        # 填充路由操作选项卡
        self.create_actions_tab()

        # 填充永久路由选项卡
        self.create_permanent_tab()

    def create_routes_tab(self):
        """创建路由表选项卡"""
        # 控制按钮框架
        btn_frame = ttk.Frame(self.tab_routes)
        btn_frame.pack(fill='x', padx=10, pady=5)

        # 刷新按钮
        refresh_btn = ttk.Button(btn_frame, text="刷新路由表", command=self.refresh_routes)
        refresh_btn.pack(side='left', padx=5, pady=5)

        # 导出按钮
        export_btn = ttk.Button(btn_frame, text="导出路由表", command=self.export_routes)
        export_btn.pack(side='left', padx=5, pady=5)

        # 路由表显示区域
        route_frame = ttk.Frame(self.tab_routes)
        route_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # 添加滚动条
        scroll_y = ttk.Scrollbar(route_frame)
        scroll_y.pack(side='right', fill='y')

        scroll_x = ttk.Scrollbar(route_frame, orient='horizontal')
        scroll_x.pack(side='bottom', fill='x')

        # 路由表文本框
        self.route_text = tk.Text(
            route_frame,
            wrap=tk.NONE,
            font=('Consolas', 9),
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            bg='#f0f0f0'
        )
        self.route_text.pack(fill='both', expand=True)

        scroll_y.config(command=self.route_text.yview)
        scroll_x.config(command=self.route_text.xview)

    def create_actions_tab(self):
        """创建路由操作选项卡"""
        # 表单框架
        form_frame = ttk.LabelFrame(self.tab_actions, text="路由参数")
        form_frame.pack(fill='x', padx=10, pady=5)

        # 创建网格布局
        form_frame.columnconfigure(1, weight=1)
        form_frame.columnconfigure(3, weight=1)

        # 目标网络
        ttk.Label(form_frame, text="目标网络:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.target_var = tk.StringVar(value=self.settings.get('target', '0.0.0.0'))
        target_entry = ttk.Entry(form_frame, textvariable=self.target_var)
        target_entry.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        # 子网掩码
        ttk.Label(form_frame, text="子网掩码:").grid(row=0, column=2, padx=5, pady=5, sticky='e')
        self.mask_var = tk.StringVar(value=self.settings.get('mask', '0.0.0.0'))
        mask_entry = ttk.Entry(form_frame, textvariable=self.mask_var)
        mask_entry.grid(row=0, column=3, padx=5, pady=5, sticky='ew')

        # 网关
        ttk.Label(form_frame, text="网关:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.gateway_var = tk.StringVar(value=self.settings.get('gateway', '192.168.1.1'))
        gateway_entry = ttk.Entry(form_frame, textvariable=self.gateway_var)
        gateway_entry.grid(row=1, column=1, padx=5, pady=5, sticky='ew')

        # 跃点数
        ttk.Label(form_frame, text="跃点数:").grid(row=1, column=2, padx=5, pady=5, sticky='e')
        self.metric_var = tk.IntVar(value=int(self.settings.get('metric', '1')))
        metric_spin = ttk.Spinbox(form_frame, from_=1, to=9999, textvariable=self.metric_var, width=10)
        metric_spin.grid(row=1, column=3, padx=5, pady=5, sticky='w')

        # 永久路由选项
        permanent_value = self.settings.get('permanent', 'False').lower() == 'true'
        self.permanent_var = tk.BooleanVar(value=permanent_value)
        permanent_check = ttk.Checkbutton(form_frame, text="永久路由", variable=self.permanent_var)
        permanent_check.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='w')

        # 按钮框架
        btn_frame = ttk.Frame(self.tab_actions)
        btn_frame.pack(fill='x', padx=10, pady=10)

        # 添加路由按钮
        add_btn = ttk.Button(btn_frame, text="添加路由", command=self.add_route_action, width=15)
        add_btn.pack(side='left', padx=10, pady=5)

        # 删除路由按钮
        delete_btn = ttk.Button(btn_frame, text="删除路由", command=self.delete_route_action, width=15)
        delete_btn.pack(side='left', padx=10, pady=5)

        # 结果输出区域
        result_frame = ttk.LabelFrame(self.tab_actions, text="操作结果")
        result_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            height=8,
            wrap=tk.WORD,
            font=('Tahoma', 9)
        )
        self.result_text.pack(fill='both', expand=True, padx=5, pady=5)
        self.result_text.config(state='disabled', bg='#f5f5f5')

    def create_permanent_tab(self):
        """创建永久路由选项卡"""
        # 控制按钮框架
        btn_frame = ttk.Frame(self.tab_permanent)
        btn_frame.pack(fill='x', padx=10, pady=5)

        # 刷新按钮
        refresh_btn = ttk.Button(btn_frame, text="刷新永久路由", command=self.refresh_permanent_routes)
        refresh_btn.pack(side='left', padx=5, pady=5)

        # 删除按钮
        delete_btn = ttk.Button(btn_frame, text="删除选中的永久路由", command=self.delete_selected_permanent_route)
        delete_btn.pack(side='left', padx=5, pady=5)

        # 永久路由表格
        columns = ("target", "mask", "gateway", "metric", "interface")
        self.permanent_tree = ttk.Treeview(
            self.tab_permanent,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        # 设置列标题
        self.permanent_tree.heading("target", text="目标网络")
        self.permanent_tree.heading("mask", text="子网掩码")
        self.permanent_tree.heading("gateway", text="网关")
        self.permanent_tree.heading("metric", text="跃点数")
        self.permanent_tree.heading("interface", text="接口")

        # 设置列宽
        self.permanent_tree.column("target", width=120, anchor='center')
        self.permanent_tree.column("mask", width=120, anchor='center')
        self.permanent_tree.column("gateway", width=120, anchor='center')
        self.permanent_tree.column("metric", width=80, anchor='center')
        self.permanent_tree.column("interface", width=150, anchor='center')

        # 添加滚动条
        scroll_y = ttk.Scrollbar(self.tab_permanent, orient="vertical", command=self.permanent_tree.yview)
        scroll_y.pack(side='right', fill='y')
        self.permanent_tree.configure(yscrollcommand=scroll_y.set)

        scroll_x = ttk.Scrollbar(self.tab_permanent, orient="horizontal", command=self.permanent_tree.xview)
        scroll_x.pack(side='bottom', fill='x')
        self.permanent_tree.configure(xscrollcommand=scroll_x.set)

        self.permanent_tree.pack(fill='both', expand=True, padx=10, pady=5)

    def refresh_routes(self):
        """刷新路由表显示"""
        success, result = print_ipv4_routes()
        self.route_text.config(state='normal')
        self.route_text.delete(1.0, tk.END)

        if success:
            # 高亮显示永久路由部分
            self.route_text.insert(tk.END, result)

            # 查找永久路由部分并添加标签
            start_idx = result.find("永久路由:")
            if start_idx != -1:
                self.route_text.tag_add("permanent", f"1.0 + {start_idx} chars", "end")
                self.route_text.tag_config("permanent", foreground='blue', font=('Consolas', 9, 'bold'))
        else:
            self.route_text.insert(tk.END, result)

        self.route_text.config(state='disabled')

    def refresh_permanent_routes(self):
        """刷新永久路由表格 - 已修复"""
        # 清空现有数据
        for item in self.permanent_tree.get_children():
            self.permanent_tree.delete(item)

        # 获取永久路由
        persistent_routes = get_persistent_routes()

        # 添加到表格
        for route in persistent_routes:
            self.permanent_tree.insert("", "end", values=(
                route['target'],
                route['mask'],
                route['gateway'],
                route['metric'],
                route['interface']
            ))

        # 更新表格状态
        if persistent_routes:
            self.permanent_tree.config(height=min(15, len(persistent_routes)))
        else:
            self.permanent_tree.insert("", "end", values=("无永久路由", "", "", "", ""))

    def delete_selected_permanent_route(self):
        """删除选中的永久路由"""
        selected = self.permanent_tree.selection()
        if not selected:
            messagebox.showwarning("选择错误", "请先选择要删除的永久路由")
            return

        item = self.permanent_tree.item(selected[0])
        values = item['values']

        if len(values) >= 3 and values[0] != "无永久路由":
            target = values[0]
            mask = values[1]
            gateway = values[2]

            # 删除永久路由
            success, result = delete_route(target, mask, gateway, permanent=True)

            if success:
                # 刷新永久路由列表
                self.refresh_permanent_routes()
                # 刷新路由表
                self.refresh_routes()

            # 显示结果
            self.show_result(result)
        else:
            messagebox.showerror("操作错误", "无法删除此路由条目")

    def export_routes(self):
        """导出路由表到文件"""
        success, result = print_ipv4_routes()
        if not success:
            self.show_result(result)
            return

        try:
            with open('route_table.txt', 'w', encoding='gbk') as f:
                f.write(result)
            self.show_result("✅ 路由表已成功导出到 route_table.txt")
        except Exception as e:
            self.show_result(f"❌ 导出路由表失败: {str(e)}")

    def add_route_action(self):
        """执行添加路由操作"""
        target = self.target_var.get().strip()
        mask = self.mask_var.get().strip()
        gateway = self.gateway_var.get().strip()
        metric = self.metric_var.get()
        permanent = self.permanent_var.get()

        if not all([target, mask, gateway]):
            self.show_result("❌ 错误：请填写所有必填字段")
            return

        success, result = add_route(target, mask, gateway, metric, permanent)
        self.show_result(result)

        # 添加成功后刷新路由表
        if success:
            self.refresh_routes()
            # 如果是永久路由，刷新永久路由列表
            if permanent:
                self.refresh_permanent_routes()

    def delete_route_action(self):
        """执行删除路由操作"""
        target = self.target_var.get().strip()
        mask = self.mask_var.get().strip()
        gateway = self.gateway_var.get().strip()
        permanent = self.permanent_var.get()

        if not all([target, mask, gateway]):
            self.show_result("❌ 错误：请填写所有必填字段")
            return

        success, result = delete_route(target, mask, gateway, permanent)
        self.show_result(result)

        # 删除成功后刷新路由表
        if success:
            self.refresh_routes()
            # 如果是永久路由，刷新永久路由列表
            if permanent:
                self.refresh_permanent_routes()

    def show_result(self, message):
        """在结果区域显示消息"""
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, message)
        self.result_text.config(state='disabled')


if __name__ == "__main__":
    # 设置控制台代码页为简体中文(936)
    subprocess.run("chcp 936 >nul", shell=True)

    root = tk.Tk()
    app = RouteManagerApp(root)
    root.mainloop()
