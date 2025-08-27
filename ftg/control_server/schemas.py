from pydantic import BaseModel, Field
from typing import Any, Dict, Optional


class ChatPayload(BaseModel):
    prompt: str


class ExecRequest(BaseModel):
    action: str = Field(..., description="Action name, e.g. start, stop, restart, module_toggle")
    params: Dict[str, Any] | None = None


class SendMessageRequest(BaseModel):
    chat: str | int = Field(..., description="Username or numeric chat ID")
    text: str = Field(..., description="Message text to send")


class LLMChatRequest(BaseModel):
    prompt: str
    system: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class LLMConfigPayload(BaseModel):
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    request_timeout_seconds: Optional[float] = None


class LLMProviderInfo(BaseModel):
    id: str
    name: str
    base_url: str
