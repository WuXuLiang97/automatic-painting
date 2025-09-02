import cv2


def parse_pl(game_img):
    """
    如果这个和小于 100，函数返回 False，这可能意味着该位置的像素颜色相对较暗，可能不满足某种特定的条件（比如，可能是在检查一个特定的游戏元素是否可见，而较暗的颜色可能表示该元素被遮挡或不在视野中）。
    如果这个和大于或等于 100，函数返回 True，这可能表示该位置的像素颜色相对较亮，满足某种条件。
    @param game_img:
    @return: bool
    """
    (r, g, b) = game_img[715, 897]
    if r + g + b < 100:
        return False
    return True


def template_match(max_img, min_img):
    res = cv2.matchTemplate(max_img, min_img, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    if max_val < 0.9:
        return None, None
    x, y = list(max_loc)
    return x, y
