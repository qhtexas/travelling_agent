from pathlib import Path
from playwright.sync_api import sync_playwright
import subprocess
# 导入原来的 scraper
from scrapers import MFWScraper, XhsScraper
import time
subprocess.Popen([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--remote-debugging-port=9222",
    r"--user-data-dir=D:\U盘\dev\agent-dev\travelling_agent\tools\user_data", # 让它自己存 Cookie 养号，别管它
    "--start-maximized"
])
time.sleep(2) # 稳稳等 2 秒，确保浏览器完全启动并监听在 9222 端口上

class MockBrowser:
    """
    一个简单的包装器，将 BrowserContext 伪装成 Browser 对象。
    这样现有的 Scraper 调用 `self.browser.new_context()` 时，
    就会直接返回我们通过 `launch_persistent_context` 创建的上下文，而不会报错。
    """
    def __init__(self, context):
        self.context = context

    def new_context(self, **kwargs):
        # 忽略传入的 storage_state 等参数，直接复用持久化上下文
        return self.context

def main():
    play = sync_playwright().start()
    
    # 连接到通过 CDP 暴露的现有浏览器
    cdp_url = "http://localhost:9222"
    print(f"Connecting to browser via CDP at: {cdp_url}")
    browser = play.chromium.connect_over_cdp(cdp_url)
    
    # 获取已有的上下文（通常手动启动的浏览器只有一个 context）
    contexts = browser.contexts
    if contexts:
        context = contexts[0]
    else:
        context = browser.new_context()
    
    # 将 context 包装起来传给 scraper
    mock_browser = MockBrowser(context)
    
    print("----- 测试 MFWScraper -----")
    scraper = MFWScraper(browser=mock_browser)
    # 这将调用 MFWScraper 内部的逻辑，但实际上使用的是我们的持久化 context
    scraper.mfw_create_and_login()

    # 测试 XhsScraper (若需要可取消注释)
    # print("----- 测试 XhsScraper -----")
    # xhs_scraper = XhsScraper(browser=mock_browser)
    # notes = xhs_scraper.xhs_note_text_scrape("怀柔旅游攻略")
    # print(notes)

    print("测试完毕，请手动关闭浏览器或停止进程。")

if __name__ == "__main__":
    main()
