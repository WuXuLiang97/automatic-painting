import psutil
import ntplib
from datetime import datetime, timedelta


def get_identity_mark():
    mac_addresses = []
    for interface, info in psutil.net_if_addrs().items():
        for addr in info:
            if addr.family == psutil.AF_LINK:
                mac_addresses.append(addr.address)
    # 去除短横线
    mac = '20190213' + mac_addresses[0]
    mac = mac.replace("-", "")
    # 如果你想去除字符串中所有的空格，包括中间的，可以使用replace()方法
    mac = mac.replace(" ", "")
    # print(mac)
    # 取出奇数位置的字符
    odd_position_chars = [char for index, char in enumerate(mac) if index % 2 != 0]

    # 将字符列表转换为字符串
    identity_mark = ''.join(odd_position_chars)
    # print(identity_mark)
    return identity_mark


def get_network_time():
    client = ntplib.NTPClient()
    try:
        # time.windows.com
        # response = client.request('pool.ntp.org')  # 使用公共NTP服务器，也可以替换为其他可信的NTP服务器
        response = client.request('time.windows.com')  # 使用公共NTP服务器，也可以替换为其他可信的NTP服务器
        network_time = datetime.fromtimestamp(response.tx_time)

        timestamp = str(network_time)
        # 使用split(".")分割字符串，并只取第一部分（小数点前的部分）
        new_timestamp = timestamp.split(".")[0]
        # print(new_timestamp)
        return new_timestamp
    except ntplib.NTPException as e:
        print(f"网络错误：无法从NTP服务器获取时间。{e}")
        return None


def add_days_to_datetime(datetime_str, days_to_add):
    # 将字符串转换为datetime对象
    dt_object = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')

    # 使用timedelta添加指定的天数
    new_dt_object = dt_object + timedelta(days=days_to_add)

    # 将新的datetime对象转换回字符串格式
    new_datetime_str = new_dt_object.strftime('%Y-%m-%d %H:%M:%S')

    return new_datetime_str


# # 示例用法
# original_datetime = "2024-04-06 10:09:42"
# days_to_add = 7
# new_datetime = add_days_to_datetime(original_datetime, days_to_add)
# # print(new_datetime)  # 输出：2024-04-13 10:09:42
# registration_code = get_identity_mark() + str(new_datetime)
# print(registration_code)

# print(get_identity_mark())
# print(get_network_time())
# registration_code = get_identity_mark() + get_network_time()
# print(registration_code)

# # 打印MAC地址
# for mac in mac_addresses:
#     print(mac)
