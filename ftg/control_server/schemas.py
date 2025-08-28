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


class BotConfigPayload(BaseModel):
    auto_reply_enabled: Optional[bool] = None
    auto_reply_mode: Optional[str] = Field(
        default=None, description="one of: off, mentions_only, all"
    )
    allowlist_chats: Optional[list[str | int]] = None
    blocklist_chats: Optional[list[str | int]] = None
    silent_reading: Optional[bool] = None
    min_reply_interval_seconds: Optional[int] = Field(default=None, ge=0)
    reply_prompt: Optional[str] = None
    humanize_typing_enabled: Optional[bool] = None
    typing_min_ms: Optional[int] = Field(default=None, ge=0)
    typing_max_ms: Optional[int] = Field(default=None, ge=0)
    typo_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
