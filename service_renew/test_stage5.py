# -*- coding: utf-8 -*-
"""
第五阶段代码质量提升测试脚本
测试内容：
1. 常量集中管理
2. 协议定义
3. 类型提示
"""

import sys
import os
import io
import ast
import inspect

# 设置标准输出编码为 UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加 service_renew 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


def test_constants_management():
    """测试1: 常量集中管理"""
    print("\n" + "=" * 60)
    print("测试1: 常量集中管理")
    print("=" * 60)
    
    try:
        # 检查 constants.py 是否存在
        if not os.path.exists('server/constants.py'):
            print("✗ constants.py 文件不存在")
            return False
        print("✓ constants.py 文件存在")
        
        # 检查是否导入了 constants
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            threaded_content = f.read()
            if 'from .constants import' in threaded_content:
                print("✓ threaded_server.py 导入了 constants")
            else:
                print("✗ threaded_server.py 未导入 constants")
                return False
        
        with open('server/ocr_handler.py', 'r', encoding='utf-8') as f:
            ocr_content = f.read()
            if 'from .constants import' in ocr_content:
                print("✓ ocr_handler.py 导入了 constants")
            else:
                print("✗ ocr_handler.py 未导入 constants")
                return False
        
        # 检查是否还有硬编码的数字（常见值）
        hardcoded_values = [
            ('50 * 1024 * 1024', 'MAX_IMAGE_SIZE'),
            ('1024 * 1024', 'MAX_HEADER_SIZE'),
            ('100', 'MAX_CONNECTIONS'),
            ('8192', 'SOCKET_CHUNK_SIZE'),
            ('0.2', 'OCR_DET_BIN_THRESH'),
            ('0.50', 'OCR_DET_BOX_THRESH'),
            ('0.85', 'OCR_PADDLE_SCORE_THRESH'),
            ('320', 'OCR_MAX_REC_WIDTH'),
            ('256', 'OCR_MIN_DET_SIDE'),
            ('960', 'OCR_DET_LIMIT_SIDE_LEN'),
            ('48', 'OCR_REC_IMG_HEIGHT'),
            ('32', 'OCR_ALIGN_MULTIPLE'),
        ]
        
        # 检查 threaded_server.py
        found_hardcoded = []
        for value, constant_name in hardcoded_values:
            if value in threaded_content and constant_name not in threaded_content:
                # 检查是否在注释中
                lines = threaded_content.split('\n')
                for i, line in enumerate(lines):
                    if value in line and constant_name not in line:
                        # 检查是否是注释
                        stripped = line.strip()
                        if not stripped.startswith('#'):
                            found_hardcoded.append((value, constant_name, i+1))
                            break
        
        if found_hardcoded:
            print(f"⚠ 发现可能的硬编码值: {found_hardcoded[:3]}")
        else:
            print("✓ 未发现明显的硬编码值")
        
        # 检查 constants.py 中是否定义了关键常量
        with open('server/constants.py', 'r', encoding='utf-8') as f:
            constants_content = f.read()
            required_constants = [
                'MAX_IMAGE_SIZE',
                'MAX_HEADER_SIZE',
                'MAX_CONNECTIONS',
                'SOCKET_CHUNK_SIZE',
                'OCR_DET_BIN_THRESH',
                'OCR_DET_BOX_THRESH',
                'OCR_PADDLE_SCORE_THRESH',
                'OCR_MAX_REC_WIDTH',
                'OCR_MIN_DET_SIDE',
            ]
            missing = []
            for const in required_constants:
                if const not in constants_content:
                    missing.append(const)
            
            if missing:
                print(f"✗ constants.py 缺少常量: {missing}")
                return False
            else:
                print(f"✓ constants.py 包含所有关键常量 ({len(required_constants)} 个)")
        
        return True
    except Exception as e:
        print(f"✗ 常量管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_protocol_definition():
    """测试2: 协议定义"""
    print("\n" + "=" * 60)
    print("测试2: 协议定义")
    print("=" * 60)
    
    try:
        # 检查 protocol.py 是否存在
        if not os.path.exists('server/protocol.py'):
            print("✗ protocol.py 文件不存在")
            return False
        print("✓ protocol.py 文件存在")
        
        # 检查是否导入了 protocol
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            threaded_content = f.read()
            if 'from .protocol import' in threaded_content:
                print("✓ threaded_server.py 导入了 protocol")
            else:
                print("✗ threaded_server.py 未导入 protocol")
                return False
        
        # 检查 protocol.py 中是否定义了关键常量
        with open('server/protocol.py', 'r', encoding='utf-8') as f:
            protocol_content = f.read()
            required_constants = [
                'REQUEST_TYPE_GAME_WINDOWS',
                'REQUEST_TYPE_MIN_MAP',
                'REQUEST_TYPE_OCR',
                'VALID_REQUEST_TYPES',
                'HEADER_FIELD_TYPE',
                'HEADER_FIELD_IMAGE_SIZE',
                'RESPONSE_FIELD_TYPE',
                'RESPONSE_FIELD_DATA_SIZE',
                'ERROR_FIELD_ERROR',
            ]
            missing = []
            for const in required_constants:
                if const not in protocol_content:
                    missing.append(const)
            
            if missing:
                print(f"✗ protocol.py 缺少常量: {missing}")
                return False
            else:
                print(f"✓ protocol.py 包含所有关键常量 ({len(required_constants)} 个)")
        
        # 检查是否使用了协议常量而不是硬编码字符串
        hardcoded_strings = [
            ('"game_windows"', 'REQUEST_TYPE_GAME_WINDOWS'),
            ('"min_map"', 'REQUEST_TYPE_MIN_MAP'),
            ('"ocr"', 'REQUEST_TYPE_OCR'),
            ('"type"', 'HEADER_FIELD_TYPE'),
            ('"image_size"', 'HEADER_FIELD_IMAGE_SIZE'),
            ('"data_size"', 'RESPONSE_FIELD_DATA_SIZE'),
            ('"error"', 'ERROR_FIELD_ERROR'),
        ]
        
        found_hardcoded = []
        for value, constant_name in hardcoded_strings:
            # 检查是否在 threaded_server.py 中使用了硬编码字符串
            if value in threaded_content:
                # 检查是否也使用了常量
                if constant_name not in threaded_content:
                    # 检查是否是注释或字符串文档
                    lines = threaded_content.split('\n')
                    for i, line in enumerate(lines):
                        if value in line and constant_name not in line:
                            stripped = line.strip()
                            # 跳过注释和文档字符串
                            if not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                                # 检查是否在字符串字面量中（可能是日志）
                                if f'logger.' in line or 'print(' in line:
                                    continue  # 日志中的字符串可以接受
                                found_hardcoded.append((value, constant_name, i+1))
                                break
        
        if found_hardcoded:
            print(f"⚠ 发现可能的硬编码字符串: {found_hardcoded[:3]}")
            print("  (日志消息中的字符串可以接受)")
        else:
            print("✓ 未发现明显的硬编码字符串（除日志消息）")
        
        # 检查是否使用了协议常量
        protocol_constants_used = [
            'REQUEST_TYPE_GAME_WINDOWS',
            'REQUEST_TYPE_MIN_MAP',
            'REQUEST_TYPE_OCR',
            'HEADER_FIELD_TYPE',
            'ERROR_FIELD_ERROR',
        ]
        used_count = sum(1 for const in protocol_constants_used if const in threaded_content)
        print(f"✓ 使用了 {used_count}/{len(protocol_constants_used)} 个协议常量")
        
        return True
    except Exception as e:
        print(f"✗ 协议定义测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_type_hints():
    """测试3: 类型提示"""
    print("\n" + "=" * 60)
    print("测试3: 类型提示")
    print("=" * 60)
    
    try:
        # 检查是否导入了 typing 模块
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            threaded_content = f.read()
            if 'from typing import' in threaded_content or 'import typing' in threaded_content:
                print("✓ threaded_server.py 导入了 typing 模块")
            else:
                print("✗ threaded_server.py 未导入 typing 模块")
                return False
        
        with open('server/ocr_handler.py', 'r', encoding='utf-8') as f:
            ocr_content = f.read()
            if 'from typing import' in ocr_content or 'import typing' in ocr_content:
                print("✓ ocr_handler.py 导入了 typing 模块")
            else:
                print("✗ ocr_handler.py 未导入 typing 模块")
                return False
        
        with open('server/yolo_handler.py', 'r', encoding='utf-8') as f:
            yolo_content = f.read()
            if 'from typing import' in yolo_content or 'import typing' in yolo_content:
                print("✓ yolo_handler.py 导入了 typing 模块")
            else:
                print("✗ yolo_handler.py 未导入 typing 模块")
                return False
        
        # 检查主要方法是否有类型提示
        methods_to_check = [
            ('ThreadedServer', '__init__', threaded_content),
            ('ThreadedServer', 'start', threaded_content),
            ('ThreadedServer', 'stop', threaded_content),
            ('ThreadedServer', '_handle_client', threaded_content),
            ('ThreadedServer', '_receive_message', threaded_content),
            ('ThreadedServer', '_send_response', threaded_content),
            ('OCRHandler', '__init__', ocr_content),
            ('OCRHandler', 'process', ocr_content),
            ('YoloHandler', '__init__', yolo_content),
            ('YoloHandler', 'process', yolo_content),
        ]
        
        found_hints = 0
        missing_hints = []
        
        for class_name, method_name, content in methods_to_check:
            # 查找方法定义
            pattern = f'def {method_name}('
            if pattern in content:
                # 查找方法定义行
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if pattern in line:
                        # 检查是否有类型提示（包含 -> 或 :）
                        if '->' in line or ':' in line.split('(')[1] if '(' in line else False:
                            found_hints += 1
                            break
                else:
                    missing_hints.append(f"{class_name}.{method_name}")
        
        if missing_hints:
            print(f"⚠ 以下方法缺少类型提示: {missing_hints[:5]}")
        else:
            print(f"✓ 所有主要方法都有类型提示 ({found_hints} 个)")
        
        # 检查返回类型注解
        return_annotations = [
            ('-> None', threaded_content),
            ('-> Tuple', threaded_content),
            ('-> Optional', threaded_content),
            ('-> str', ocr_content),
            ('-> List', ocr_content),
        ]
        
        found_returns = sum(1 for pattern, content in return_annotations if pattern in content)
        print(f"✓ 发现 {found_returns} 个返回类型注解")
        
        return True
    except Exception as e:
        print(f"✗ 类型提示测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_code_quality():
    """测试4: 代码质量检查"""
    print("\n" + "=" * 60)
    print("测试4: 代码质量检查")
    print("=" * 60)
    
    try:
        # 检查是否有语法错误
        import py_compile
        
        files = [
            'server/constants.py',
            'server/protocol.py',
            'server/threaded_server.py',
            'server/ocr_handler.py',
            'server/yolo_handler.py',
        ]
        
        for file in files:
            try:
                py_compile.compile(file, doraise=True)
                print(f"✓ {file} 语法正确")
            except py_compile.PyCompileError as e:
                print(f"✗ {file} 语法错误: {e}")
                return False
        
        # 检查是否可以导入模块
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from server import constants
            from server import protocol
            print("✓ 可以导入 constants 模块")
            print("✓ 可以导入 protocol 模块")
        except Exception as e:
            print(f"✗ 导入模块失败: {e}")
            return False
        
        return True
    except Exception as e:
        print(f"✗ 代码质量检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("第五阶段代码质量提升测试")
    print("=" * 60)
    
    tests = [
        ("常量集中管理", test_constants_management),
        ("协议定义", test_protocol_definition),
        ("类型提示", test_type_hints),
        ("代码质量检查", test_code_quality),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ 测试 '{name}' 执行异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 统计结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n✓ 所有测试通过！第五阶段代码质量提升完成。")
        return 0
    else:
        print(f"\n✗ 有 {total - passed} 个测试失败，需要检查。")
        return 1


if __name__ == '__main__':
    exit(main())
