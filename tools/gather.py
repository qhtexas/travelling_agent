from pathlib import Path
from playwright.sync_api import sync_playwright
import subprocess
# 导入原来的 scraper
import time
from PIL import Image
from io import BytesIO
subprocess.Popen([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--remote-debugging-port=9222",
    r"--user-data-dir=D:\U盘\dev\agent-dev\travelling_agent\tools\user_data", #让它自己存 Cookie 养号，别管它
    "--start-maximized"
])

play = sync_playwright().start()
browser = play.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]  # 获取第一个上下文
page = context.pages[0]  # 获取第一个页面
page.goto("https://www.mafengwo.cn/")  # 打开目标网站
time.sleep(5)  # 等待页面加载完成

for i in range(100):
    print(f"第 {i+1} 次爬取")
    with page.expect_response("**cap_union_new_getcapbysig?img_index=1**", timeout = 5000) as img:
            page.reload()  # 刷新页面，触发验证码请求
    backgroud_bytes = img.value.body()
    bytes = BytesIO(backgroud_bytes)
    image = Image.open(bytes)
    path = Path(__file__).parent / "gather" / f"captcha_{i+1}.png"
    path.mkdir(parents=True, exist_ok=True)  # 确保目录存在
    image.save(path, format="PNG")
    time.sleep(1)  # 等待一秒钟再进行下一次爬取