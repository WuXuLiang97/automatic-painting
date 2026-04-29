from utils.screenshot_util import screenshot_util
from mm import MM

mm = MM()
x1, y1, x2, y2 = (899, 77, 964, 96)
min_img = screenshot_util.get_game_screenshot()[y1:y2, x1:x2]
mm.show_image(min_img)
ret = mm.is_colored(min_img, 50)
print(ret)
