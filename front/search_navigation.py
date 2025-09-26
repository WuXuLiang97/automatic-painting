import os
import sys

# 设置项目根目录
root_dir = r'd:\dxf\dxf_auto\front'

# 要搜索的类名
search_pattern = 'NavigationHandler'

# 忽略的文件
ignore_files = ['navigation.py', 'navigation_handler.py', 'player.py', '__init__.py']

print(f"搜索项目中的 {search_pattern} 引用，忽略特定文件...\n")

# 遍历所有Python文件
for root, _, files in os.walk(root_dir):
    for file in files:
        if file.endswith('.py') and file not in ignore_files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if search_pattern in content:
                        print(f"在 {file_path} 中找到 {search_pattern} 的引用")
            except Exception as e:
                print(f"读取文件 {file_path} 时出错: {e}")

print("\n搜索完成。")