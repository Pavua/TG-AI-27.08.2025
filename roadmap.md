# Дорожная карта (RU)

## Фаза 1 — Базовая инфраструктура (DONE)
- Control Server (FastAPI) на 127.0.0.1:8787 с токен‑авторизацией
  - Эндпойнты: `/`, `/health`, `/llm/chat`, `/llm/config` (GET/POST), `/llm/providers`, `/logs/tail`, `/exec`, `/send_message`, `/bot/config` (GET/POST), `/ui`
  - Простейший rate‑limit и логирование
- LLM клиент (httpx, таймауты, трим ответов) + нормализация LM Studio `/v1` и автопоиск `model id`
- AI‑команды: `.ai`, `.sum`, `.tr` (ru/en/es/uk)
- Makefile (`install/dev/test/run-server/run-ftg`), скрипты (string session, launchagent)
- Фолбек‑лайт юзербот (Telethon)

Acceptance:
- `/health` 200 c токеном; `/llm/chat` возвращает ответ модели (LM Studio)
- `.ai/.sum/.tr` работают через лайт‑бот; логи доступны через `/logs/tail`

## Фаза 2 — Управление процессом FTG (DONE)
- `/exec`: start/stop/restart/status через PID
- `/send_message`: отправка через Pyrogram (session string)
- Установка AI‑модуля в FTG при наличии

Acceptance:
- Старт/Стоп/Рестарт работают; `/send_message` отправляет в Saved Messages

## Фаза 3 — macOS GUI (IN PROGRESS)
- Dashboard: кнопки `/exec`, живой статус (`/health`) + RU/EN переключатель
- AI Settings: выбор провайдера/модели через `/llm/config` (OpenAI/Groq/LM Studio/…)
- Logs: tail, копирование, автообновление
- Web Panel: встроенная панель `/ui` (Exec + тест `/llm/chat`)
- Messages: отправка сообщений (me/@username/ID)
- Bot Settings: автоответчик (режимы, allow/block‑list, silent reading, системный prompt)
- Command‑listener: .help/.ping/.ai работают без запуска Dragon‑Userbot

Acceptance:
- Все базовые операции доступны из GUI без терминала
- Команды работают в Saved Messages и обычных чатах

## Фаза 4 — Инструменты и интеграции LLM (NEXT)
- MCP/инструменты LM Studio: включение `tool_choice=auto`, поддержка параллельных вызовов
- Кнопка "Загрузить модели" (GET `/v1/models`) и выпадающий список в GUI
- Управление ключами и профилями провайдеров; тест соединения

Acceptance:
- Модель с инструментами может вызывать MCP (например, web‑поиск), результаты видны в ответах

## Фаза 5 — UX/автозапуск/безопасность (NEXT)
- Keychain: хранение секретов (LLM API Key, FTG token)
- SMAppService: автозапуск GUI (Login Item)
- LaunchAgent: автозапуск юзербота
- Уведомления, тосты, светлая/тёмная темы

Acceptance:
- Секреты вне .env при использовании GUI; автозапуск включается из GUI

## Фаза 6 — Диалоги/логирование/память (NEXT)
- Просмотр списка диалогов (read‑only) в GUI
- Логирование удалённых сообщений, экспорты
- Память чатов (переписки/тэги/профили), контекст для ИИ

## Чек‑лист (статус)
- [x] Сервер: токен, health, логи, LLM‑прокси
- [x] LLM клиент: LM Studio `/v1`, поиск `model id`, таймауты
- [x] Запуск Dragon‑Userbot: venv, Python 3.8–3.11, asyncio fix (work in progress)
- [x] Session bootstrap: создание `my_account.session` (улучшено)
- [x] GUI: Dashboard, AI, Logs, Messages, Server, Bot; RU/EN
- [x] Web Panel: встроенный `/ui`
- [x] Messages: Pyrogram‑отправка
- [x] Команды: .help/.ping/.ai через command‑listener (без FTG)
- [ ] Перезапуск FTG: устойчивый (наблюдаем, улучшаем)
- [ ] MCP в LM Studio: проверка/включение, тест с web‑поиском
- [ ] GUI: Models from `/v1/models`, тосты/индикаторы
- [ ] Автозапуск: LaunchAgent + Login Item
- [ ] Диалоги/удалённые сообщения (просмотр/лог)
- [ ] Память и контекст ИИ

## Гайд по использованию (кратко)
1) LM Studio: запустите модель (например, `openai/gpt-oss-20b`).
2) `.env`: заполните `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_STRING_SESSION`, `FTG_CONTROL_TOKEN`, при необходимости `DRAGON_DB_URL`, `LLM_*`.
3) Сервер: `make run-server` (GUI → Server → Ping /health = ok).
4) GUI:
   - AI: Base URL `http://192.168.0.171:1234/v1`, Model `openai/gpt-oss-20b`, Timeout 60–120, Test.
   - Bot: включите автоответчик по желанию; allow/block‑list; системный prompt.
   - Messages: `me` → Отправить.
   - Панель: Start/Stop/Restart/Status.
5) Команды в Telegram: `.help`, `.ping`, `.ai <текст>` — работают даже без Dragon‑Userbot.

## Следующий спринт (1–2 дня)
1) MCP‑режим LM Studio: убедиться, что инструменты включены (tool_choice=auto), провести E2E‑тест (web‑поиск)
2) AI Settings: загрузка `/v1/models` + выбор модели + сохранение
3) Dashboard: тосты/индикатор running; обработка таймаутов
4) Диалоги (read‑only) и базовый журнал удалённых сообщений
5) Документация (RU): README/скриншоты/траблшутинг

Acceptance:
- Команды и MCP работают; GUI стабилен; документация обновлена