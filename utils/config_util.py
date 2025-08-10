import configparser
import datetime
import json
import os
import shutil

from root_path import root_path
from utils.common_util import get_date

run_path = os.path.join(root_path, "work_space")

# 拼接文件路径
ini_file_path = os.path.join('C:\\', "config.json")

config_path = 'C:\\work_space'  # C 盘上的目标文件夹路径


def get_settings_group():
    """
    获取设置组
    :return:
    """
    # 检查目标路径是否存在
    if not os.path.exists(config_path):
        # 如果不存在，则创建该路径及其所有必需的父目录
        os.makedirs(config_path)
    # 使用os.listdir列出目标路径下的所有文件和目录的名称
    # 在这里，我们假设只有目录才代表有效的设置组
    # 注意：如果目标路径下包含文件，它们也会被列在返回的列表中，这可能不是预期的行为
    # 如果需要只列出目录，可以使用os.scandir()配合os.path.isdir()进行过滤
    settings_group_list = os.listdir(config_path)

    # 返回设置组名称的列表
    # 注意：返回的列表可能包含非目录项（如文件），如果这是一个问题，需要进行额外的过滤
    return settings_group_list


def init_ui_ip():
    # 检查文件是否存在
    if not os.path.exists(ini_file_path):
        settings = {
            'ip': '',
        }
        with open(ini_file_path, 'w') as file:
            json.dump(settings, file, indent=4)

        print(f"{ini_file_path} 文件已创建。")
    else:
        # 文件已存在，可以执行其他操作或打印消息
        print(f"{ini_file_path} 文件已存在。")


init_ui_ip()


def release_folder():
    """
    释放整个文件夹
    """
    # 注意：这里我们使用 source_folder_path 和 c_drive_target_folder_path 代替单个文件路径
    source_folder_path = run_path  # 这里假设 config_path 实际上是源文件夹的路径
    c_drive_target_folder_path = config_path  # 目标文件夹路径
    # 检查源文件夹是否存在
    if os.path.isdir(source_folder_path):
        # 检查目标文件夹是否存在（注意这里是文件夹而不是文件）
        if not os.path.exists(os.path.join('C:\\', os.path.basename(source_folder_path))):
            try:
                # 使用 shutil.copytree() 复制整个文件夹
                shutil.copytree(source_folder_path, os.path.join('C:\\', os.path.basename(source_folder_path)))
                print("文件夹已成功复制到 C 盘：", os.path.join('C:\\', os.path.basename(source_folder_path)))
            except Exception as e:
                print(f"复制文件夹时出错: {e}")
        else:
            print("文件夹已经存在于目标位置，无需复制：", os.path.join('C:\\', os.path.basename(source_folder_path)))
    else:
        print("源文件夹不存在：", source_folder_path)


release_folder()


def set_ip(input_char):
    """把主机IP写入文件"""
    # config = configparser.ConfigParser()  # 创建配置解析器对象
    # config.read(ini_file_path)  # 确保加载了配置文件
    # config['config']['ip'] = input_char
    # 保存配置文件
    # with open(ini_file_path, 'w') as configfile:
    #     config.write(configfile)
    with open(ini_file_path, 'r') as file:
        settings = json.load(file)

    settings["ip"] = input_char
    with open(ini_file_path, 'w') as file:
        json.dump(settings, file, indent=4)


def get_gui_config():
    """获取主机IP"""
    try:
        with open(ini_file_path, 'r') as file:
            settings = json.load(file)
        gui_config = {
            'ip': settings.get("ip", ''),
            'yjs': settings.get("yjs", 0),
            'banzhuan': settings.get("banzhuan", 0),
            'vmware_ip': settings.get("vmware_ip", "127.0.0.1"),
            'vmware_prot': settings.get("vmware_prot", "5900"),
            'vmware_password': settings.get("vmware_password", ''),
        }
        return gui_config
    except FileNotFoundError:
        # 如果文件不存在，则使用默认设置
        pass
    except json.JSONDecodeError:
        # 如果文件存在但格式不正确，则使用默认设置并可能给出警告
        print("Warning: Config file is corrupted or not in JSON format.")
    # config = configparser.ConfigParser()  # 创建配置解析器对象
    # config.read(ini_file_path)  # 确保加载了配置文件
    # my_ip = config.get('config', 'ip', fallback='')
    # return my_ip


def get_all_role_settings(role_group_name):
    if role_group_name == "":
        return None
    role_settings_path = os.path.join(config_path, role_group_name + "/roles.ini")
    if not os.path.exists(role_settings_path):
        raise Exception("")
    config = configparser.ConfigParser()
    config.read(role_settings_path)
    role_settings = {}
    sections = config.sections()
    for section in sections:
        if config.get(section, "今日是否刷图") == "否":
            continue
        role_settings[section] = {
            "role_index": section,
            "role_occupation_type": config.get(section, "角色职业类型"),
            "role_occupation": config.get(section, "角色转职职业"),
            "height": config.get(section, "时装身高", fallback="0"),
            "map_name": config.get(section, "地图名称"),
            "map_level": config.get(section, "地图难度"),
            "is_brush": config.get(section, "今日是否刷图"),
            "is_daily_tasks": config.get(section, "是否完成每日"),
            "retain_pl": config.get(section, "保留疲劳"),
            "finished_time": config.get(section, "刷图完成时间")
        }
    return role_settings


def save_settings_group(settings_group_name):
    """
    创建一个包含特定配置信息的目录和配置文件。

    参数:
    settings_group_name (str): 设置组的名称，用于构建目录路径。
    """
    print(settings_group_name)
    # 构建设置组目录的完整路径
    settings_group_path = os.path.join(config_path, settings_group_name)
    # 检查设置组目录是否存在，如果不存在则创建它
    if not os.path.exists(settings_group_path):
        os.makedirs(settings_group_path)
        # 创建一个ConfigParser对象用于处理配置文件
        config = configparser.ConfigParser()
        # 计算昨天的日期
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        # 循环创建4个配置条目，每个条目都有相同的设置
        for i in range(1, 5):
            config[str(i)] = {
                "角色职业类型": "鬼剑士",
                "角色转职职业": "鬼剑士",
                "时装身高": "0",
                '地图名称': "流雨瀑布",
                "地图难度": "噩梦",
                "今日是否刷图": "是",
                "是否完成每日": "是",
                "保留疲劳": "0",
                "刷图完成时间": yesterday
            }
        # 打开（或创建）配置文件并写入配置信息
        with open(settings_group_path + '/roles.ini', 'w') as configfile:
            config.write(configfile)


def delete_settings_group(settings_group_name):
    """
    此函数用于删除指定名称的设置组及其包含的所有文件和子目录。

    :param settings_group_name: str，要删除的设置组的名称。
    """
    # 使用os.path.join将配置路径（config_path，该变量应在函数外部定义）和设置组名称连接起来，
    # 形成完整的设置组路径。
    settings_group_path = os.path.join(config_path, settings_group_name)

    # 检查设置组路径是否存在。
    if os.path.exists(settings_group_path):
        # 使用os.walk遍历设置组路径下的所有文件和子目录。
        # os.walk返回一个三元组(当前路径, 当前路径下的目录列表, 当前路径下的文件列表)。
        for root, dirs, files in os.walk(settings_group_path):
            # 遍历当前路径下的所有文件。
            for file in files:
                # 将当前文件路径（由当前遍历的根路径和文件名组成）连接起来。
                file_path = os.path.join(root, file)
                # 删除当前文件。
                os.remove(file_path)

        # 在删除完所有文件后，使用os.removedirs删除空的设置组目录。
        # 注意：os.removedirs只能删除空的目录树，如果目录不为空，删除操作将失败。
        # 由于前面已经删除了所有文件，所以这里可以安全地调用os.removedirs。
        os.removedirs(settings_group_path)


def save_role_settings(settings_group_name, role_settings):
    print(role_settings)
    settings_group_path = os.path.join(config_path, settings_group_name)
    if not os.path.exists(settings_group_path):
        os.makedirs(settings_group_path)
    config = configparser.ConfigParser()
    config.read(settings_group_path + '/roles.ini')
    section = role_settings['role_index']
    if not config.has_section(section):
        config.add_section(section)
    config.set(section, '角色职业类型', role_settings['role_occupation_type'])
    config.set(section, '角色转职职业', role_settings['role_occupation'])
    config.set(section, '时装身高', role_settings['height'])
    config.set(section, '地图名称', role_settings['map_name'])
    config.set(section, '地图难度', role_settings['map_level'])
    config.set(section, '今日是否刷图', role_settings['is_brush'])
    config.set(section, '是否完成每日', role_settings['is_daily_tasks'])
    config.set(section, '保留疲劳', role_settings['retain_pl'])
    config.set(section, '刷图完成时间', role_settings['finished_time'])
    with open(settings_group_path + '/roles.ini', 'w') as configfile:
        config.write(configfile)


def delete_role_settings(settings_group_name, role_settings):
    settings_group_path = os.path.join(config_path, settings_group_name)
    if not os.path.exists(settings_group_path):
        return
    config = configparser.ConfigParser()
    config.read(settings_group_path + '/roles.ini')
    section = role_settings['role_index']
    if config.has_section(section):
        config.remove_section(section)
    with open(settings_group_path + '/roles.ini', 'w') as configfile:
        config.write(configfile)


def delete_all_role_settings(settings_group_name):
    settings_group_path = os.path.join(config_path, settings_group_name)
    if not os.path.exists(settings_group_path):
        return
    config = configparser.ConfigParser()
    config.read(settings_group_path + '/roles.ini')
    sections = config.sections()
    for section in sections:
        config.remove_section(section)
    with open(settings_group_path + '/roles.ini', 'w') as configfile:
        config.write(configfile)


def update_role_brush_date(settings_group_name, role_index):
    settings_group_path = os.path.join(config_path, settings_group_name)
    if not os.path.exists(settings_group_path):
        return
    config = configparser.ConfigParser()
    config.read(settings_group_path + '/roles.ini')
    sections = config.sections()
    for section in sections:
        if section == role_index:
            config.set(section, '刷图完成时间', get_date())
            break
    with open(settings_group_path + '/roles.ini', 'w') as configfile:
        config.write(configfile)
