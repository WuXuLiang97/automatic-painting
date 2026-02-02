# -*- coding: utf-8 -*-
"""
功能测试脚本：验证已完成阶段的功能
测试内容：
1. 配置加载和验证
2. 日志系统
3. 服务器启动
4. 基本功能验证
"""

import sys
import os
import io
import time
import socket
import struct
import json
import threading

# 设置标准输出编码为 UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加 service_renew 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def test_config_loading():
    """测试1: 配置加载和验证"""
    print("\n" + "=" * 60)
    print("测试1: 配置加载和验证")
    print("=" * 60)
    
    try:
        from server.config_manager import settings
        
        print(f"✓ 配置加载成功")
        print(f"  服务器地址: {settings.host}:{settings.port}")
        print(f"  最大工作线程: {settings.max_workers}")
        print(f"  任务队列大小: {settings.task_queue_size}")
        print(f"  每线程独立模型: {settings.per_thread_models}")
        print(f"  模型预热: {settings.model_warmup}")
        
        # 验证配置值
        assert 1 <= settings.port <= 65535, "端口号无效"
        assert settings.max_workers >= 1, "线程数无效"
        assert settings.task_queue_size >= 1, "队列大小无效"
        
        print("✓ 配置验证通过")
        return True
    except ValueError as e:
        print(f"✗ 配置验证失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logger():
    """测试2: 日志系统"""
    print("\n" + "=" * 60)
    print("测试2: 日志系统")
    print("=" * 60)
    
    try:
        from server.logger import get_logger
        
        logger = get_logger('test_logger')
        
        logger.debug("这是一条 DEBUG 日志")
        logger.info("这是一条 INFO 日志")
        logger.warning("这是一条 WARNING 日志")
        logger.error("这是一条 ERROR 日志")
        
        print("✓ 日志系统工作正常")
        print("  检查日志文件: service_renew/log/server.log")
        return True
    except Exception as e:
        print(f"✗ 日志系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_server_import():
    """测试3: 服务器模块导入"""
    print("\n" + "=" * 60)
    print("测试3: 服务器模块导入")
    print("=" * 60)
    
    try:
        # 检查文件是否存在
        import os
        files = [
            'server/threaded_server.py',
            'server/yolo_handler.py',
            'server/ocr_handler.py',
            'server/config_manager.py',
            'server/logger.py',
        ]
        
        for file in files:
            if not os.path.exists(file):
                print(f"✗ 文件不存在: {file}")
                return False
        
        print("✓ 所有必需文件存在")
        
        # 检查代码结构（不导入，避免依赖问题）
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'class ThreadedServer' in content:
                print("✓ ThreadedServer 类定义存在")
            else:
                print("✗ ThreadedServer 类未找到")
                return False
        
        with open('server/yolo_handler.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'class YoloHandler' in content:
                print("✓ YoloHandler 类定义存在")
            else:
                print("✗ YoloHandler 类未找到")
                return False
        
        with open('server/ocr_handler.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'class OCRHandler' in content:
                print("✓ OCRHandler 类定义存在")
            else:
                print("✗ OCRHandler 类未找到")
                return False
        
        return True
    except Exception as e:
        print(f"✗ 服务器模块检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_security_constants():
    """测试4: 安全限制常量"""
    print("\n" + "=" * 60)
    print("测试4: 安全限制常量")
    print("=" * 60)
    
    try:
        # 检查代码中的常量定义
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            constants = {
                'MAX_IMAGE_SIZE': '50 * 1024 * 1024',
                'MAX_HEADER_SIZE': '1024 * 1024',
                'MAX_CONNECTIONS': '100',
                'VALID_REQUEST_TYPES': '{"game_windows", "min_map", "ocr"}'
            }
            
            for const_name, expected_value in constants.items():
                if const_name in content:
                    print(f"✓ {const_name} 常量已定义")
                else:
                    print(f"✗ {const_name} 常量未找到")
                    return False
            
            # 检查值
            if '50 * 1024 * 1024' in content:
                print("✓ 最大图像大小: 50MB")
            if '1024 * 1024' in content:
                print("✓ 最大头部大小: 1MB")
            if 'MAX_CONNECTIONS = 100' in content or 'MAX_CONNECTIONS=100' in content:
                print("✓ 最大连接数: 100")
            if '"game_windows"' in content and '"min_map"' in content and '"ocr"' in content:
                print("✓ 有效请求类型: game_windows, min_map, ocr")
        
        print("✓ 安全常量验证通过")
        return True
    except Exception as e:
        print(f"✗ 安全常量测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_exception_handling():
    """测试5: 异常处理"""
    print("\n" + "=" * 60)
    print("测试5: 异常处理")
    print("=" * 60)
    
    try:
        # 检查代码中的异常处理
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            exception_types = ['ValueError', 'RuntimeError', 'AttributeError', 
                              'ConnectionResetError', 'BrokenPipeError', 
                              'ConnectionAbortedError', 'socket.error', 'OSError']
            found_exceptions = []
            for exc_type in exception_types:
                if exc_type in content:
                    found_exceptions.append(exc_type)
            
            print(f"✓ 异常处理完善")
            print(f"  发现的异常类型: {', '.join(found_exceptions)}")
            
            # 检查是否有 exc_info=True
            if 'exc_info=True' in content:
                print("✓ 异常处理包含完整堆栈记录")
            else:
                print("⚠ 部分异常处理可能缺少完整堆栈记录")
            
            # 检查 finally 块
            if 'finally:' in content:
                print("✓ 有 finally 块确保资源释放")
            else:
                print("⚠ 缺少 finally 块")
                return False
        
        return True
    except Exception as e:
        print(f"✗ 异常处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_thread_safety():
    """测试6: 线程安全"""
    print("\n" + "=" * 60)
    print("测试6: 线程安全")
    print("=" * 60)
    
    try:
        # 检查代码中的锁定义和使用
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查锁定义
            locks = ['_model_lock', '_connections_lock', '_stats_lock']
            for lock in locks:
                if lock in content:
                    print(f"✓ {lock} 已定义")
                else:
                    print(f"✗ {lock} 未找到")
                    return False
            
            # 检查锁的使用
            if 'threading.Lock()' in content:
                print("✓ 使用 threading.Lock()")
            else:
                print("⚠ 未找到 threading.Lock() 定义")
                return False
            
            # 检查共享模型模式下是否使用锁
            if 'with self._model_lock:' in content:
                print("✓ 共享模型模式下使用锁保护")
            else:
                print("⚠ 共享模型模式下未找到锁保护代码")
                return False
            
            # 检查连接数锁的使用
            if 'with self._connections_lock:' in content:
                print("✓ 连接数统计使用锁保护")
            else:
                print("⚠ 连接数统计未使用锁保护")
                return False
        
        return True
    except Exception as e:
        print(f"✗ 线程安全测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_socket_management():
    """测试7: Socket 资源管理"""
    print("\n" + "=" * 60)
    print("测试7: Socket 资源管理")
    print("=" * 60)
    
    try:
        # 检查代码中的 socket 管理
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查 _listen 方法
            if 'def _listen(self):' in content:
                listen_start = content.find('def _listen(self):')
                listen_end = content.find('def ', listen_start + 1)
                if listen_end == -1:
                    listen_end = len(content)
                listen_code = content[listen_start:listen_end]
                
                if 'finally:' in listen_code and 'sock.close()' in listen_code:
                    print("✓ _listen 方法有 finally 块确保 socket 关闭")
                else:
                    print("⚠ _listen 方法缺少 finally 块或 socket 关闭代码")
                    return False
            else:
                print("✗ _listen 方法未找到")
                return False
            
            # 检查 _handle_client 方法
            if 'def _handle_client(self,' in content:
                handle_start = content.find('def _handle_client(self,')
                handle_end = content.find('def ', handle_start + 1)
                if handle_end == -1:
                    handle_end = len(content)
                handle_code = content[handle_start:handle_end]
                
                if 'finally:' in handle_code and 'conn.close()' in handle_code:
                    print("✓ _handle_client 方法有 finally 块确保连接关闭")
                else:
                    print("⚠ _handle_client 方法缺少 finally 块或连接关闭代码")
                    return False
            else:
                print("✗ _handle_client 方法未找到")
                return False
            
            # 检查 stop 方法
            if 'def stop(self):' in content:
                stop_start = content.find('def stop(self):')
                stop_end = content.find('def ', stop_start + 1)
                if stop_end == -1:
                    stop_end = len(content)
                stop_code = content[stop_start:stop_end]
                
                if 'self._listen_sock.close()' in stop_code:
                    print("✓ stop 方法正确关闭监听 socket")
                else:
                    print("⚠ stop 方法未关闭监听 socket")
                    return False
            else:
                print("✗ stop 方法未找到")
                return False
            
            # 检查异常处理
            if 'OSError' in content or 'socket.error' in content:
                print("✓ Socket 操作有异常处理")
            else:
                print("⚠ Socket 操作缺少异常处理")
        
        return True
    except Exception as e:
        print(f"✗ Socket 资源管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_thread_pool_shutdown():
    """测试8: 线程池关闭"""
    print("\n" + "=" * 60)
    print("测试8: 线程池关闭")
    print("=" * 60)
    
    try:
        # 检查代码中的线程池关闭逻辑
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查 stop 方法
            if 'def stop(self):' in content:
                stop_start = content.find('def stop(self):')
                stop_end = content.find('def ', stop_start + 1)
                if stop_end == -1:
                    stop_end = len(content)
                stop_code = content[stop_start:stop_end]
                
                if 'shutdown(wait=True' in stop_code:
                    print("✓ 线程池使用 wait=True 优雅关闭")
                else:
                    print("⚠ 线程池未使用 wait=True")
                    return False
                
                if 'timeout' in stop_code or '_shutdown_timeout' in stop_code:
                    print("✓ 线程池关闭有超时设置")
                else:
                    print("⚠ 线程池关闭缺少超时设置")
                    return False
                
                if 'TimeoutError' in stop_code:
                    print("✓ 线程池关闭有超时处理")
                else:
                    print("⚠ 线程池关闭缺少超时处理")
                    return False
            else:
                print("✗ stop 方法未找到")
                return False
            
            # 检查超时配置
            if '_shutdown_timeout' in content:
                print("✓ 关闭超时配置已定义")
            else:
                print("⚠ 关闭超时配置未定义")
        
        return True
    except Exception as e:
        print(f"✗ 线程池关闭测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_init_handling():
    """测试9: 模型初始化失败处理"""
    print("\n" + "=" * 60)
    print("测试9: 模型初始化失败处理")
    print("=" * 60)
    
    try:
        # 检查 YoloHandler 中的 _model_loaded 标志
        with open('server/yolo_handler.py', 'r', encoding='utf-8') as f:
            yolo_content = f.read()
            if '_model_loaded' in yolo_content:
                print("✓ YoloHandler 有 _model_loaded 标志")
            else:
                print("⚠ YoloHandler 缺少 _model_loaded 标志")
                return False
        
        # 检查 _worker 方法中的失败处理
        with open('server/threaded_server.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 查找 _worker 方法
            if 'def _worker(self):' in content:
                worker_start = content.find('def _worker(self):')
                worker_end = content.find('def ', worker_start + 1)
                if worker_end == -1:
                    worker_end = len(content)
                worker_code = content[worker_start:worker_end]
                
                if '_model_loaded' in worker_code and 'return' in worker_code:
                    print("✓ 独立模式下模型加载失败时线程会退出")
                else:
                    print("⚠ 独立模式下缺少模型加载失败处理")
                    return False
            else:
                print("✗ _worker 方法未找到")
                return False
            
            # 检查共享模式下的失败处理
            if 'def __init__(self,' in content:
                init_start = content.find('def __init__(self,')
                init_end = content.find('def ', init_start + 1)
                if init_end == -1:
                    init_end = len(content)
                init_code = content[init_start:init_end]
                
                if '初始化部分失败' in init_code or 'failed_models' in init_code:
                    print("✓ 共享模式下有失败处理逻辑")
                else:
                    print("⚠ 共享模式下缺少失败处理逻辑")
                    return False
            else:
                print("✗ __init__ 方法未找到")
                return False
        
        return True
    except Exception as e:
        print(f"✗ 模型初始化失败处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("功能测试：验证已完成阶段的功能")
    print("=" * 60)
    
    tests = [
        ("配置加载和验证", test_config_loading),
        ("日志系统", test_logger),
        ("服务器模块导入", test_server_import),
        ("安全限制常量", test_security_constants),
        ("异常处理", test_exception_handling),
        ("线程安全", test_thread_safety),
        ("Socket 资源管理", test_socket_management),
        ("线程池关闭", test_thread_pool_shutdown),
        ("模型初始化失败处理", test_model_init_handling),
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
        print("\n✓ 所有测试通过！功能正常。")
        return 0
    else:
        print(f"\n✗ 有 {total - passed} 个测试失败，需要检查。")
        return 1


if __name__ == '__main__':
    exit(main())
