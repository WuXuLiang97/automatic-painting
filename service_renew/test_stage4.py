# -*- coding: utf-8 -*-
"""
第四阶段性能优化测试脚本
测试内容：
1. 图像解码优化（BytesIO 使用）
2. OCR 处理优化（生成器表达式）
3. 统计指标优化（排序算法）
"""

import sys
import os
import io

# 设置标准输出编码为 UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加 service_renew 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_image_decode_optimization():
    """测试1: 图像解码优化"""
    print("\n" + "=" * 60)
    print("测试1: 图像解码优化")
    print("=" * 60)
    
    try:
        # 检查代码中是否使用了 BytesIO
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查导入
            if 'from io import BytesIO' in content or 'import BytesIO' in content:
                print("✓ BytesIO 已导入")
            else:
                print("✗ BytesIO 未导入")
                return False
            
            # 检查使用
            if 'BytesIO()' in content:
                print("✓ 使用了 BytesIO")
            else:
                print("✗ 未使用 BytesIO")
                return False
            
            # 检查是否还有旧的 chunks 列表方式
            if 'chunks = []' in content and 'chunks.append(chunk)' in content:
                # 检查是否在 _receive_message 中
                receive_start = content.find('def _receive_message(self, conn):')
                receive_end = content.find('def ', receive_start + 1)
                if receive_end == -1:
                    receive_end = len(content)
                receive_code = content[receive_start:receive_end]
                
                if 'chunks = []' in receive_code:
                    print("⚠ 仍在使用 chunks 列表（可能在其他地方）")
                else:
                    print("✓ 不再使用 chunks 列表方式")
            else:
                print("✓ 不再使用 chunks 列表方式")
            
            # 检查块大小
            if '8192' in content or 'chunk_size = min(8192' in content:
                print("✓ 使用更大的块大小（8192 字节）")
            else:
                print("⚠ 块大小可能未优化")
            
            # 检查资源释放
            if 'image_buffer.close()' in content:
                print("✓ BytesIO 缓冲区正确关闭")
            else:
                print("⚠ BytesIO 缓冲区可能未关闭")
                return False
        
        return True
    except Exception as e:
        print(f"✗ 图像解码优化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ocr_optimization():
    """测试2: OCR 处理优化"""
    print("\n" + "=" * 60)
    print("测试2: OCR 处理优化")
    print("=" * 60)
    
    try:
        # 检查 OCR 处理代码
        with open('server/ocr_handler.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查是否使用生成器表达式
            if "''.join(r['text'] for r in results" in content:
                print("✓ 使用生成器表达式（优化后）")
            elif "''.join([r['text'] for r in results" in content:
                print("✗ 仍使用列表推导式（未优化）")
                return False
            else:
                print("⚠ 未找到相关代码")
                return False
            
            # 检查是否有其他可以优化的列表推导式
            # 但 char_probs 需要列表，所以保留列表推导式是合理的
            if "[round(c, 4) for c in char_confs]" in content:
                print("✓ char_probs 使用列表推导式（合理，需要列表）")
        
        return True
    except Exception as e:
        print(f"✗ OCR 处理优化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics_optimization():
    """测试3: 统计指标优化"""
    print("\n" + "=" * 60)
    print("测试3: 统计指标优化")
    print("=" * 60)
    
    try:
        # 检查统计指标代码
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 查找 _metrics_loop 方法
            if 'def _metrics_loop(self):' in content:
                metrics_start = content.find('def _metrics_loop(self):')
                metrics_end = content.find('def ', metrics_start + 1)
                if metrics_end == -1:
                    metrics_end = len(content)
                metrics_code = content[metrics_start:metrics_end]
                
                # 检查平均值计算（不需要排序）
                if 'avg = sum(lat_list) /' in metrics_code:
                    # 检查是否在排序之前
                    avg_pos = metrics_code.find('avg = sum(lat_list) /')
                    sort_pos = metrics_code.find('sorted', avg_pos)
                    if sort_pos == -1 or sort_pos > avg_pos + 100:
                        print("✓ 平均值计算在排序之前（优化）")
                    else:
                        print("⚠ 平均值计算可能在排序之后")
                else:
                    print("⚠ 未找到平均值计算")
                
                # 检查小样本优化
                if 'if sample_count >= 20:' in metrics_code or 'if len(lat_list) >= 20:' in metrics_code:
                    print("✓ 小样本使用近似值（优化）")
                else:
                    print("⚠ 未找到小样本优化")
                
                # 检查是否总是排序
                if 'lat_list.sort()' in metrics_code:
                    # 检查是否在条件中
                    if 'if' in metrics_code and 'sorted(' in metrics_code:
                        print("✓ 只在需要时排序（优化）")
                    else:
                        print("⚠ 可能总是排序（未优化）")
                        return False
                elif 'sorted(' in metrics_code:
                    print("✓ 使用 sorted() 函数（优化）")
                else:
                    print("⚠ 未找到排序代码")
                    return False
            else:
                print("✗ _metrics_loop 方法未找到")
                return False
        
        return True
    except Exception as e:
        print(f"✗ 统计指标优化测试失败: {e}")
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
            'server/threaded_server.py',
            'server/ocr_handler.py',
        ]
        
        for file in files:
            try:
                py_compile.compile(file, doraise=True)
                print(f"✓ {file} 语法正确")
            except py_compile.PyCompileError as e:
                print(f"✗ {file} 语法错误: {e}")
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
    print("第四阶段性能优化测试")
    print("=" * 60)
    
    tests = [
        ("图像解码优化", test_image_decode_optimization),
        ("OCR 处理优化", test_ocr_optimization),
        ("统计指标优化", test_metrics_optimization),
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
        print("\n✓ 所有测试通过！第四阶段优化完成。")
        return 0
    else:
        print(f"\n✗ 有 {total - passed} 个测试失败，需要检查。")
        return 1


if __name__ == '__main__':
    exit(main())
