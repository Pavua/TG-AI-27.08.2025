SHELL := /bin/zsh

.PHONY: install dev lint test run-ftg run-server stop-server install-ai-module gui gui-open launchagent-load launchagent-unload

VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

$(VENV): requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install: $(VENV)

dev: install
	$(PIP) install -r requirements-dev.txt

lint: install
	$(VENV)/bin/ruff check .
	$(VENV)/bin/black --check .

test: dev
	$(PY) -m pytest -q

run-ftg: install
	bash ftg/run_ftg.sh

run-server: install
	@if lsof -ti tcp:8787 >/dev/null; then \
	  echo "Port 8787 is already in use. Run 'make stop-server' and retry."; \
	  exit 1; \
	fi
	$(PY) -m uvicorn ftg.control_server.server:app --host 127.0.0.1 --port 8787 --workers 1

stop-server:
	-@pids=$$(lsof -ti tcp:8787); if [ -n "$$pids" ]; then echo "Killing $$pids"; kill $$pids || true; sleep 1; fi

install-ai-module: install
	$(PY) scripts/install_ai_module.py

gui:
	brew list xcodegen >/dev/null 2>&1 || brew install xcodegen
	cd macos-app && xcodegen generate

gui-open: gui
	open "macos-app/FTG Companion.xcodeproj"

launchagent-load:
	$(PY) scripts/create_launchagent.py
	launchctl load -w ~/Library/LaunchAgents/com.ftg.userbot.plist || true

launchagent-unload:
	launchctl unload -w ~/Library/LaunchAgents/com.ftg.userbot.plist || true


