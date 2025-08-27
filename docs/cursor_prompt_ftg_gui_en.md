# Cursor Prompt — FTG + macOS GUI + Local AI (English)

## Context
We are extending **Friendly‑Telegram (FTG)** — a Telethon‑based userbot — for **macOS 26** (Apple Silicon). Goals:
1) Add an **AI module** in FTG that talks to any **OpenAI‑compatible** backend (LM Studio / Ollama / etc.).
2) Ship a **native macOS app (SwiftUI)** with a **full GUI** (menu bar + windows) to manage the userbot without a terminal.
3) Add a **local Control Server** inside FTG (FastAPI on `127.0.0.1`) used by the GUI for bot control.
4) Add **Launch at Login** + secure secret storage via **Keychain**.
5) Provide Shortcuts integrations, notifications, and a polished UX (Light/Dark, accessibility).

> Use **latest stable** versions:
> - **Telethon**: 1.40.0+  
> - **Python**: 3.12/3.13  
> - **FastAPI + Uvicorn**: latest stable  
> - **LM Studio**: OpenAI‑compatible API at `http://127.0.0.1:1234/v1`  
> - **Ollama**: optional, OpenAI chat‑completions compatible
> - macOS: **SMAppService** (Login Item), **Keychain Services**

## Tech stack & requirements
- **Python 3.12+**, **Telethon**, **httpx**.
- **FastAPI + Uvicorn** for **local Control Server** bound to `127.0.0.1`.
- **SwiftUI (Xcode 16)** + **WKWebView** for the macOS GUI.
- **Keychain** for secrets (`API_ID`, `API_HASH`, `STRING_SESSION`, LLM keys).
- **Security**: require `X‑FTG‑Token` on every Control Server call; no CORS; loopback only.
- **Autostart**: `SMAppService` for GUI; **LaunchAgent** for FTG process.
- Include **docs + tests**.

## Monorepo layout
```
ftg-suite/
  README-quickstart.md
  roadmap.md
  CURSOR_RULES.md
  .env.example
  requirements.txt
  requirements-dev.txt
  pytest.ini
  Makefile
  HOWTO-cursor-files.md
  docs/
    cursor_prompt_ftg_gui_en.md
    cursor_prompt_ftg_gui.md
  tests/
    test_control_server.py
    test_llm_client.py
  ftg/
    run_ftg.sh
    control_server/
      server.py
      schemas.py
    modules/
      ai.py
    utils/
      llm_client.py
      config.py
      text.py
    launch/
      com.ftg.userbot.plist
  macos-app/
    project.yml
    Sources/...(SwiftUI app skeleton)
  scripts/
    generate_string_session.py
    create_launchagent.py
```

## Tasks

### A) FTG AI module (`ftg/modules/ai.py`)
- Commands:
  - `.ai <prompt>` — chat with LLM; configurable system prompt.
  - `.sum` — summarize replied message (text/caption) concisely.
  - `.tr <ru|en|es|uk>` — translate replied message to target language.
- Config in FTG Web Panel or `.env`:
  - `LLM_BASE_URL` (default `http://127.0.0.1:1234/v1`)
  - `LLM_MODEL`, `LLM_API_KEY`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`
- `utils/llm_client.py` with **httpx** (async) and explicit timeouts.
- Trim outputs to **4096 chars**, robust error handling.
- Unit tests with mocks.

### B) Local Control Server (`ftg/control_server/server.py`)
- **FastAPI**, port `8787`, bind only `127.0.0.1`.
- Require header `X‑FTG‑Token` (from Keychain or env).
- Endpoints:
  - `GET /health` → `{status:"ok", ftg:"running"|"stopped"}`
  - `POST /exec` → run FTG action (send a command; toggle a module)
  - `POST /send_message` → send message to chat by username/id
  - `POST /llm/chat` → proxy to LLM client (for GUI test)
  - `GET /logs/tail?lines=200` → tail logs
- Request logging (redact secrets). No CORS. Simple rate‑limit.

### C) macOS GUI (SwiftUI, `macos-app/`)
- **Menu bar + main window** with tabs:
  - **Dashboard**: status via `/health`, Start/Stop/Restart.
  - **AI Settings**: tweak LLM params and test via `/llm/chat`.
  - **Web Panel**: embed FTG Web UI (`http://localhost:8080`) in **WKWebView**.
  - **Logs**: tail via `/logs/tail` with search/copy.
  - **Shortcuts**: quick actions (`POST /exec`).
- Secrets in **Keychain**. GUI **Login Item** via **SMAppService**.
- Process supervisor to run `ftg/run_ftg.sh` and capture logs.
- Polished UI (Light/Dark, accessibility).

### D) Scripts & Autostart
- `scripts/generate_string_session.py` → Telethon flow to print **STRING_SESSION**.
- `scripts/create_launchagent.py` → writes `~/Library/LaunchAgents/com.ftg.userbot.plist`.
- `ftg/run_ftg.sh` → activate venv, load `.env`, `python -m friendly-telegram`.

### E) Docs
- `README-quickstart.md`: brew/venv, FTG setup, LM Studio/Ollama setup, GUI usage, security.
- Architecture diagrams/notes: GUI ⇄ Control Server ⇄ FTG; GUI ⇄ Web Panel; GUI ⇄ LLM.

### F) Tests / Acceptance
- `.ai/.sum/.tr` work in Saved Messages; `.tr` supports ru/en/es/uk.
- GUI restart updates `/health`; logs reflect changes.
- FTG Web Panel loads inside GUI and authenticates.
- LLM settings apply **without FTG restart** (hot reload).
- All network calls require `X‑FTG‑Token` and are reachable only on `127.0.0.1`.

## Code quality
- Python: Ruff/black, type hints, explicit timeouts; no hard‑coded secrets.
- Swift: `@MainActor` as needed, background for IO; constants over magic strings.
- Output length limits everywhere.

## Do this
1) Implement modules/services above.
2) Provide `.env.example`, `README-quickstart.md`, screenshots.
3) Add tests and stubs (`ocr.py`, `digest.py` later).
4) Generate LaunchAgent; ensure FTG starts at login.