from __future__ import annotations

import os
from dataclasses import asdict, dataclass, replace
from typing import Optional, Dict, Any

from dotenv import load_dotenv


# Load environment variables from the project root .env if present
load_dotenv(override=False)


# In-memory, hot-reloadable LLM config
@dataclass(frozen=True)
class LLMConfig:
    base_url: str = os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234/v1")
    model: str = os.getenv("LLM_MODEL", "gpt-oss:latest")
    api_key: Optional[str] = os.getenv("LLM_API_KEY") or None
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.5"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
    request_timeout_seconds: float = float(os.getenv("LLM_REQUEST_TIMEOUT", "60"))


@dataclass(frozen=True)
class SecurityConfig:
    control_token: str = os.getenv("FTG_CONTROL_TOKEN", "changeme_local_token")


_LLM_CONFIG: LLMConfig = LLMConfig()


@dataclass(frozen=True)
class BotConfig:
    auto_reply_enabled: bool = (os.getenv("BOT_AUTO_REPLY_ENABLED", "0") == "1")
    auto_reply_mode: str = os.getenv("BOT_AUTO_REPLY_MODE", "off")  # off|mentions_only|all
    allowlist_chats: tuple[str, ...] = tuple(
        [x.strip() for x in (os.getenv("BOT_ALLOWLIST_CHATS", "").split(",") if os.getenv("BOT_ALLOWLIST_CHATS") else []) if x.strip()]
    )
    blocklist_chats: tuple[str, ...] = tuple(
        [x.strip() for x in (os.getenv("BOT_BLOCKLIST_CHATS", "").split(",") if os.getenv("BOT_BLOCKLIST_CHATS") else []) if x.strip()]
    )
    silent_reading: bool = (os.getenv("BOT_SILENT_READING", "1") == "1")
    min_reply_interval_seconds: int = int(os.getenv("BOT_MIN_REPLY_INTERVAL", "5"))
    reply_prompt: str = os.getenv("BOT_REPLY_PROMPT", "")
    # Humanize options
    humanize_typing_enabled: bool = (os.getenv("BOT_HUMANIZE_TYPING", "1") == "1")
    typing_min_ms: int = int(os.getenv("BOT_TYPING_MIN_MS", "800"))
    typing_max_ms: int = int(os.getenv("BOT_TYPING_MAX_MS", "2500"))
    typo_rate: float = float(os.getenv("BOT_TYPO_RATE", "0.0"))
    # Memory
    memory_enabled: bool = (os.getenv("BOT_MEMORY_ENABLED", "1") == "1")
    memory_window_messages: int = int(os.getenv("BOT_MEMORY_WINDOW", "6"))
    memory_max_chars: int = int(os.getenv("BOT_MEMORY_MAX_CHARS", "4000"))


_BOT_CONFIG: BotConfig = BotConfig()


def get_llm_config() -> LLMConfig:
    return _LLM_CONFIG


def update_llm_config(**kwargs: Any) -> LLMConfig:
    global _LLM_CONFIG
    # filter allowed fields
    allowed = {k: v for k, v in kwargs.items() if k in LLMConfig().__dict__}
    _LLM_CONFIG = replace(_LLM_CONFIG, **allowed)
    return _LLM_CONFIG


def llm_config_dict(redact_api_key: bool = True) -> Dict[str, Any]:
    d = asdict(_LLM_CONFIG)
    if redact_api_key and d.get("api_key"):
        d["api_key"] = "***"
    return d


def get_security_config() -> SecurityConfig:
    return SecurityConfig()


def get_bot_config() -> BotConfig:
    return _BOT_CONFIG


def update_bot_config(**kwargs: Any) -> BotConfig:
    global _BOT_CONFIG
    allowed_fields = set(BotConfig().__dict__.keys())
    filtered: Dict[str, Any] = {k: v for k, v in kwargs.items() if k in allowed_fields}
    # convert lists to tuples for immutability
    if "allowlist_chats" in filtered and isinstance(filtered["allowlist_chats"], list):
        filtered["allowlist_chats"] = tuple(filtered["allowlist_chats"])  # type: ignore[assignment]
    if "blocklist_chats" in filtered and isinstance(filtered["blocklist_chats"], list):
        filtered["blocklist_chats"] = tuple(filtered["blocklist_chats"])  # type: ignore[assignment]
    _BOT_CONFIG = replace(_BOT_CONFIG, **filtered)
    return _BOT_CONFIG


def bot_config_dict() -> Dict[str, Any]:
    return asdict(_BOT_CONFIG)

import os
def env(n,d=None):
    v=os.getenv(n); return v if v is not None else d
