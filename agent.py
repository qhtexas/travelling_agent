# 导入必要的库
import os
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError, validate_call
from playwright.sync_api import sync_playwright
from tools import XhsScraper
from schemas import XhsSearchInput, XhsSearchNoteResult
from playwright_stealth import Stealth
import jsonref
from utils import generate_function_tool
_global_Playwright = None
_global_browser = None

_tools = []
def ini() -> None:
    global _global_browser, _global_Playwright, _tools
    if _global_browser is None:
        _global_Playwright = Stealth().use_sync(sync_playwright()).start()
        _global_browser = _global_Playwright.chromium.launch(headless=False)
        

# 加载环境变量
load_dotenv()

# 初始化 OpenAI 客户端，使用 DeepSeek 的 API 地址和密钥
client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY")
)



def search_xhs(data: str) -> list:
    """
    搜索小红书笔记的工具函数。
    
    参数:
        data (str): 包含搜索关键词的 JSON 字符串。
        
    返回:
        list: 返回小红书上前五条笔记内容的 JSON 字符串，如果出错则返回错误状态。
    """
    try:
        # 使用 Pydantic 验证并转换输入数据
        input_data = XhsSearchInput.model_validate_json(data)
    except ValidationError as e:
        print(f"输入数据类型错误失败: {e}")
        return []
    ini()
    # 实例化爬虫并抓取笔记内容
    scraper = XhsScraper(browser=_global_browser,user_name="。")
    try:
        return_list = scraper.xhs_note_text_scrape(input_data.keyword)
    except TimeoutError as e:
        return XhsSearchNoteResult(status="error",data=["login timeout",f"err_msg:{e}"])
    else:
        # 根据抓取结果返回相应的 JSON 响应
        if return_list:
            return XhsSearchNoteResult(status="success", data=return_list).model_dump_json()
        else:
            return XhsSearchNoteResult(status="error", data=[]).model_dump_json()

# 定义模型可调用的工具
tool = [
    generate_function_tool(
        name="search_xhs",
        description="根据关键词，返回小红书上前五条笔记内容",
        parameters=XhsSearchInput.model_json_schema()
    ),
    ]


# 工具分发器，将工具名称映射到对应的函数
dispatcher = {
    "search_xhs": search_xhs
}

# 初始化对话消息列表
messages = []
# 添加系统提示词
messages.append({"role":"system","content":"你是一个乐于助人的助手，你只有在能不做任何猜测的情况下才能返回用户需要的信息，否则请你询问用户更多的信息来帮助你完成任务。"})

# 获取用户初始请求
initial_request = input("AI助手上线！，你想聊些什么？")
messages.append({"role":"user","content":initial_request})

# 调用模型生成初步回复
response = client.chat.completions.create(
    model = "deepseek-chat",
    max_completion_tokens=200,
    messages=messages,
    tools=tool,
    tool_choice="auto",
    temperature = 0.2
)
response_message = response.choices[0].message
print(response.usage)
print("模型回复的内容：")

# 检查模型是否需要调用工具
if response.choices[0].message.tool_calls:
    print("模型调用了工具函数，正在处理工具函数的调用结果...")
    messages.append(response_message)
    
    # 遍历并处理每个工具调用
    for tool_call in response_message.tool_calls:
        function_name = tool_call.function.name 
        function_to_call = dispatcher.get(function_name)

        if function_to_call:
            args = tool_call.function.arguments
            function_response = function_to_call(args)
        
        # 将工具返回的结果添加到消息历史中
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id, # 对应那张“便签”的ID
            "name": function_name,
            "content": function_response 
        })

        # 再次调用模型，根据工具返回的结果生成最终回复
    final_response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream = True,
        tools=None        
    )
    
    # 流式输出模型回复
    for chunk in final_response:
        chunk_message = chunk.choices[0].delta
        if chunk_message.content:
            print(chunk_message.content, end="", flush=True)
else:
    # 如果没有工具调用，直接输出模型内容
    print(response_message.content)

_global_browser.close()
_global_Playwright.stop()








