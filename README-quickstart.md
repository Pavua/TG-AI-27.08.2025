# FTG Suite — Quickstart

## Install
```bash
make install        # creates .venv and installs runtime deps
make dev            # dev extras (pytest, ruff, black, mypy)
```

## Configure
- Copy `.env.example` → `.env`, fill: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `STRING_SESSION`.
- Set `FTG_CONTROL_TOKEN` (used by the Control Server auth header `X-FTG-Token`).
- Optional LLM params: `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`.
- Generate **STRING_SESSION**:
```bash
python scripts/generate_string_session.py
```
- Start **LM Studio** → Start Server (OpenAI API on http://127.0.0.1:1234/v1).

## Run
```bash
make run-ftg
# open http://localhost:8080 and log in with the code from Saved Messages
```

## Test AI
In Saved Messages:
- `.ping` → `pong`
- `.ai hello`
- reply `.sum`
- reply `.tr es`

## Build GUI
```bash
brew install xcodegen
cd macos-app && xcodegen generate
open FTG\ Companion.xcodeproj
```

## Security
- Control Server binds to 127.0.0.1 only and requires `X-FTG-Token`.
- Never commit secrets; use `.env` and macOS Keychain (GUI will store tokens).

### Control token
- Если в `.env` не указали `FTG_CONTROL_TOKEN`, используйте `changeme_local_token` (дефолт).
- В запросах к Control Server передавайте: `-H "X-FTG-Token: <token>"`.

### Выбор LLM провайдера
- Список предустановленных провайдеров: `GET /llm/providers`.
- Текущая конфигурация: `GET /llm/config`.
- Горячее обновление: `POST /llm/config` с полями `base_url`, `model`, `api_key`, `temperature`, `max_tokens`, `request_timeout_seconds`.

## Next
- Read `roadmap.md` and follow phases.
- Use `docs/cursor_prompt_ftg_gui_en.md` in Cursor to generate/complete code.