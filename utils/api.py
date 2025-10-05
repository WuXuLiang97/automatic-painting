import time
import requests
import random
import hashlib
import json
from datetime import datetime, timedelta
import logging

# 基础配置
BASE_URL = "http://192.168.1.15:5001"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123456"
TEST_USERNAME = f"testuser{random.randint(1000, 9999)}"
TEST_PASSWORD = "testpassword123"


def hash_password(password):
    """使用SHA-256哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()


def print_response(response, description):
    """打印响应信息"""
    print(f"\n{description}")
    print(f"状态码: {response.status_code}")
    try:
        print("响应内容:", json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print("响应内容:", response.text)


def test_register(USERNAME, PASSWORD):
    """测试用户注册"""
    start = time.time()
    url = f"{BASE_URL}/register"
    data = {"username": USERNAME, "password": PASSWORD}
    response = requests.post(url, json=data)
    print_response(response, "测试用户注册")
    duration = time.time() - start
    logging.debug(f"注册测试耗时: {duration:.2f}秒")
    return response.json()


def test_login(USERNAME, PASSWORD):
    """测试用户登录"""
    start = time.time()
    url = f"{BASE_URL}/login"
    data = {"username": USERNAME, "password": PASSWORD}
    response = requests.post(url, json=data)
    print_response(response, "测试用户登录")

    if response.status_code == 200:
        # 保存会话token
        session_token = response.json().get('user', {}).get('username')
        logging.debug(f"登录成功! 用户: {session_token}")
        duration = time.time() - start
        logging.debug(f"登录测试耗时: {duration:.2f}秒")
        return response.cookies
    return None


def test_dashboard(cookies):
    """测试仪表盘信息"""
    start = time.time()
    url = f"{BASE_URL}/dashboard"
    response = requests.get(url, cookies=cookies)
    print_response(response, "测试仪表盘信息")
    duration = time.time() - start
    logging.debug(f"测试仪表盘信息耗时: {duration:.2f}秒")
    return response.json()


def test_create_subgroup(cookies, subgroup_name):
    """测试创建分组"""
    start = time.time()
    url = f"{BASE_URL}/subgroups"
    data = {"subgroup_name": subgroup_name}
    response = requests.post(url, json=data, cookies=cookies)
    print_response(response, f"测试创建分组 '{subgroup_name}'")
    duration = time.time() - start
    logging.debug(f"测试创建分组耗时: {duration:.2f}秒")
    return response.json()


def test_add_subgroup_config(cookies, subgroup_name, config_data):
    """测试添加分组配置"""
    start = time.time()
    url = f"{BASE_URL}/subgroups/{subgroup_name}/config"
    response = requests.post(url, json=config_data, cookies=cookies)
    print_response(response, f"测试添加分组配置到 '{subgroup_name}'")
    duration = time.time() - start
    logging.debug(f"测试添加分组配置耗时: {duration:.2f}秒")
    return response.json()


def test_copy_subgroup(cookies, source_subgroup_name, target_subgroup_name):
    """测试复制分组"""
    start = time.time()
    url = f"{BASE_URL}/subgroups/copy"
    # 复制分组
    copy_data = {
        "source_subgroup_name": source_subgroup_name,
        "target_subgroup_name": target_subgroup_name
    }
    response = requests.post(url, json=copy_data, cookies=cookies)
    print_response(response, f"测试复制分组到 '{target_subgroup_name}'")
    duration = time.time() - start
    logging.debug(f"测试复制分组耗时: {duration:.2f}秒")
    return response.json()


def test_view_subgroup_config(cookies, subgroup_name):
    """测试查看分组配置"""
    start = time.time()
    url = f"{BASE_URL}/subgroups/{subgroup_name}/config"
    response = requests.get(url, cookies=cookies)
    print_response(response, f"测试查看分组 '{subgroup_name}' 的配置")
    duration = time.time() - start
    logging.debug(f"测试查看分组配置耗时: {duration:.2f}秒")
    return response.json()


def test_view_subgroups(cookies):
    """测试查看分组配置"""
    start = time.time()
    url = f"{BASE_URL}/subgroups"
    response = requests.get(url, cookies=cookies)
    print_response(response, f"测试查看所有分组")
    duration = time.time() - start
    logging.debug(f"测试查看所有分组耗时: {duration:.2f}秒")
    return response.json()


def test_update_subgroup_config(cookies, subgroup_name, old_order, new_data):
    """测试更新分组配置"""
    start = time.time()
    url = f"{BASE_URL}/subgroups/{subgroup_name}/config/{old_order}"
    response = requests.put(url, json=new_data, cookies=cookies)
    print_response(response, f"测试更新分组配置 (刷图序号 {old_order})")
    duration = time.time() - start
    logging.debug(f"测试更新分组配置耗时: {duration:.2f}秒")
    return response.json()


def test_delete_subgroup_config(cookies, subgroup_name, brush_order):
    """测试删除分组配置"""
    url = f"{BASE_URL}/subgroups/{subgroup_name}/config/{brush_order}"
    response = requests.delete(url, cookies=cookies)
    print_response(response, f"测试删除分组配置 (刷图序号 {brush_order})")
    return response.json()


def test_change_password(cookies, old_password, new_password):
    """测试修改密码"""
    url = f"{BASE_URL}/change_password"
    data = {"old_password": old_password, "new_password": new_password}
    response = requests.post(url, json=data, cookies=cookies)
    print_response(response, "测试修改密码")
    return response.json()


def test_admin_users(cookies):
    """测试管理员查看用户"""
    url = f"{BASE_URL}/admin/users"
    response = requests.get(url, cookies=cookies)
    print_response(response, "测试管理员查看用户")
    return response.json()


def test_logout(cookies):
    """测试退出登录"""
    url = f"{BASE_URL}/logout"
    response = requests.get(url, cookies=cookies)
    print_response(response, "测试退出登录")
    return response.json()


def test_delete_subgroup(cookies, subgroup_name):
    """测试删除分组"""
    url = f"{BASE_URL}/subgroups/{subgroup_name}"
    response = requests.delete(url, cookies=cookies)
    print_response(response, f"测试删除分组 '{subgroup_name}'")
    return response.json()


def run_tests():
    """运行所有测试"""
    print(f"开始API测试，测试用户: {TEST_USERNAME}")

    # 测试用户注册
    if not test_register():
        logging.debug("用户注册测试失败!")
        return

    # 测试用户登录
    cookies = test_login()
    if not cookies:
        logging.debug("用户登录测试失败!")
        return

    # 测试仪表盘
    test_dashboard(cookies)

    # 测试创建分组
    subgroup_name = "测试分组"
    test_create_subgroup(cookies, subgroup_name)

    # 测试添加分组配置
    config_data = {"brush_order": 1, "career": "剑魂", "convert_career": "鬼泣", "height": 180, "map": "幽暗密林", "difficulty": "3", "leave_pl": 10, "brush_map_expire_time": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")}
    test_add_subgroup_config(cookies, subgroup_name, config_data)

    # 测试查看分组配置
    test_view_subgroup_config(cookies, subgroup_name)

    # 测试更新分组配置
    update_data = {"brush_order": 2,  # 修改刷图序号
                   "career": "狂战士", "convert_career": "阿修罗", "height": 175, "map": "洛兰深处", "difficulty": "4", "leave_pl": 5}
    test_update_subgroup_config(cookies, subgroup_name, 1, update_data)

    # 再次查看配置确认更新
    test_view_subgroup_config(cookies, subgroup_name)

    # 测试删除分组配置
    test_delete_subgroup_config(cookies, subgroup_name, 2)

    # 测试修改密码
    test_change_password(cookies)

    # 测试管理员功能（普通用户应无权限）
    test_admin_users(cookies)

    # 测试退出登录
    test_logout(cookies)

    # 测试管理员登录
    admin_data = {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}
    admin_response = requests.post(f"{BASE_URL}/login", json=admin_data)
    admin_cookies = admin_response.cookies
    print_response(admin_response, "管理员登录")

    # 测试管理员查看用户
    test_admin_users(admin_cookies)

    # 测试管理员删除分组
    test_delete_subgroup(admin_cookies, subgroup_name)

    # 测试管理员退出
    test_logout(admin_cookies)

    logging.debug("\n所有测试完成!")


if __name__ == "__main__":
    # run_tests()
    cookies = test_login('1457854270', '111222')
    test_copy_subgroup(cookies, '16号', '18号')
