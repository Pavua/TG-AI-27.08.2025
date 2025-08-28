from __future__ import annotations

import os
import signal
import subprocess
import time
from collections import deque
import asyncio
import time as _time
import contextlib
from pathlib import Path
from typing import Deque, Dict, Optional, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse

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


_UI_HTML = """
<!doctype html>
<html lang=\"ru\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>FTG Companion — Web Panel</title>
    <style>
      body { font-family: -apple-system, system-ui, sans-serif; margin: 16px; }
      input, button, select, textarea { font: inherit; padding: 6px 8px; }
      .row { margin: 8px 0; }
      .mono { font-family: ui-monospace, Menlo, Consolas, monospace; white-space: pre-wrap; }
    </style>
  </head>
  <body>
    <h2>FTG Companion — Web Panel</h2>
    <div class=\"row\">
      <label>Token: <input id=\"token\" type=\"password\" placeholder=\"X-FTG-Token\" /></label>
      <button onclick=\"saveToken()\">Save</button>
    </div>
    <hr>
    <h3>Exec</h3>
    <div class=\"row\">
      <button onclick=\"execAction('status')\">Status</button>
      <button onclick=\"execAction('start')\">Start</button>
      <button onclick=\"execAction('stop')\">Stop</button>
      <button onclick=\"execAction('restart')\">Restart</button>
    </div>
    <div id=\"execOut\" class=\"mono\"></div>
    <hr>
    <h3>LLM Test</h3>
    <div class=\"row\"><textarea id=\"prompt\" rows=\"3\" style=\"width:100%\" placeholder=\"Hello\"></textarea></div>
    <div class=\"row\"><button onclick=\"testLLM()\">/llm/chat</button></div>
    <div id=\"llmOut\" class=\"mono\"></div>
    <script>
      const $ = (id) => document.getElementById(id);
      const tokenKey = 'FTGControlToken';
      $('token').value = localStorage.getItem(tokenKey) || '';
      function saveToken(){ localStorage.setItem(tokenKey, $('token').value); }
      async function execAction(a){
        const r = await fetch('/exec', { method:'POST', headers: { 'Content-Type':'application/json', 'X-FTG-Token': localStorage.getItem(tokenKey)||'' }, body: JSON.stringify({action:a}) });
        $('execOut').textContent = await r.text();
      }
      async function testLLM(){
        const r = await fetch('/llm/chat', { method:'POST', headers: { 'Content-Type':'application/json', 'X-FTG-Token': localStorage.getItem(tokenKey)||'' }, body: JSON.stringify({prompt: $('prompt').value}) });
        $('llmOut').textContent = await r.text();
      }
    </script>
  </body>
  </html>
"""


@app.get("/ui")
async def web_panel():
    # UI доступен без токена; сами API-вызовы внутри страницы требуют X-FTG-Token
    return HTMLResponse(content=_UI_HTML)


_ROOT_DIR = Path(__file__).resolve().parents[2]
_PID_FILE = _ROOT_DIR / "ftg/ftg_runner.pid"

# Temporary auth store for generating Pyrogram string sessions
_AUTH_STORE: Dict[str, Dict[str, str]] = {}

# Auto-reply worker state
_auto_worker_task: Optional[asyncio.Task] = None
_auto_worker_should_stop: asyncio.Event | None = None
_auto_worker_last_reply_at: Dict[int, float] = {}


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


def _kill_process_tree(pid: int) -> None:
    """Best-effort terminate the spawned process group."""
    try:
        pgid = os.getpgid(pid)
        with contextlib.suppress(Exception):
            os.killpg(pgid, signal.SIGTERM)
    except Exception:
        with contextlib.suppress(Exception):
            os.kill(pid, signal.SIGTERM)


async def _auto_reply_loop(stop_event: asyncio.Event):
    try:
        from pyrogram import Client, filters  # type: ignore
    except Exception:
        return

    api_id = int(os.getenv("API_ID") or os.getenv("TELEGRAM_API_ID") or 0)
    api_hash = os.getenv("API_HASH") or os.getenv("TELEGRAM_API_HASH") or ""
    session_string = (
        os.getenv("TELEGRAM_STRING_SESSION")
        or os.getenv("SESSION_STRING")
        or os.getenv("STRING_SESSION")
        or ""
    )
    if not (api_id and api_hash and session_string):
        return

    cfg = get_bot_config()

    app = Client(
        "ftg_autoreply",
        api_id=api_id,
        api_hash=api_hash,
        session_string=session_string,
        device_model="FTG-Companion-Auto",
    )  # type: ignore

    # note: allow/block set пересчитываем при каждом событии, чтобы ловить новые настройки

    def _chat_in_list(chat: Any, lst: set[str]) -> bool:
        if not chat:
            return False
        cid = getattr(chat, "id", None)
        username = getattr(chat, "username", None)
        title = getattr(chat, "title", None)
        candidates = []
        if cid is not None:
            candidates.append(str(cid))
        if username:
            candidates.append(str(username))
        if title:
            candidates.append(str(title))
        return any(c in lst for c in candidates)

    @app.on_message(filters.text)
    async def handler(client, message):  # type: ignore
        nonlocal cfg
        # reload latest cfg periodically (cheap read)
        # avoid excessive locking: refresh every 5 seconds
        if int(_time.time()) % 5 == 0:
            cfg_local = get_bot_config()
            cfg = cfg_local

        # Ignore our own non-command messages to avoid loops
        try:
            if getattr(message, "outgoing", False):
                txt = (message.text or message.caption or "").strip().lower()
                if not (txt.startswith(".") or txt.startswith("/")):
                    return
        except Exception:
            pass

        # rate limiting per chat
        chat_id = int(getattr(message.chat, "id", 0) or 0)
        now = _time.time()
        last_at = _auto_worker_last_reply_at.get(chat_id, 0)
        if now - last_at < max(0, int(cfg.min_reply_interval_seconds or 0)):
            return

        user_text = message.text or message.caption or ""
        if not user_text.strip():
            return

        # built-in commands (рус./англ.)
        text_lower = user_text.strip().lower()
        if text_lower in (".ping", "/ping", "пинг"):
            await message.reply_text("pong", quote=True)
            _auto_worker_last_reply_at[chat_id] = now
            return
        if text_lower.startswith(".help") or text_lower == "/help" or text_lower == "помощь":
            await message.reply_text("Доступные команды: .ai <текст>, .sum, .tr ru|en|es|uk <текст>, .ping", quote=True)
            _auto_worker_last_reply_at[chat_id] = now
            return

        # .ai and variations trigger LLM directly
        ai_prefixes = (".ai ", "/ai ", "аи ")
        prompt_text = None
        for pfx in ai_prefixes:
            if user_text.startswith(pfx):
                prompt_text = user_text[len(pfx):].strip()
                break
        if prompt_text is None:
            # если автоответ отключён — команды выше уже отработали; обычные ответы не шлём
            if not cfg.auto_reply_enabled:
                return
            # Команды не найдены — применяем allow/block и режим
            allow_set = set(str(x) for x in (cfg.allowlist_chats or ()))
            block_set = set(str(x) for x in (cfg.blocklist_chats or ()))
            if block_set and _chat_in_list(message.chat, block_set):
                return
            if allow_set and not _chat_in_list(message.chat, allow_set):
                return
            if cfg.auto_reply_mode == "off":
                return
            if cfg.auto_reply_mode == "mentions_only":
                if not (message.mentioned or (message.text and client.me and (getattr(client.me, "username", None) or "") in message.text)):
                    return
            prompt_text = user_text

        try:
            # Симуляция печати (для человеческого ощущения)
            if getattr(cfg, "humanize_typing_enabled", True):
                import random
                delay_ms = random.randint(int(getattr(cfg, "typing_min_ms", 800)), int(getattr(cfg, "typing_max_ms", 2500)))
                with contextlib.suppress(Exception):
                    await message.react("⌨️")  # необязательный жест, если доступен
                await asyncio.sleep(delay_ms / 1000.0)

            reply = await llm_chat(prompt=prompt_text, system=(cfg.reply_prompt or None))
            if reply.strip():
                await message.reply_text(reply, quote=True)
                _auto_worker_last_reply_at[chat_id] = now
        except Exception:
            # do not crash the worker on LLM errors
            pass

    try:
        await app.start()
        while not stop_event.is_set():
            await asyncio.sleep(0.5)
    finally:
        with contextlib.suppress(Exception):
            await app.stop()


def _ensure_auto_worker() -> None:
    global _auto_worker_task, _auto_worker_should_stop
    cfg = get_bot_config()
    # Always run worker to catch commands (.ai/.help/.ping), even if FTG is running.
    # Auto-replies will still respect cfg.auto_reply_enabled in handler.
    should_run = True
    is_running = _auto_worker_task is not None and not _auto_worker_task.done()
    if should_run and not is_running:
        _auto_worker_should_stop = asyncio.Event()
        _auto_worker_task = asyncio.create_task(_auto_reply_loop(_auto_worker_should_stop))
    elif not should_run and is_running:
        if _auto_worker_should_stop is not None:
            _auto_worker_should_stop.set()
        _auto_worker_task = None


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
    _kill_process_tree(pid)
    # Wait up to 10s for graceful stop
    for _ in range(100):
        if not _is_pid_alive(pid):
            break
        time.sleep(0.1)
    if _PID_FILE.exists() and not _is_pid_alive(pid):
        with contextlib.suppress(Exception):
            _PID_FILE.unlink()
    return {"ok": True, "stopped": True}


@app.post("/exec")
async def exec_action(payload: ExecRequest, _: str = Depends(require_token)):
    action = (payload.action or "").lower()
    if action == "status":
        return {"ok": True, "running": bool(_read_pid())}
    if action == "start":
        res = _start_ftg()
        _ensure_auto_worker()
        return res
    if action == "stop":
        res = _stop_ftg()
        _ensure_auto_worker()
        return res
    if action == "restart":
        _stop_ftg()
        time.sleep(0.5)
        res = _start_ftg()
        _ensure_auto_worker()
        return res
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
    _ensure_auto_worker()
    return {"ok": True, "config": bot_config_dict()}


@app.on_event("startup")
async def on_startup():
    _ensure_auto_worker()


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
