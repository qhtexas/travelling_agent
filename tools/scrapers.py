from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from turtle import delay
from typing import List, Optional, Dict, Any
from playwright.sync_api import sync_playwright, Playwright, Page
import json
import httpx
from bs4 import BeautifulSoup
from pathlib import Path
import time
from playwright_stealth import Stealth
import random

from pytest_playwright.pytest_playwright import context, page

@dataclass(kw_only=True)
class Scraper(ABC):

    time_out: int = 30000

    _playwright_instance: Any = field(init=False, default=None)

    def random_delay(self):
        """
        产生一个正态分布的随机延迟
        mu: 平均等待时间
        sigma: 波动范围
        """
        # 确保延迟不为负数
        delay = max(0.5, random.gauss(2, 1))
        time.sleep(delay)

    def create_browser(self) -> Any:
        self._playwright_instance = Stealth().use_sync(sync_playwright()).start()
        browser = self._playwright_instance.chromium.launch(headless=False)
        return browser

    def close_browser(self):
        if self._playwright_instance:
            self._playwright_instance.stop()
        





@dataclass(kw_only=True)    
class XhsScraper(Scraper):
    file_path: Optional[Path] = field(init=False)
    context: Any = field(init=False, default=None)
    page: Any = field(init=False, default=None)
    browser: Any = field(init=False)
    
    def __post_init__(self):
        par_dir = Path(__file__).resolve().parent
        target_dir = par_dir.parent / "auth" / "playwright"
        target_dir.mkdir(parents=True, exist_ok=True)            
        self.file_path = target_dir / "xhs_info.json"
        self.browser = self.create_browser()
        self.xhs_create_and_login()


    def route_search_request(self, route, captured_data):
        captured_data["header"] = route.request.headers
        captured_data["url"] = route.request.url
        captured_data["method"] = route.request.method
        if route.request.method == "POST":
            captured_data["post_data"] = route.request.post_data
        route.abort()  # 阻止请求继续进行
    
    def xhs_create_and_login(self) -> None:

            if self.file_path is None:
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
            if self.page.get_by_text("登录后推荐更懂你的笔记").is_visible():
                print("需要登录")
                try:
                    self.page.get_by_role("textbox", name="搜索小红书").wait_for(state="visible", timeout=self.time_out)
                except:
                    print("等待登录超时")
                print("登录成功")
            self.context.storage_state(path=self.file_path)  

        

    def xhs_note_text_scrape(self, keyword: str) -> list[str]:
        return_list = []
        captured_data = {"header": {}, "url": "", "method": "", "post_data": None}

        if self.context is None or self.page is None:
            self.xhs_create_and_login()

        self.page.get_by_role("textbox", name="搜索小红书").click()
        self.page.get_by_role("textbox", name="搜索小红书").fill(keyword)
        self.page.route(
            "**/api/sns/web/v1/search/notes",
            lambda route: self.route_search_request(route, captured_data)
            )
        self.page.get_by_role("img").nth(2).click()

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
                 with open("result.json", "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            except httpx.HTTPError as e:
                print(f"请求出错: {e}")
                return []
        
            items = data.get("data", {}).get("items", [])
            for item in items: 
                self.random_delay()  # 每次请求前随机等待
                id = item["id"]
                print(f"笔记ID: {id}")
                token = item["xsec_token"]
                print(f"笔记Token: {token}")
                params={"xsec_token": token,
                    "xsec_source": "pc_search",
                   "source": "web_search_reslut_notes"
                    }
                try:
                    message = client.get(f"https://www.xiaohongshu.com/explore/{id}", params=params)
                    print(f"请求URL: {message.url}")
                    message.raise_for_status()  # 如果请求失败会抛出异常
                except httpx.HTTPError as e:
                    print(f"请求笔记 {id} 时出错: {e}")
                    continue
                soup = BeautifulSoup(message.text,"html.parser")
                tag = soup.find_all("meta",attrs={"name":"description"})
                if tag:
                    return_list.append(tag[0].get('content').strip())
        print(return_list)
        return return_list


if __name__ == "__main__":
    scraper = XhsScraper()
    notes = scraper.xhs_note_text_scrape("怀柔旅游攻略")
    print(notes)
    scraper.close_browser()



