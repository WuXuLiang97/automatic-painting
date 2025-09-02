import datetime


def sort_points_by_x(points):
    """
    根据点的x坐标对一组点进行排序。

    参数:
        points (list): 一个包含点的列表，每个点都是一个具有x属性的对象。

    返回:
        list: 根据点的x坐标升序排序后的点列表。
    """
    # print(f"排列前points:{points}")
    # 使用sorted函数对points列表进行排序
    # key参数指定了一个函数，该函数用于从列表中的每个元素（这里是点）提取一个用于比较的关键字
    # 在这里，lambda函数 p: p.x 表示从每个点p中提取其x属性作为排序的关键字
    sorted_points = sorted(points, key=lambda x: x[0])
    # print(f"排列后sorted_points:{sorted_points}")
    # 返回排序后的点列表
    return sorted_points


def get_date():
    now = datetime.datetime.now()
    if now.hour < 6:
        previous_day = now - datetime.timedelta(days=1)
        return previous_day.strftime("%Y-%m-%d")
    else:
        return now.strftime("%Y-%m-%d")

