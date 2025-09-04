# 判断字符串是否为中文
def is_chinese(context):
    """
    检查整个字符串是否包含中文
    :param string: 需要检查的字符串
    :return: bool
    """
    for ch in context:
        if "\u4e00" <= ch <= "\u9fff":
            return True
    return False
