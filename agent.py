import os
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError, validate_call
from playwright.sync_api import sync_playwright
from tools import XhsScraper
from schemas import XhsSearchInput, XhsSearchNoteResult
load_dotenv()



client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY")
)



def search_xhs(data: str) -> list:
    try:
        input_data = XhsSearchInput.model_validate_json(data)
    except ValidationError as e:
        print(f"输入数据类型错误失败: {e}")
        return []

    scraper = XhsScraper()
    return_list = scraper.xhs_note_text_scrape(input_data.keyword)
    if return_list:
        return XhsSearchNoteResult(status="success", data=return_list).model_dump_json()
    else:
        return XhsSearchNoteResult(status="error", data=[]).model_dump_json()




tool = [
    {"type":"function",
     "function":{
                    "name":"search_xhs",
                    "description":"根据关键词，返回小红书上前五条笔记内容",
                    "parameters":{
                            "type":"object",
                            "properties":{
                            "keyword":{
                                "type":"string",
                                "description":"要查询的关键词，例如：怀柔旅游攻略"
                            }
                    },
                    "required":["keyword"],
                    "additionalProperties": False
                }
            }
        }

]

dispatcher = {
    "search_xhs": search_xhs
}

messages = []
messages.append({"role":"system","content":"你是一个乐于助人的助手，你只有在能不做任何猜测的情况下才能返回用户需要的信息，否则请你询问用户更多的信息来帮助你完成任务。"})
initial_request = input("AI助手上线！，你想聊些什么？")
messages.append({"role":"user","content":initial_request})

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
if response.choices[0].message.tool_calls:
    print("模型调用了工具函数，正在处理工具函数的调用结果...")
    messages.append(response_message)
    for tool_call in response_message.tool_calls:
        function_name = tool_call.function.name 
        function_to_call = dispatcher.get(function_name)

        if function_to_call:
            args = tool_call.function.arguments
            function_response = function_to_call(args)
        
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id, # 对应那张“便签”的ID
            "name": function_name,
            "content": function_response 
        })

        final_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream = True,
            tools=None
        )
    for chunk in final_response:
        chunk_message = chunk.choices[0].delta
        if chunk_message.content:
            print(chunk_message.content, end="", flush=True)
else:
    print(response_message.content)









