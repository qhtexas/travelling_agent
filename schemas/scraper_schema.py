from pydantic import BaseModel, Field
from typing import Any, Literal

class XhsSearchInput(BaseModel):
    keyword: str = Field(..., description="搜索关键词")

class XhsSearchNoteResult(BaseModel):
    status: Literal["success", "error"] = Field(..., description="状态")
    data: list[str] = Field(..., description="搜索结果列表")





