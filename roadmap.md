# Roadmap

## Phase 1 — Core plumbing (done/in progress)
- Control Server (FastAPI) on 127.0.0.1:8787 with token auth
  - Endpoints: /, /health, /llm/chat, /llm/config (GET/POST), /llm/providers, /logs/tail
  - Basic rate limiting, request logging with redaction
- LLM client (httpx, timeouts, 4096-char trim) with hot-reload config
- AI commands: .ai, .sum, .tr (ru/en/es/uk)
- Makefile (install/dev/test/run-server/run-ftg), scripts (string session, launchagent)
- FTG launcher with auto-install attempts + lite userbot fallback

Acceptance:
- /health returns 200 with token; /llm/chat returns model output (LM Studio)
- .ai/.sum/.tr work via lite userbot; logs accessible via /logs/tail

## Phase 2 — FTG integration & process control (current)
- /exec: start/stop/restart/status FTG via PID file
- /send_message: send via Telethon (STRING_SESSION or ephemeral)
- Auto-install AI module into FTG when available

Acceptance:
- Start/Stop/Restart работают из Control Server
- /send_message отправляет в Saved Messages по username/id

## Phase 3 — macOS GUI controls
- Dashboard: buttons wired to /exec, real-time status (/health)
- AI Settings: choose provider/model via /llm/config (OpenAI, Groq, LM Studio, …)
- Logs: tail, search, copy
- Web Panel: embedded (http://localhost:8080)

Acceptance:
- Все основные операции доступны из GUI без терминала

## Phase 4 — Security & UX polish
- Keychain: хранение токенов и секретов
- SMAppService: автозапуск GUI (Login Item)
- LaunchAgent: автозапуск FTG
- Notifications, Shortcuts, accessibility, dark/light

Acceptance:
- Секреты не в .env при использовании GUI; автозапуск работает

## Phase 5 — Tests & Docs
- Расширить unit/integration tests (Control Server, LLM, GUI hooks)
- Документация с скриншотами и сценариями

Acceptance:
- Тесты проходят; README-quickstart обновлён; скриншоты добавлены