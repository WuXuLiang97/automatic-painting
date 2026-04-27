import requests
import json
import psutil


class ret_data:
    def __init__(self, data):
        response, msg, information = data
        self.response = response
        self.msg = msg
        self.information = information


def get_identity_mark():
    mac_addresses = []
    for interface, info in psutil.net_if_addrs().items():
        for addr in info:
            if addr.family == psutil.AF_LINK:
                mac_addresses.append(addr.address)
    # print(mac_addresses)
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


def send_request(f_program_version=None, state=1):
    # 定义请求的URL
    # url = 'http://39.98.46.105:5000/Information_dnf'
    url = 'https://autowxl.xyz/Information_dnf'

    # url = 'http://127.0.0.1:5000/Information'
    # 定义请求头
    headers = {'Content-Type': 'application/json'}

    id_value = get_identity_mark()
    # 定义POST请求的数据
    data = {'id': id_value, 'f_program_version': f_program_version, 'state': state}

    # 将数据转换为JSON格式
    json_data = json.dumps(data)

    # print(json_data)

    # 发送POST请求
    response = requests.post(url, headers=headers, data=json_data)

    # 打印响应状态码
    # print(response.status_code)

    # 打印响应内容
    # print(response.text)

    # 如果服务器返回的是JSON数据，你也可以将其转换为Python对象
    try:
        response_json = response.json()
        # print(response_json['result'])
        # print(response_json)
        ret_data = response.status_code, response_json['result'], response_json['information']

        return ret_data
    except ValueError:
        print("Response content is not JSON format.")


if __name__ == '__main__':
    get_identity_mark()
    print(send_request())
    import uuid

    # import psutil
    #
    #
    # def get_mac_addresses1():
    #     mac_addresses = []
    #     # 遍历网络接口
    #     for interface, snicstats in psutil.net_if_addrs().items():
    #         for snic in snicstats:
    #             # 检查是否是物理接口且包含MAC地址
    #             if snic.family == psutil.AF_LINK:
    #                 mac_addresses.append((interface, snic.address))
    #     return mac_addresses
    #
    #     # 打印所有物理接口的MAC地址
    #
    #
    # for interface, mac in get_mac_addresses1():
    #     print(f"Interface: {interface}, MAC: {mac}")
