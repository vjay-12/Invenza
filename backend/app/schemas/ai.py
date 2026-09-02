from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    tenant_id: Optional[str] = None
    stream: bool = False

class ToolInvocation(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    output: Optional[Any] = None

class ChatResponse(BaseModel):
    message: str
    tools_invoked: List[ToolInvocation] = Field(default_factory=list)
    sql_query_used: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
