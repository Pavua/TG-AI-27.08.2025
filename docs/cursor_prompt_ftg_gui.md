### FTG Companion — макет целевого интерфейса

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ FTG Companion                                 ●  ○  ⬜︎                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ Dashboard   AI Settings   Bot Settings   Messages   Logs   Server   WebPanel │
├──────────────────────────────────────────────────────────────────────────────┤
│ Status: ok   FTG: running                                      [Refresh]     │
│                                                                              │
│ [Start]  [Stop]  [Restart]  [Status]     ⟲ Running ●                         │
│ ──────────────────────────────────────────────────────────────────────────── │
│ Last action: Action restart OK                                               │
│                                                                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

Bot Settings
┌──────────────────────────────────────────────────────────────────────────────┐
│ Auto reply enabled [x]                                                       │
│ Auto reply mode: (• Off  ○ Mentions only  ○ All)                             │
│ Allowlist chats: me,@team                                                    │
│ Blocklist chats: @spam                                                       │
│ Silent reading (do not mark read) [x]                                        │
│ Min reply interval (sec): 5                                                  │
│ Reply prompt (system): "Ты — вежливый ассистент..."                           │
│ [Load] [Save]                                                                 │
└──────────────────────────────────────────────────────────────────────────────┘

AI Settings (пример)
┌──────────────────────────────────────────────────────────────────────────────┐
│ Providers: [Load]  Apply Config  Save Key                                    │
│ Base URL: http://192.168.0.171:1234/v1                                        │
│ Model: openai/gpt-oss-20b                                                     │
│ API Key: ********                                                             │
│ Test prompt: Hello                                                            │
│ [Test /llm/chat]                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

Пояснения:
- Dashboard: управление процессом юзербота и быстрый статус.
- Bot Settings: высокоуровневые настройки поведения автоответчика и приватности.
- AI Settings: выбор провайдера/модели, тест.
- Messages: отправка сообщений от имени аккаунта.
- Logs: просмотр логов и копирование.
- Server: токен для доступа к Control Server.
- Web Panel: встроенный UI внешних панелей (LM Studio и др.).