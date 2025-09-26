import re

# 读取player.py文件内容
with open('d:\\dxf\\dxf_auto\\front\\core\\player.py', 'r', encoding='utf-8') as f:
    file_content = f.read()

# 定义要查找的模式和替换内容
pattern = r'def brush_map\(self\):.*?def brush_map_2\(self\):'
replacement = '''def brush_map(self):
        """调用GameFlowHandler的刷图方法"""
        return self.game_flow_handler.brush_map()

    def brush_map_2(self):'''

# 使用正则表达式进行替换（DOTALL模式让.匹配换行符）
new_content = re.sub(pattern, replacement, file_content, flags=re.DOTALL)

# 写回文件
with open('d:\\dxf\\dxf_auto\\front\\core\\player.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("替换完成！")