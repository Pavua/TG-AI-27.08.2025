from __future__ import annotations

import os
import signal
import subprocess
import time
from collections import deque
from pathlib import Path
from typing import Deque, Dict

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from ..utils.config import (
    get_security_config,
    llm_config_dict,
    update_llm_config,
    get_bot_config,
    update_bot_config,
    bot_config_dict,
)
from ..utils.llm_client import chat as llm_chat
from .schemas import (
    ChatPayload,
    ExecRequest,
    LLMChatRequest,
    SendMessageRequest,
    LLMConfigPayload,
    LLMProviderInfo,
    BotConfigPayload,
)


app = FastAPI()

def require_token(x_ftg_token: str | None = Header(default=None, alias="X-FTG-Token")) -> str:
    # Load latest token each request to allow hot changes via .env
    sec = get_security_config()
    if x_ftg_token != sec.control_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_ftg_token


# very simple in-memory rate limiter: key -> deque[timestamps]
_rate_window_seconds: int = 2
_rate_max_requests: int = 10
_rate_state: Dict[str, Deque[float]] = {}


def rate_limit(request: Request):
    key = request.client.host if request.client else "local"
    now = time.time()
    dq = _rate_state.setdefault(key, deque())
    while dq and now - dq[0] > _rate_window_seconds:
        dq.popleft()
    dq.append(now)
    if len(dq) > _rate_max_requests:
        raise HTTPException(status_code=429, detail="Too Many Requests")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    rate_limit(request)
    try:
        response = await call_next(request)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    return response


@app.get("/health")
async def health(_: str = Depends(require_token)):
    return {"status": "ok", "ftg": "running"}


@app.get("/")
async def root(_: str = Depends(require_token)):
    return {"name": "FTG Control Server", "status": "ok"}


_ROOT_DIR = Path(__file__).resolve().parents[2]
_PID_FILE = _ROOT_DIR / "ftg/ftg_runner.pid"

# Temporary auth store for generating Pyrogram string sessions
_AUTH_STORE: Dict[str, Dict[str, str]] = {}


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _read_pid() -> int | None:
    if not _PID_FILE.exists():
        return None
    try:
        pid = int(_PID_FILE.read_text().strip())
        return pid if _is_pid_alive(pid) else None
    except Exception:
        return None


def _write_pid(pid: int) -> None:
    _PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PID_FILE.write_text(str(pid))


def _start_ftg() -> Dict[str, str | bool]:
    if _read_pid():
        return {"ok": False, "error": "already_running"}
    # Ensure session string exists to avoid interactive prompts which suspend the server
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(_ROOT_DIR / ".env")
    except Exception:
        pass
    if not (os.getenv("TELEGRAM_STRING_SESSION") or os.getenv("SESSION_STRING") or os.getenv("STRING_SESSION")):
        return {"ok": False, "error": "missing_telegram_session"}
    env = os.environ.copy()
    # Prevent interactive prompts when started from server
    env["NON_INTERACTIVE"] = "1"
    proc = subprocess.Popen(  # noqa: S603
        ["bash", "ftg/run_ftg.sh"],
        cwd=str(_ROOT_DIR),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    _write_pid(proc.pid)
    return {"ok": True, "started": True}


def _stop_ftg() -> Dict[str, str | bool]:
    pid = _read_pid()
    if not pid:
        return {"ok": False, "error": "not_running"}
    try:
        os.kill(pid, signal.SIGTERM)
    except Exception:
        pass
    return {"ok": True, "stopped": True}


@app.post("/exec")
async def exec_action(payload: ExecRequest, _: str = Depends(require_token)):
    action = (payload.action or "").lower()
    if action == "status":
        return {"ok": True, "running": bool(_read_pid())}
    if action == "start":
        return _start_ftg()
    if action == "stop":
        return _stop_ftg()
    if action == "restart":
        _stop_ftg()
        time.sleep(0.5)
        return _start_ftg()
    return {"ok": False, "error": "unknown_action"}


@app.post("/send_message")
async def send_message(payload: SendMessageRequest, _: str = Depends(require_token)):
    """Send message via Pyrogram using the same session string as userbot.
    We use Pyrogram (not Telethon) because the stored session string is Pyrogram-compatible.
    """
    try:
        from pyrogram import Client  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Pyrogram not available: {exc}")

    api_id = int(os.getenv("API_ID") or os.getenv("TELEGRAM_API_ID") or 0)
    api_hash = os.getenv("API_HASH") or os.getenv("TELEGRAM_API_HASH") or ""
    string_session = (
        os.getenv("TELEGRAM_STRING_SESSION")
        or os.getenv("SESSION_STRING")
        or os.getenv("STRING_SESSION")
        or ""
    )
    if not api_id or not api_hash:
        raise HTTPException(status_code=400, detail="Missing TELEGRAM_API_ID/TELEGRAM_API_HASH")
    if not string_session:
        raise HTTPException(status_code=400, detail="Missing TELEGRAM_STRING_SESSION in .env")

    chat = payload.chat or "me"
    try:
        async with Client("ftg_ctrl", api_id=api_id, api_hash=api_hash, session_string=string_session, device_model="FTG-Companion") as app:  # type: ignore
            await app.send_message(chat, payload.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Send failed: {exc}")
    return {"ok": True}


@app.post("/llm/chat")
async def llm_chat_api(payload: LLMChatRequest, _: str = Depends(require_token)):
    text = await llm_chat(
        prompt=payload.prompt,
        system=payload.system,
        max_tokens=payload.max_tokens,
        temperature=payload.temperature,
    )
    return {"ok": True, "text": text}


@app.get("/llm/config")
async def llm_get_config(_: str = Depends(require_token)):
    return {"ok": True, "config": llm_config_dict(redact_api_key=True)}


@app.post("/llm/config")
async def llm_update_config(payload: LLMConfigPayload, _: str = Depends(require_token)):
    updated = update_llm_config(**{k: v for k, v in payload.model_dump(exclude_none=True).items()})
    return {"ok": True, "config": llm_config_dict(redact_api_key=True)}


@app.get("/llm/providers")
async def llm_list_providers(_: str = Depends(require_token)):
    providers = [
        LLMProviderInfo(id="lmstudio", name="LM Studio (local)", base_url="http://127.0.0.1:1234/v1"),
        LLMProviderInfo(id="openai", name="OpenAI", base_url="https://api.openai.com/v1"),
        LLMProviderInfo(id="groq", name="Groq", base_url="https://api.groq.com/openai/v1"),
        LLMProviderInfo(id="fireworks", name="Fireworks.ai", base_url="https://api.fireworks.ai/inference/v1"),
        LLMProviderInfo(id="openrouter", name="OpenRouter", base_url="https://openrouter.ai/api/v1"),
        LLMProviderInfo(id="ollama", name="Ollama (local)", base_url="http://127.0.0.1:11434/v1"),
    ]
    return {"ok": True, "providers": [p.model_dump() for p in providers]}


@app.get("/bot/config")
async def bot_get_config(_: str = Depends(require_token)):
    return {"ok": True, "config": bot_config_dict()}


@app.post("/bot/config")
async def bot_update_config(payload: BotConfigPayload, _: str = Depends(require_token)):
    update_bot_config(**{k: v for k, v in payload.model_dump(exclude_none=True).items()})
    return {"ok": True, "config": bot_config_dict()}


@app.get("/logs/tail")
async def logs_tail(lines: int = Query(200, ge=1, le=2000), _: str = Depends(require_token)):
    # Use absolute path to avoid CWD confusion when server launched from different folders
    log_path = _ROOT_DIR / "ftg.log"
    if not log_path.exists():
        return {"ok": True, "lines": []}
    result: Deque[str] = deque(maxlen=lines)
    with log_path.open("r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            result.append(line.rstrip("\n"))
    return {"ok": True, "lines": list(result)}
