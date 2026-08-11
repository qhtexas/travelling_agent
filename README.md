# Overview

**This is a project which will ultimately developed to a travel planning agent, which can crawl web pages automatically and generate a fascinating plan for you, and especially for you, since it wil[...]

But for now, it is at the early stage, so my focus now is primarily on **web scraper tools developing**, not maximizing the capability of the agent.

Some json and html files I grabbed during developing and some my personal notes/writings can be seen under the /doc directory, as one may find them useful.

# Getting Started

1. **Environment**: Python 3.10+
2. **Install Dependencies**: `pip install playwright httpx beautifulsoup4 openai`
3. **Setup Playwright**: `playwright install chromium`
4. **Configuration**: Add your `OPENAI_API_KEY` to `.env.example`, and remove the .example at the end of the name
5. if you use Openai or other's api, please change the url and name of api key follow their norms.
# The structure

The repo now has 1 directory and 1 file, which looks like this:

```text
travelling_agent/
├── agent.py           # Core Logic: LLM Dispatcher & Memory
├── tools/             
│   ├── __init__.py    # Package Initializer
│   └── scrapers.py    # Multi-engine Scraper (Playwright + httpx)
└── docs/              # Research notes & HTML samples
	
```

The agent.py now stores a super simple example of an agent(using OpenAI's API, and deepseek's model), which only has one tool for now from the scrapers.py, which is for catching the words from not[...]

# The scraper workflow

For my scraper codes(though only 1 function for now), I combined `playwright` and `httpx`.


Playwright is used to get the response packet from xiaohongshu, and use the dynamic tokens inside the json to get access to the note's detailed view, which is achieved as follows:

```python
        with page.expect_response(re.compile(r".*api/sns/web/v1/search/notes")) as response_info:

            page.get_by_role("img").nth(2).click()

            data = response_info.value.json()
            
```
A regular expression is employed to intercept the specific JSON response containing the target data.

And after getting the token we need, using httpx directly **without any special constructing**, through the easiest request we can compose we can get the raw html:
```python
try:

			    message=httpx.get(f"https://www.xiaohongshu.com/explore/{id}",params=params)

        print(f"请求URL: {message.url}")

       message.raise_for_status()  # 如果请求失败会抛出异常
except httpx.HTTPError as e:

       print(f"请求笔记 {id} 时出错: {e}")

       continue
```

And after inspecting the raw file, I used `BeautifulSoup` to snatch the piece of notes inside it, which is in a <meta> tag:
```python
soup = BeautifulSoup(message.text,"html.parser")

tag = soup.find_all("meta",attrs={"name":"description"})

if tag:

      return_list.append(tag[0].get('content').strip())
```

Then, the grabbed pieces of text are wrapped in a list and returned.

# The agent workflow

The agent now is quite primitive, the declaration of tools, a primitive level of memory management, and an agent even without a loop. But I used a dispatcher any way,  for the architecture is desi[...]

# My philosophy


As a Mathematics major who codes in my spare time, I prioritize logic and efficiency over standard boilerplate. Though talking about my philosophy seems a bit odd and smug, but what I thought, and[...]

---

# Changelog 

[v 0.1.0]
- basic scraping of xiaohongshu
- basic capability for agent to sum up the resources

# TODO List

- add coockies to avoid login everytime
- increase robustness to tackle edge cases
- React loop of agent to further enhance agent capability

---

# README — 简体中文

下面是本项目 README 的简体中文翻译，保留了原始的代码块与文件结构说明：

# 概述

**这是一个最终将开发为旅行规划代理（agent）的项目，该代理可以自动抓取网页并为你生成个性化的旅行计划。**

但目前项目仍处于早期阶段，所以作者主要关注的是**网页爬虫工具的开发**，而不是立即将代理的全部能力实现完备。

在 /doc 目录下可以看到开发过程中抓取的一些 json 和 html 文件，以及作者的个人笔记/写作，可能会对你有用。

# 快速开始

1. **环境**：Python 3.10+
2. **安装依赖**：`pip install playwright httpx beautifulsoup4 openai`
3. **设置 Playwright**：`playwright install chromium`
4. **配置**：将你的 `OPENAI_API_KEY` 添加到 `.env.example`，并去掉文件名末尾的 `.example`
5. 如果你使用 OpenAI 或其他第三方的 API，请按其规范修改 API 的 URL 以及 API key 的变量名。

# 项目结构

仓库当前包含 1 个目录和 1 个文件，结构如下：

```text
travelling_agent/
├── agent.py           # 核心逻辑：LLM 调度器 & 内存
├── tools/             
│   ├── __init__.py    # 包初始化器
│   └── scrapers.py    # 多引擎爬虫（Playwright + httpx）
└── docs/              # 研究笔记 & HTML 示例
```

agent.py 目前存放了一个非常简单的代理示例（使用 OpenAI 的 API 和 deepseek 的模型），当前只包含来自 scrapers.py 的一个工具，用于从笔记中抓取文字内容。

# 爬虫工作流程

在爬虫实现上，作者将 `playwright` 与 `httpx` 结合使用。

Playwright 用于捕获小红书（xiaohongshu）的响应包，并从 JSON 中提取动态 token，以访问笔记详情页，示例代码如下：

```python
        with page.expect_response(re.compile(r".*api/sns/web/v1/search/notes")) as response_info:

            page.get_by_role("img").nth(2).click()

            data = response_info.value.json()
```

使用正则表达式拦截包含目标数据的特定 JSON 响应。

在获取必要的 token 后，直接使用 `httpx`（无需复杂构造），通过最简单的请求就能获取到原始 HTML：

```python
try:
    message = httpx.get(f"https://www.xiaohongshu.com/explore/{id}", params=params)
    print(f"请求URL: {message.url}")
    message.raise_for_status()  # 如果请求失败会抛出异常
except httpx.HTTPError as e:
    print(f"请求笔记 {id} 时出错: {e}")
    continue
```

随后使用 `BeautifulSoup` 从 HTML 中提取笔记的文本部分（位于 `<meta name="description">` 标签中）：

```python
soup = BeautifulSoup(message.text, "html.parser")

tag = soup.find_all("meta", attrs={"name": "description"})

if tag:
    return_list.append(tag[0].get('content').strip())
```

最后将抓取到的文本片段封装为列表并返回。

# 代理（agent）工作流程

当前的代理实现比较原始：声明了工具、实现了基础的内存管理，甚至没有完整的循环。但作者采用了调度器（dispatcher）架构以便将来扩展。

# 作者理念

作为一名业余写代码的数学专业人员，作者更注重逻辑与效率而非模板化的样板代码。虽然谈论理念显得有些奇怪或自负，但这些是作者的编程与设计原则。

---

# 变更日志

[v 0.1.0]
- 对小红书的基础爬取
- 代理对资源做基本汇总的能力

# 待办事项

- 添加 cookies 支持以避免每次登录
- 提高鲁棒性以处理边缘情况
- 为 agent 添加循环以进一步增强其能力
