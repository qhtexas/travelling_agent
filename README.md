# Overview

**This is a project which will ultimately developed to a travel planning agent, which can crawl web pages automatically and generate a fascinating plan for you, and especially for you, since it will know what best suits your needs and maximize for that**

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

The agent.py now stores a super simple example of an agent(using OpenAI's API, and deepseek's model), which only has one tool for now from the scrapers.py, which is for catching the words from notes from 小红书(xiaohongshu), a Chinese social media famous for user-curated everyday contents of high quality.

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

       message.raise_for_status()  # 如果请求失败会抛出异常
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

The agent now is quite primitive, the declaration of tools, a primitive level of memory management, and an agent even without a loop. But I used a dispatcher any way,  for the architecture is designed with modularity in mind to support future scaling.

# My philosophy


As a Mathematics major who codes in my spare time, I prioritize logic and efficiency over standard boilerplate. Though talking about my philosophy seems a bit odd and smug, but what I thought, and how I reached these developing decisions during doing this project seems to, at least I hope, help someone.

---

# Changelog 

\[v 0.1.0]
- basic scraping of xiaohongshu
- basic capability for agent to sum up the resources

# TODO List

- add coockies to avoid login everytime
- increase robustness to tackle edge cases
- React loop of agent to further enhance agent capability