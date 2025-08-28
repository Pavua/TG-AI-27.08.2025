# Roadmap

## Phase 1 — Core plumbing (DONE)
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

## Phase 2 — FTG integration & process control (DONE)
- /exec: start/stop/restart/status FTG via PID file
- /send_message: send via Telethon (STRING_SESSION or ephemeral)
- Auto-install AI module into FTG when available

Acceptance:
- Start/Stop/Restart работают из Control Server
- /send_message отправляет в Saved Messages по username/id

## Phase 3 — macOS GUI controls (IN PROGRESS)
- Dashboard: buttons wired to /exec, real-time status (/health)
- AI Settings: choose provider/model via /llm/config (OpenAI, Groq, LM Studio, …)
- Logs: tail, search, copy
- Web Panel: embedded (LM Studio UI at http://192.168.0.171:1234)
- Bot Settings: тумблеры и параметры автоответчика (невидимое чтение, allow/block list)

Acceptance:
- Все основные операции доступны из GUI без терминала

## Phase 4 — Security & UX polish (NEXT)
- Keychain: хранение токенов и секретов
- SMAppService: автозапуск GUI (Login Item)
- LaunchAgent: автозапуск FTG
- Notifications, Shortcuts, accessibility, dark/light

Acceptance:
- Секреты не в .env при использовании GUI; автозапуск работает

## Phase 5 — Tests & Docs (NEXT)

---

## Milestones & Checklist

- [x] Control Server: token auth, health, logs, LLM proxy
- [x] LLM client: LM Studio normalization (/v1), resolve model id, timeouts
- [x] Dragon‑Userbot launcher: Python 3.8–3.11 discovery, .venv_dragon, asyncio fix
- [x] Session bootstrap: create my_account.session from TELEGRAM_STRING_SESSION
- [x] GUI: Dashboard, AI Settings, Logs, Messages, Server (token)
- [x] Web Panel: temporary LM Studio UI
- [x] Messages: send via Pyrogram (session string), no interactive prompts
- [ ] GUI: Status/Restart/Stop robust UX (spinners, toasts)
- [ ] GUI: Bot Settings – управление автоответчиком и списками чатов
- [ ] GUI: Web Panel URL editable, error banner on load failure
- [ ] GUI: AI Settings – dropdown from /models, timeout slider, latency stats
- [ ] Security: store FTG_CONTROL_TOKEN & LLM_API_KEY only in Keychain; scrub defaults
- [ ] LaunchAgent: enable/disable from GUI; login item for app
- [ ] Shortcuts: quick actions for /exec and /send_message
- [ ] Providers: OpenAI/Groq/OpenRouter toggles; connectivity tests
- [ ] Tests: integration tests for /exec, /llm/chat; SwiftUI snapshot tests
- [ ] Docs: full README with scenarios; screenshots; troubleshooting

## Usage Guide (short)

1. LM Studio: запустить модель; проверить API id (например, `openai/gpt-oss-20b`).
2. .env: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_STRING_SESSION, DRAGON_DB_URL, FTG_CONTROL_TOKEN.
3. Сервер: `make run-server` (GUI → Server → Ping /health = ok).
4. GUI:
   - AI Settings: Base URL `http://192.168.0.171:1234/v1`, Model `openai/gpt-oss-20b`, Test.
   - Messages: `me` → Send (ожидаем `{"ok":true}`).
   - Dashboard: Start/Status/Stop FTG.

## Next Sprint (1–2 дня)

1) GUI Web Panel URL → editable + сохранение (Keychain/UserDefaults).  
2) Dashboard UX: ненавязчивые тосты об ошибках/успехе, явный индикатор running.  
3) AI Settings: список из /models + выбор модели в 1 клик; таймаут 15–90s.  
4) LaunchAgent toggle в GUI (вкл/выкл автозапуск юзербота).  
5) Документация по использованию бота: команда `.ai`, `.sum`, `.tr`, примеры.
- Расширить unit/integration tests (Control Server, LLM, GUI hooks)
- Документация с скриншотами и сценариями

Acceptance:
- Тесты проходят; README-quickstart обновлён; скриншоты добавлены