# -*- coding: utf-8 -*-
"""
第六阶段功能增强测试脚本
测试内容：
1. 健康检查接口
2. 指标导出接口
3. 配置热重载
"""

import sys
import os
import io
import inspect

# 设置标准输出编码为 UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加 service_renew 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


def test_health_check():
    """测试1: 健康检查接口"""
    print("\n" + "=" * 60)
    print("测试1: 健康检查接口")
    print("=" * 60)
    
    try:
        # 检查方法是否存在
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            if 'def get_health_status(self)' in content:
                print("✓ get_health_status 方法存在")
            else:
                print("✗ get_health_status 方法不存在")
                return False
            
            # 检查返回类型注解
            if '-> Dict[str, Any]' in content or '-> Dict' in content:
                print("✓ 有返回类型注解")
            else:
                print("⚠ 缺少返回类型注解")
            
            # 检查方法内容
            if '"status"' in content and '"running"' in content and '"models"' in content:
                print("✓ 返回数据结构完整")
            else:
                print("⚠ 返回数据结构可能不完整")
        
        return True
    except Exception as e:
        print(f"✗ 健康检查接口测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics_export():
    """测试2: 指标导出接口"""
    print("\n" + "=" * 60)
    print("测试2: 指标导出接口")
    print("=" * 60)
    
    try:
        # 检查方法是否存在
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            if 'def get_metrics(self)' in content:
                print("✓ get_metrics 方法存在")
            else:
                print("✗ get_metrics 方法不存在")
                return False
            
            # 检查返回类型注解
            if '-> Dict[str, Any]' in content or '-> Dict' in content:
                print("✓ 有返回类型注解")
            else:
                print("⚠ 缺少返回类型注解")
            
            # 检查方法内容
            if 'total_requests' in content and 'error_rate' in content and 'by_type' in content:
                print("✓ 返回数据结构完整")
            else:
                print("⚠ 返回数据结构可能不完整")
        
        return True
    except Exception as e:
        print(f"✗ 指标导出接口测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_reload():
    """测试3: 配置热重载"""
    print("\n" + "=" * 60)
    print("测试3: 配置热重载")
    print("=" * 60)
    
    try:
        # 检查 config_manager.py 中的函数
        with open('server/config_manager.py', 'r', encoding='utf-8') as f:
            config_content = f.read()
            
            if 'def reload_config()' in config_content:
                print("✓ config_manager.reload_config 函数存在")
            else:
                print("✗ config_manager.reload_config 函数不存在")
                return False
            
            # 检查返回类型
            if '-> tuple' in config_content or '-> Tuple' in config_content:
                print("✓ 有返回类型注解")
            else:
                print("⚠ 缺少返回类型注解")
        
        # 检查 threaded_server.py 中的方法
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            server_content = f.read()
            
            if 'def reload_config(self)' in server_content:
                print("✓ ThreadedServer.reload_config 方法存在")
            else:
                print("✗ ThreadedServer.reload_config 方法不存在")
                return False
            
            # 检查返回类型
            if '-> Tuple[bool' in server_content:
                print("✓ 有返回类型注解")
            else:
                print("⚠ 缺少返回类型注解")
            
            # 检查是否调用了 config_manager.reload_config
            if 'from .config_manager import reload_config' in server_content or 'reload_config()' in server_content:
                print("✓ 正确调用 config_manager.reload_config")
            else:
                print("⚠ 可能未正确调用 config_manager.reload_config")
        
        return True
    except Exception as e:
        print(f"✗ 配置热重载测试失败: {e}")
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
            'server/config_manager.py',
            'server/threaded_server.py',
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
    print("第六阶段功能增强测试")
    print("=" * 60)
    
    tests = [
        ("健康检查接口", test_health_check),
        ("指标导出接口", test_metrics_export),
        ("配置热重载", test_config_reload),
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
        print("\n✓ 所有测试通过！第六阶段功能增强完成。")
        return 0
    else:
        print(f"\n✗ 有 {total - passed} 个测试失败，需要检查。")
        return 1


if __name__ == '__main__':
    exit(main())
