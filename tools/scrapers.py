from playwright.sync_api import sync_playwright
import re
import json
import httpx
from bs4 import BeautifulSoup


def xhs_scraper(keyword: str)-> list:
    return_list = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://www.xiaohongshu.com/explore")
        print(page.title())
        if page.get_by_text("登录后推荐更懂你的笔记").is_visible():
            print("需要登录")
            page.wait_for_timeout(30000)  # wait for scan QR code to login
        page.get_by_role("textbox", name="搜索小红书").click()
        page.get_by_role("textbox", name="搜索小红书").fill(keyword)
        with page.expect_response(re.compile(r".*api/sns/web/v1/search/notes")) as response_info:# use this to capture the response packet
            page.get_by_role("img").nth(2).click()
        data = response_info.value.json()
        for i in range(5):# only get the first 5 notes
            id = data["data"]["items"][i]["id"]
            print(f"笔记ID: {id}")
            token = data["data"]["items"][i]["xsec_token"]
            print(f"用户Token: {token}")
            params={"xsec_token": token,
                    "xsec_source": "pc_search",
                   "source": "web_search_reslut_notes"
                    }
            try:
                message = httpx.get(f"https://www.xiaohongshu.com/explore/{id}",params=params)
                print(f"请求URL: {message.url}")
                message.raise_for_status()  # 如果请求失败会抛出异常
            except httpx.HTTPError as e:
                print(f"请求笔记 {id} 时出错: {e}")
                continue
            soup = BeautifulSoup(message.text,"html.parser")
            tag = soup.find_all("meta",attrs={"name":"description"})
            if tag:
                return_list.append(tag[0].get('content').strip())
        browser.close()   
    print(return_list)
    return return_list


     


if __name__ == "__main__":
    xhs_scraper()

