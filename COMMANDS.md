# FTG Suite — Minimal Commands

Install
```bash
make install
make dev
```

Control Server
```bash
make stop-server
make run-server
```

LLM quick checks
```bash
TOKEN=changeme_local_token
curl -s -H "X-FTG-Token: $TOKEN" http://127.0.0.1:8787/health
curl -s -H "X-FTG-Token: $TOKEN" http://127.0.0.1:8787/llm/providers
curl -s -H "X-FTG-Token: $TOKEN" http://127.0.0.1:8787/llm/config
curl -s -X POST http://127.0.0.1:8787/llm/chat \
  -H "X-FTG-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"prompt":"Hello"}'
```

Userbot
```bash
make run-ftg
```

GUI
```bash
brew install xcodegen
cd macos-app && xcodegen generate && open FTG\ Companion.xcodeproj
```

LaunchAgent (FTG autostart)
```bash
python scripts/create_launchagent.py
launchctl load -w ~/Library/LaunchAgents/com.ftg.userbot.plist
# remove: launchctl unload -w ~/Library/LaunchAgents/com.ftg.userbot.plist
```

Tests / Lint
```bash
make test
make lint
```
