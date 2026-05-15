from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from playwright.sync_api import sync_playwright, Playwright, Page
import json
import httpx
from bs4 import BeautifulSoup
from pathlib import Path
import time
from playwright_stealth import Stealth
import random





@dataclass(kw_only=True)
class Scraper():
    """
    爬虫基类，定义了通用的爬虫行为。
    """

    # 默认超时时间
    time_out: int = 30000

    # Playwright 实例
    _playwright_instance: Any = field(init=False, default=None)

    def random_delay(self):
        """
        产生一个正态分布的随机延迟，模拟人类行为。
        """
        # 确保延迟不为负数，至少 0.5 秒
        delay = max(0.5, random.gauss(2, 1))
        time.sleep(delay)

    def create_browser(self) -> Any:
        """
        创建一个带有隐身模式的浏览器实例。
        """
        self._playwright_instance = Stealth().use_sync(sync_playwright()).start()
        browser = self._playwright_instance.chromium.launch(headless=False)
        return browser

    def close_browser(self):
        """
        关闭 Playwright 实例。
        """
        if self._playwright_instance:
            self._playwright_instance.stop()
    
    
        

@dataclass(kw_only=True)    
class XhsScraper(Scraper):
    """
    小红书爬虫类，继承自 Scraper。
    """
    # 存储登录状态的文件路径
    file_path: Path | None = field(init=False)
    # Playwright 浏览器上下文
    context: Any  = field(init=False)
    # Playwright 页面对象
    page: Any = field(init=False, default=None)
    # browser
    browser: Any
    # user_name
    user_name: str | None = None

    
    def __post_init__(self):
        """
        初始化后的处理，设置文件路径并启动浏览器。
        """
        self.cookie_file_path()
        self.xhs_create_and_login()

    def cookie_file_path(self):
        par_dir = Path(__file__).resolve().parent
        target_dir = par_dir.parent / "auth" / "playwright"
        target_dir.mkdir(parents=True, exist_ok=True)            
        self.file_path = target_dir / f"xhs_info.json_{self.user_name}" if self.user_name else None

    def route_search_request(self, route, captured_data):
        """
        拦截搜索请求的回调函数，用于捕获请求头和参数。
        """
        captured_data["header"] = route.request.headers
        captured_data["url"] = route.request.url
        captured_data["method"] = route.request.method
        if route.request.method == "POST":
            captured_data["post_data"] = route.request.post_data
        route.abort()  # 阻止请求继续进行，避免不必要的流量消耗

    def route_user_name(self,route):
        """
        拦截用户名，用于第一次登录
        """
        data = route.fetch()
        data = data.json()
        self.user_name = data["data"]["nickname"]
        print(self.user_name)
        self.cookie_file_path()
        route.continue_()
    
    def xhs_create_and_login(self) -> None:
            """
            创建浏览器上下文并处理登录逻辑。
            """
            if self.file_path is None:
                print("未指定认证文件路径，使用无状态浏览器登录")
                self.context = self.browser.new_context()
            elif self.file_path.exists():
                print("找到认证文件，尝试使用存储状态登录")
                self.context = self.browser.new_context(storage_state=self.file_path)
            else:
                print("未找到认证文件，使用无状态浏览器登录")
                self.context = self.browser.new_context()
            self.page = self.context.new_page()
            self.page.goto("https://www.xiaohongshu.com/explore")
            print(self.page.title())
            # 检查是否需要手动登录
            self.page.wait_for_timeout(2000)
            if self.page.get_by_text("登录后推荐更懂你的笔记").is_visible():
                print("需要登录")
                self.page.route("**web/v2/user/me", lambda route: self.route_user_name(route))
                try:
                    # 等待搜索框可见，作为登录成功的标志（或者让用户有时间手动操作）
                    for _ in range(300):
                        if self.page.get_by_role("textbox", name="搜索小红书").is_visible():
                            break                
                        self.page.wait_for_timeout(100)  # 等待 100ms 后再次检查
                    else:
                        raise TimeoutError("超时")
                except TimeoutError as e:
                    print(f"登陆超时,msg{e}")
                else:
                    print("登录成功")
                    self.page.unroute("**web/v2/user/me")
                # 保存当前的登录状态到文件
                if self.file_path is not None:
                    self.context.storage_state(path=self.file_path)
            else:
                print("无需登录，本次未登录状态进行查询")

        

    def xhs_note_text_scrape(self, keyword: str) -> list[str]:
        """
        抓取指定关键词的小红书笔记文本。
        """
        return_list = []
        captured_data = {"header": {}, "url": "", "method": "", "post_data": None}

        # 确保浏览器已初始化且已登录
        if self.context is None or self.page is None:
            try:
                self.xhs_create_and_login()
            except TimeoutError as e:
                return [f"登录超时，msg:{e}"]

        # 在搜索框输入关键词
        self.page.get_by_role("textbox", name="搜索小红书").click()
        self.page.get_by_role("textbox", name="搜索小红书").fill(keyword)
        # 注册拦截器
        self.page.route(
            "**/api/sns/web/v1/search/notes",
            lambda route: self.route_search_request(route, captured_data)
            )
        # 点击搜索按钮
        self.page.get_by_role("img").nth(2).click()

        # 轮询等待请求被捕获
        found = False
        for _ in range(50):  # 最多等 5 秒 (50 * 0.1s)
            if captured_data["header"]:
                found = True
                print("成功捕获到搜索请求的包")
                break
            self.page.wait_for_timeout(100)  # 每次等 100ms
        
        if not found:
            print("超时了，还是没抓到包")
            return []

        # 使用捕获到的 Headers 进行模拟请求
        with httpx.Client(headers=captured_data["header"],http2=True) as client:
            try:
                response = client.request(
                    method=captured_data["method"],
                    url=captured_data["url"],
                    headers=captured_data["header"],
                    content=captured_data.get("post_data") # 针对 POST 自动处理
                    )
                response.raise_for_status()
                data = response.json()
                # 将搜索结果保存到本地 json
                with open("result.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except httpx.HTTPError as e:
                print(f"请求出错: {e}")
                return []
        
            # 提取笔记列表并进一步抓取详情
            items = data.get("data", {}).get("items", [])[:3]
            for item in items: 
                self.random_delay()  # 每次请求前随机等待，降低被封风险
                id = item["id"]
                print(f"笔记ID: {id}")
                token = item["xsec_token"]
                print(f"笔记Token: {token}")
                params={"xsec_token": token,
                        "xsec_source": "pc_search",
                        "source": "web_explore_feed",
                        }
                try:
                    # 获取笔记详情页内容
                    message = client.get(f"https://www.xiaohongshu.com/explore/{id}", params=params)
                    print(f"请求URL: {message.url}")
                    message.raise_for_status()
                except httpx.HTTPError as e:
                    print(f"请求笔记 {id} 时出错: {e}")
                    continue
                # 解析 HTML 提取 Meta 描述信息（通常包含笔记简介）
                soup = BeautifulSoup(message.text,"html.parser")
                tag = soup.find_all("meta",attrs={"name":"description"})
                if tag:
                    return_list.append(tag[0].get('content').strip())
        print(return_list)
        return return_list
    
    def __del__(self):
        """
        close context created, while keeping browser alive for potential reuse.
        """
        try:
            if hasattr(self, "context") and self.context:
                self.context.close()
        except Exception:
            pass


if __name__ == "__main__":
    # 测试代码
    play = Stealth().use_sync(sync_playwright()).start()
    brow = play.chromium.launch(headless=False)
    scraper = XhsScraper(browser=brow)
    notes = scraper.xhs_note_text_scrape("怀柔旅游攻略")
    print(notes)
    scraper.close_browser()
