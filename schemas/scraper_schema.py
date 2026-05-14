from pydantic import BaseModel, Field
from typing import Any, Literal

# 定义小红书搜索输入的 Schema
class XhsSearchInput(BaseModel):
    # 搜索关键词，必须提供
    keyword: str = Field(..., description="搜索关键词")

# 定义小红书搜索结果输出的 Schema
class XhsSearchNoteResult(BaseModel):
    # 执行状态，只能是 "success" 或 "error"
    status: Literal["success", "error"] = Field(..., description="状态")
    # 搜索到的笔记内容列表
    data: list[str] = Field(..., description="搜索结果列表")





