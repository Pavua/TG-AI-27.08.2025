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
    request_timeout_seconds: float = float(os.getenv("LLM_REQUEST_TIMEOUT", "30"))


@dataclass(frozen=True)
class SecurityConfig:
    control_token: str = os.getenv("FTG_CONTROL_TOKEN", "changeme_local_token")


_LLM_CONFIG: LLMConfig = LLMConfig()


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

import os
def env(n,d=None):
    v=os.getenv(n); return v if v is not None else d
