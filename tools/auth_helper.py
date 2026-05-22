from PIL import Image
from io import BytesIO
from playwright.sync_api import Page, Locator
from typing import Callable, Any
from pathlib import Path
def edge_detection(image: Image.Image) -> int:
    width, height = image.size
    
    # 1. 规划高密度网格 (X 轴步长 4px, Y 轴步长 6px，交织成严密的雷达网)
    x_grid = list(range(int(width * 0.25), int(width * 0.85), 4))
    y_grid = list(range(int(height * 0.20), int(height * 0.80), 6))
    
    # 用来存放所有通过“空间连通性”审计的真缺口内部点
    confirmed_black_points = []
    
    # 定义一个快捷闭包：判断某个网格坐标点是不是黑的
    def is_black(px, py):
        if not (0 <= px < width and 0 <= py < height):
            return False
        r, g, b = image.getpixel((px, py))
        return ((r + g + b) / 3) < 90

    # 2. 二维邻域审计
    for x in x_grid:
        for y in y_grid:
            if is_black(x, y):
                # 💡 核心防御：检查上下左右的邻域节点（跨度设为 6px）
                neighbors = [
                    is_black(x, y - 6),  # 上
                    is_black(x, y + 6),  # 下
                    is_black(x - 4, y),  # 左
                    is_black(x + 4, y)   # 右
                ]
                
                # 只有周围至少有两个邻居也是黑的，才说明这里有“纵向和横向的厚度”
                if sum(neighbors) >= 2:
                    confirmed_black_points.append((x, y))
                    
    # 3. 统计中心轴
    if not confirmed_black_points:
        print("❌ [空间连通审计] 未能检测到任何具备二维厚度的点集。")
        return 0
        
    # 提取出所有过审点的 X 坐标
    all_valid_xs = [pt[0] for pt in confirmed_black_points]
    
    # 💡 再次利用你最爱的中位数/截尾平均数，直接干掉两端可能残留的细微扰动
    all_valid_xs.sort()
    
    # 砍掉头尾 10% 的极值，剩下的取平均数，这就是最完美的图形空间中心
    trim_size = max(1, len(all_valid_xs) // 10)
    core_xs = all_valid_xs[trim_size:-trim_size] if len(all_valid_xs) > 2 else all_valid_xs
    
    center_x = sum(core_xs) / len(core_xs)
    
    # 减去滑块左边到它自身中心的物理偏置（根据实际对齐情况微调，通常在 20-30 之间）
    target = int(center_x)
    
    print(f"🎯 [空间连通审计] 成功捕获 {len(confirmed_black_points)} 个连通核心点。")
    print(f"🎯 [二维质心锁定] 终极中心 X 坐标: {target} px")
    return target


def Tencent_auth(action: Callable[[], Any], page:Page) -> float:


    try:
        with page.expect_response("**cap_union_new_getcapbysig?img_index=1**", timeout = 5000) as img:
            action()
        backgroud_bytes = img.value.body()
    except:
        action()
        if "马蜂窝" in page.title():
            return 1
        print("timeout")
        return -1
   
    try:
        frame = page.frame_locator('iframe[name*="captcha.qq.com"]')
        frame.get_by_text("拖动下方滑块完成拼图").wait_for(state="visible", timeout=10000)
    except:
        print("等待验证码图片加载超时。")
        message = "超时"
        print(message)
        return -1
    print("验证码图片已加载，正在分析...")
    
    #获取在线验证码图片的宽度
    bg_element = frame.locator("#slideBg")
    bg_box = bg_element.bounding_box()

    #获取滑块位置
    slider = frame.locator("div[class*='tc-slider-normal']")
    slider_box = slider.bounding_box()
    if slider_box:
        print("找到滑块")
    if not bg_box or not slider_box:
        print("无法获取验证码背景图片的尺寸信息。")
        return -1
    width_online = bg_box["width"]
    background_image = Image.open(BytesIO(backgroud_bytes)).convert("RGB")
    width, height = background_image.size
    target = edge_detection(background_image)
    pixel = target*(width_online/width)
    
    print(f"在线验证码图片宽度：{width_online} px，原始图片宽度：{width} px，计算得到的缺口位置：{pixel:.2f} px")
    # 别直接 page.mouse.move 了，先让 Playwright 框架帮你精准悬停到滑块上
    

    start_x = slider_box["x"] + slider_box["width"] / 2
    start_y = slider_box["y"] + slider_box["height"] / 2
    offset = start_x - bg_box["x"]
    print(f"滑块中心位置：({start_x:.2f}, {start_y})")
    print(f"滑块起始偏移：{offset:.2f} px")
    to = pixel + start_x - offset
    print(f"目标位置：{to:.2f} px")
    with page.expect_response("**www.mafengwo.cn/WafCaptcha", timeout = 10000) as response:
        slider.hover()
        page.mouse.down()
        page.mouse.move(to , start_y, steps=30)
        page.mouse.up()
    if response.value.status == 200:
        print(f"成功验证，缺口位置：{pixel:.2f} px")
        return 0
    print("验证失败，尝试了多个位置但都未成功。")
    return -2
            

            

if __name__ == "__main__":
    path = Path(__file__).parent / "test.png"
    image = Image.open(path).convert("RGB")
    edge_detection(image)