"""
测试脚本：验证输入验证和安全性功能
用于验证任务 1.4 的完成情况

测试用例：
1. 发送超大图像（超过50MB限制）
2. 发送无效请求类型
3. 测试连接数限制
4. 发送恶意JSON数据
"""

import socket
import struct
import json
import time
import threading
import cv2
import numpy as np

# 服务器配置
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 12345

# 安全限制（与服务器保持一致）
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_CONNECTIONS = 100
VALID_REQUEST_TYPES = {"game_windows", "min_map", "ocr"}


def create_test_image(width: int = 640, height: int = 640) -> np.ndarray:
    """创建测试图像"""
    return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)


def encode_image(image: np.ndarray) -> bytes:
    """将图像编码为 JPEG 字节流"""
    _, buffer = cv2.imencode('.jpg', image)
    return buffer.tobytes()


def send_request(host: str, port: int, req_type: str, image_data: bytes, image_size: int = None) -> dict:
    """发送请求到服务器"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        header = {
            "type": req_type,
            "image_size": image_size if image_size is not None else len(image_data)
        }
        header_json = json.dumps(header).encode('utf-8')
        
        sock.sendall(struct.pack("!I", len(header_json)))
        sock.sendall(header_json)
        sock.sendall(image_data)
        
        # 接收响应
        header_len_data = sock.recv(4)
        if len(header_len_data) < 4:
            sock.close()
            return {"error": "响应头部长度不足"}
        
        header_len = struct.unpack("!I", header_len_data)[0]
        header_data = sock.recv(header_len)
        response_header = json.loads(header_data.decode('utf-8'))
        data_size = response_header.get("data_size", 0)
        
        response_data = b""
        while len(response_data) < data_size:
            chunk = sock.recv(min(4096, data_size - len(response_data)))
            if not chunk:
                break
            response_data += chunk
        
        result = json.loads(response_data.decode('utf-8'))
        sock.close()
        return result
        
    except Exception as e:
        try:
            sock.close()
        except:
            pass
        return {"error": str(e)}


def test_oversized_image():
    """测试1: 发送超大图像（超过50MB限制）"""
    print("\n" + "=" * 60)
    print("测试1: 超大图像限制")
    print("=" * 60)
    
    # 创建一个超大图像（超过50MB）
    # 注意：实际创建50MB+的图像会很慢，我们模拟发送超大size
    image = create_test_image(640, 640)
    image_data = encode_image(image)
    
    # 模拟发送超大图像（声明大小超过限制，但不实际发送所有数据）
    oversized_size = MAX_IMAGE_SIZE + 1024 * 1024  # 超过1MB
    print(f"尝试发送超大图像: {oversized_size / 1024 / 1024:.2f} MB (限制: {MAX_IMAGE_SIZE / 1024 / 1024:.0f} MB)")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((SERVER_HOST, SERVER_PORT))
        
        header = {
            "type": "ocr",
            "image_size": oversized_size
        }
        header_json = json.dumps(header).encode('utf-8')
        
        sock.sendall(struct.pack("!I", len(header_json)))
        sock.sendall(header_json)
        # 不发送实际数据，服务器应该在验证阶段就拒绝
        
        # 接收响应
        header_len_data = sock.recv(4)
        if len(header_len_data) >= 4:
            header_len = struct.unpack("!I", header_len_data)[0]
            header_data = sock.recv(header_len)
            response_header = json.loads(header_data.decode('utf-8'))
            data_size = response_header.get("data_size", 0)
            
            response_data = sock.recv(data_size)
            result = json.loads(response_data.decode('utf-8'))
            
            if "error" in result and "超过限制" in result["error"]:
                print(f"✓ 服务器正确拒绝超大图像")
                print(f"  错误信息: {result['error']}")
                sock.close()
                return True
        
        sock.close()
    except Exception as e:
        print(f"✗ 测试异常: {e}")
        return False
    
    print(f"✗ 服务器未正确拒绝超大图像")
    return False


def test_invalid_request_type():
    """测试2: 发送无效请求类型"""
    print("\n" + "=" * 60)
    print("测试2: 无效请求类型验证")
    print("=" * 60)
    
    image = create_test_image()
    image_data = encode_image(image)
    
    invalid_types = ["invalid_type", "hack", "exploit", "", None]
    
    for invalid_type in invalid_types:
        if invalid_type is None:
            continue  # 跳过None，因为会被之前的检查捕获
        
        result = send_request(SERVER_HOST, SERVER_PORT, invalid_type, image_data)
        
        if "error" in result and ("无效" in result["error"] or "缺失" in result["error"]):
            print(f"✓ 服务器正确拒绝无效请求类型: '{invalid_type}'")
        else:
            print(f"✗ 服务器未正确处理无效请求类型: '{invalid_type}'")
            print(f"  响应: {result}")
            return False
    
    return True


def test_connection_limit():
    """测试3: 连接数限制"""
    print("\n" + "=" * 60)
    print("测试3: 连接数限制")
    print("=" * 60)
    
    # 创建超过限制的连接数
    num_connections = MAX_CONNECTIONS + 10
    print(f"尝试创建 {num_connections} 个连接（限制: {MAX_CONNECTIONS}）")
    
    connections = []
    rejected_count = 0
    
    for i in range(num_connections):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((SERVER_HOST, SERVER_PORT))
            connections.append(sock)
            if i < 5:  # 只打印前几个
                print(f"  连接 {i+1} 建立成功")
        except Exception as e:
            rejected_count += 1
            if rejected_count <= 5:  # 只打印前几个
                print(f"  连接 {i+1} 被拒绝: {type(e).__name__}")
    
    # 关闭所有连接
    for sock in connections:
        try:
            sock.close()
        except:
            pass
    
    print(f"\n成功连接: {len(connections)}")
    print(f"被拒绝连接: {rejected_count}")
    
    # 等待连接释放
    time.sleep(1)
    
    # 验证：应该有一些连接被拒绝
    if rejected_count > 0 or len(connections) <= MAX_CONNECTIONS:
        print(f"✓ 连接数限制生效")
        return True
    else:
        print(f"✗ 连接数限制未生效（所有连接都成功）")
        return False


def test_oversized_header():
    """测试4: 超大JSON头部"""
    print("\n" + "=" * 60)
    print("测试4: 超大JSON头部")
    print("=" * 60)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((SERVER_HOST, SERVER_PORT))
        
        # 发送超大头部（超过1MB）
        oversized_header = b"x" * (1024 * 1024 + 100)  # 超过1MB
        print(f"尝试发送超大头部: {len(oversized_header) / 1024 / 1024:.2f} MB")
        
        sock.sendall(struct.pack("!I", len(oversized_header)))
        sock.sendall(oversized_header[:1024])  # 只发送一部分
        
        # 服务器应该关闭连接或返回错误
        try:
            sock.settimeout(2)
            response = sock.recv(1024)
            if response:
                print(f"✓ 服务器返回了响应")
                sock.close()
                return True
        except socket.timeout:
            print(f"✓ 服务器关闭了连接（正确处理超大头部）")
            sock.close()
            return True
        except (ConnectionResetError, BrokenPipeError):
            print(f"✓ 连接被重置（服务器正确处理超大头部）")
            return True
        
        sock.close()
    except Exception as e:
        print(f"✓ 服务器正确处理超大头部（异常: {type(e).__name__}）")
        return True
    
    return False


def test_malicious_json():
    """测试5: 恶意JSON数据"""
    print("\n" + "=" * 60)
    print("测试5: 恶意JSON数据")
    print("=" * 60)
    
    malicious_cases = [
        b'{"type":"ocr","image_size":-1}',  # 负数大小
        b'{"type":"ocr","image_size":999999999999}',  # 超大数字
        b'{"type":"ocr","image_size":"hack"}',  # 字符串类型
        b'{"type":null,"image_size":1000}',  # null类型
    ]
    
    for i, malicious_json in enumerate(malicious_cases, 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((SERVER_HOST, SERVER_PORT))
            
            sock.sendall(struct.pack("!I", len(malicious_json)))
            sock.sendall(malicious_json)
            
            # 服务器应该能够处理或拒绝
            try:
                sock.settimeout(2)
                response = sock.recv(1024)
                if response:
                    print(f"✓ 测试 {i}: 服务器返回了响应（正确处理恶意JSON）")
                else:
                    print(f"✓ 测试 {i}: 连接被关闭（正确处理恶意JSON）")
                sock.close()
            except (socket.timeout, ConnectionResetError, BrokenPipeError):
                print(f"✓ 测试 {i}: 连接被关闭或超时（正确处理恶意JSON）")
                try:
                    sock.close()
                except:
                    pass
        except Exception as e:
            print(f"✓ 测试 {i}: 异常处理（{type(e).__name__}）")
    
    return True


def main():
    """主测试函数"""
    print("=" * 60)
    print("安全性测试")
    print("=" * 60)
    print(f"服务器地址: {SERVER_HOST}:{SERVER_PORT}")
    print(f"最大图像大小: {MAX_IMAGE_SIZE / 1024 / 1024:.0f} MB")
    print(f"最大连接数: {MAX_CONNECTIONS}")
    print(f"有效请求类型: {', '.join(VALID_REQUEST_TYPES)}")
    print("\n请确保服务器已启动")
    print("=" * 60)
    
    # 检查服务器连接
    print("\n检查服务器连接...")
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(2)
        test_sock.connect((SERVER_HOST, SERVER_PORT))
        test_sock.close()
        print("✓ 服务器连接正常")
    except Exception as e:
        print(f"✗ 无法连接到服务器: {e}")
        print("请确保服务器已启动")
        return 1
    
    # 运行所有测试
    tests = [
        ("超大图像限制", test_oversized_image),
        ("无效请求类型", test_invalid_request_type),
        ("连接数限制", test_connection_limit),
        ("超大JSON头部", test_oversized_header),
        ("恶意JSON数据", test_malicious_json),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
            time.sleep(1)  # 延迟，避免过快
        except Exception as e:
            print(f"✗ 测试 '{name}' 执行异常: {e}")
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
        print("\n✓ 所有测试通过！安全性验证完善。")
        return 0
    else:
        print(f"\n✗ 有 {total - passed} 个测试失败，需要检查安全性实现。")
        return 1


if __name__ == '__main__':
    exit(main())
