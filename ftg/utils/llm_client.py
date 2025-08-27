from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from .config import get_llm_config
from .text import trim


class LLMClientError(Exception):
    pass


def _build_messages(user_prompt: str, system: Optional[str]) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_prompt})
    return messages


async def chat(
    prompt: str,
    system: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> str:
    cfg = get_llm_config()
    # Heuristic: normalize LM Studio base URL to include /v1
    base = cfg.base_url.rstrip("/")
    parsed = urlparse(base)
    is_lmstudio = any(h in (parsed.netloc or "") for h in ("127.0.0.1:1234", "localhost:1234", "192.168.0.171:1234"))
    if is_lmstudio and not parsed.path.endswith("/v1"):
        base = base + "/v1"

    model_id = cfg.model
    # If model doesn't look like a full id for LM Studio, try to resolve via /models
    if is_lmstudio and "/" not in model_id:
        try:
            async with httpx.AsyncClient(timeout=min(10.0, cfg.request_timeout_seconds)) as client:
                r = await client.get(f"{base}/models")
                r.raise_for_status()
                models = (r.json() or {}).get("data", [])
                # Try exact/contains match first, else take first available
                found = None
                for m in models:
                    mid = m.get("id") or m.get("model")
                    if not mid:
                        continue
                    if model_id.lower() in mid.lower():
                        found = mid; break
                if not found and models:
                    found = (models[0].get("id") or models[0].get("model"))
                if found:
                    model_id = found
        except Exception:
            # ignore discovery errors, fall back to cfg.model
            pass

    payload: Dict[str, Any] = {
        "model": model_id,
        "messages": _build_messages(prompt, system),
        "max_tokens": int(max_tokens if max_tokens is not None else cfg.max_tokens),
        "temperature": float(temperature if temperature is not None else cfg.temperature),
        "stream": False,
    }

    headers: Dict[str, str] = {}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"

    url = f"{base}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=cfg.request_timeout_seconds) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException as exc:
        raise LLMClientError("LLM request timed out") from exc
    except httpx.HTTPError as exc:
        raise LLMClientError(f"LLM HTTP error: {exc}") from exc
    except Exception as exc:  # pragma: no cover - safety net
        raise LLMClientError("Unexpected LLM error") from exc

    # Support both Chat and old Completions schemas
    choices = (data.get("choices") or [])
    content: str = ""
    if choices:
        first = choices[0] or {}
        content = (first.get("message") or {}).get("content") or first.get("text") or ""
    return trim(content)

