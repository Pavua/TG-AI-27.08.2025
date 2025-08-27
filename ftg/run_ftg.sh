#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a; source .env; set +a
fi

# Map env vars for Dragon-Userbot expectations
if [ -n "${TELEGRAM_API_ID:-}" ] && [ -z "${API_ID:-}" ]; then export API_ID="$TELEGRAM_API_ID"; fi
if [ -n "${TELEGRAM_API_HASH:-}" ] && [ -z "${API_HASH:-}" ]; then export API_HASH="$TELEGRAM_API_HASH"; fi
if [ -n "${DRAGON_DB_URL:-}" ]; then
  if [ -z "${MONGO_DB_URL:-}" ]; then export MONGO_DB_URL="$DRAGON_DB_URL"; fi
  if [ -z "${DATABASE_URL:-}" ]; then export DATABASE_URL="$DRAGON_DB_URL"; fi
fi

# In NON_INTERACTIVE mode require a ready session string to avoid blocking prompts
if [ "${NON_INTERACTIVE:-0}" = "1" ]; then
  if [ -z "${TELEGRAM_STRING_SESSION:-${SESSION_STRING:-${STRING_SESSION:-}}}" ]; then
    echo "[FTG] NON_INTERACTIVE=1 but no TELEGRAM_STRING_SESSION/SESSION_STRING present. Aborting start." | tee -a "$LOG_FILE"
    exit 1
  fi
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

"$ROOT_DIR"/.venv/bin/pip install -q --upgrade pip
"$ROOT_DIR"/.venv/bin/pip install -q -r requirements.txt

LOG_FILE="${ROOT_DIR}/ftg.log"
echo "[FTG] starting at $(date)" >> "$LOG_FILE"

# Validate required env for first run (Telegram API creds)
if { [ -z "${TELEGRAM_API_ID:-}" ] || [ -z "${TELEGRAM_API_HASH:-}" ]; } && { [ -z "${API_ID:-}" ] || [ -z "${API_HASH:-}" ]; }; then
  echo "[FTG] TELEGRAM_API_ID/API_ID or TELEGRAM_API_HASH/API_HASH are not set in .env" | tee -a "$LOG_FILE"
  echo "[FTG] Please set them and re-run. You can generate STRING_SESSION via scripts/generate_string_session.py" | tee -a "$LOG_FILE"
  echo "[FTG] Example: TELEGRAM_API_ID=12345" | tee -a "$LOG_FILE"
  echo "[FTG]         TELEGRAM_API_HASH=abcdef123456" | tee -a "$LOG_FILE"
  exit 1
fi

# Check if .env file contains default values that need to be replaced
if grep -q "your_telegram_api_id_here\|your_telegram_api_hash_here\|your_control_token_here" .env 2>/dev/null; then
  echo "[FTG] WARNING: .env file contains default placeholder values!" | tee -a "$LOG_FILE"
  echo "[FTG] Please edit .env file and replace placeholder values with your actual credentials." | tee -a "$LOG_FILE"
  echo "[FTG] Required: TELEGRAM_API_ID, TELEGRAM_API_HASH, FTG_CONTROL_TOKEN" | tee -a "$LOG_FILE"
  echo "[FTG] Optional: DRAGON_DB_URL, LLM_BASE_URL, LLM_MODEL, LLM_API_KEY" | tee -a "$LOG_FILE"
  exit 1
fi

# If user provided a remote FTG repo URL, clone/update into .ftg_repo EARLY and run it if it's Dragon-Userbot
if [ -n "${FTG_REPO_URL:-}" ]; then
  REPO_DIR="${ROOT_DIR}/.ftg_repo"
  if [ ! -d "$REPO_DIR/.git" ]; then
    echo "[FTG] Cloning FTG repo with tags: $FTG_REPO_URL" | tee -a "$LOG_FILE"
    git clone --quiet "$FTG_REPO_URL" "$REPO_DIR" || true
  else
    echo "[FTG] Updating FTG repo in $REPO_DIR" | tee -a "$LOG_FILE"
    (cd "$REPO_DIR" && git pull --rebase --autostash || true)
  fi
  # Ensure tags are available for GitPython logic in Dragon-Userbot
  (cd "$REPO_DIR" && git fetch --tags --quiet || true)
  export FTG_REPO_DIR="$REPO_DIR"
fi

# If a local .ftg_repo exists but FTG_REPO_DIR is not set, use it
if [ -z "${FTG_REPO_DIR:-}" ] && [ -d "${ROOT_DIR}/.ftg_repo" ]; then
  export FTG_REPO_DIR="${ROOT_DIR}/.ftg_repo"
  echo "[FTG] Using detected local FTG repo: $FTG_REPO_DIR" | tee -a "$LOG_FILE"
fi

# If user provided a local FTG repo, prefer running it directly
if [ -n "${FTG_REPO_DIR:-}" ] && [ -d "$FTG_REPO_DIR" ]; then
  echo "[FTG] Using local FTG repo: $FTG_REPO_DIR" | tee -a "$LOG_FILE"
  if [ -f "$FTG_REPO_DIR/requirements.txt" ]; then
    "$ROOT_DIR"/.venv/bin/pip install -q -r "$FTG_REPO_DIR/requirements.txt" || true
    # If using mongodb+srv, ensure dnspython is present for SRV
    if echo "${MONGO_DB_URL:-}" | grep -q "mongodb+srv://"; then
      echo "[FTG] Installing dnspython for Mongo SRV support" | tee -a "$LOG_FILE"
      "$ROOT_DIR"/.venv/bin/pip install -q dnspython
    fi
  fi
  cd "$FTG_REPO_DIR"
  if [ -f "main.py" ]; then
    echo "[FTG] Detected Dragon-Userbot (main.py)." | tee -a "$LOG_FILE"
    # Sanitize accidental angle brackets in DB URL
    if [ -n "${MONGO_DB_URL:-}" ]; then
      MONGO_DB_URL="${MONGO_DB_URL//</}"
      MONGO_DB_URL="${MONGO_DB_URL//>/}"
      export MONGO_DB_URL
    fi
    if [ -n "${MONGO_DB_URL:-}" ]; then
      if [ -z "${DATABASE_TYPE:-}" ]; then export DATABASE_TYPE="mongodb"; fi
      if [ -z "${DATABASE_NAME:-}" ]; then export DATABASE_NAME="ftg"; fi
    fi
    # Prefer Python 3.8/3.9/3.10/3.11 for Pyrogram stability (avoid 3.12/3.13 asyncio issues)
    DRAGON_PY=""
    for cand in \
      "/opt/homebrew/bin/python3.8" \
      "$(command -v python3.8 2>/dev/null)" \
      "/opt/homebrew/bin/python3.9" \
      "$(command -v python3.9 2>/dev/null)" \
      "/opt/homebrew/bin/python3.11" \
      "$(command -v python3.11 2>/dev/null)" \
      "/opt/homebrew/bin/python3.10" \
      "$(command -v python3.10 2>/dev/null)"; do
      if [ -n "$cand" ] && [ -x "$cand" ]; then DRAGON_PY="$cand"; break; fi
    done
    if [ -z "$DRAGON_PY" ] && command -v brew >/dev/null 2>&1; then
      echo "[FTG] Installing python@3.8 via Homebrew..." | tee -a "$LOG_FILE"
      brew install -q python@3.8 || true
      if [ -x "/opt/homebrew/bin/python3.8" ]; then DRAGON_PY="/opt/homebrew/bin/python3.8"; fi
    fi
    if [ -z "$DRAGON_PY" ] && command -v brew >/dev/null 2>&1; then
      echo "[FTG] Installing python@3.9 via Homebrew..." | tee -a "$LOG_FILE"
      brew install -q python@3.9 || true
      if [ -x "/opt/homebrew/bin/python3.9" ]; then DRAGON_PY="/opt/homebrew/bin/python3.9"; fi
    fi
    if [ -z "$DRAGON_PY" ] && command -v brew >/dev/null 2>&1; then
      echo "[FTG] Installing python@3.10 via Homebrew..." | tee -a "$LOG_FILE"
      brew install -q python@3.10 || true
      if [ -x "/opt/homebrew/bin/python3.10" ]; then DRAGON_PY="/opt/homebrew/bin/python3.10"; fi
    fi
    if [ -z "$DRAGON_PY" ] && command -v brew >/dev/null 2>&1; then
      echo "[FTG] Installing python@3.11 via Homebrew..." | tee -a "$LOG_FILE"
      brew install -q python@3.11 || true
      if [ -x "/opt/homebrew/bin/python3.11" ]; then DRAGON_PY="/opt/homebrew/bin/python3.11"; fi
    fi
    if [ -n "$DRAGON_PY" ]; then
      DRAGON_VENV="$ROOT_DIR/.venv_dragon"
      if [ ! -d "$DRAGON_VENV" ]; then "$DRAGON_PY" -m venv "$DRAGON_VENV"; fi
      "$DRAGON_VENV"/bin/pip install -q --upgrade pip
      # Pin known-stable versions to avoid asyncio issues
      "$DRAGON_VENV"/bin/pip install -q "pyrogram==2.0.106" "tgcrypto==1.2.5" || true
      if [ -f requirements.txt ]; then "$DRAGON_VENV"/bin/pip install -q -r requirements.txt || true; fi
      # SRV support
      if echo "${MONGO_DB_URL:-}" | grep -q "mongodb+srv://"; then "$DRAGON_VENV"/bin/pip install -q dnspython; fi
      echo "[FTG] Launching Dragon-Userbot with Python $("$DRAGON_VENV"/bin/python -V 2>/dev/null)" | tee -a "$LOG_FILE"
      # dnspython is required for mongodb+srv URIs but not always in requirements
      if [[ "${DRAGON_DB_URL:-}" == mongodb+srv* ]]; then
        if ! "$DRAGON_VENV/bin/pip" show dnspython >/dev/null 2>&1; then
           echo "[FTG] Installing dnspython for Mongo SRV support" | tee -a "$LOG_FILE"
          "$DRAGON_VENV/bin/pip" install -q dnspython
        fi
      fi

      cd "$FTG_REPO_DIR" || exit 1
      # Run via our wrapper script to handle asyncio policies
      # NON_INTERACTIVE prevents any input prompts when invoked from server
      exec env \
        API_ID="$TELEGRAM_API_ID" \
        API_HASH="$TELEGRAM_API_HASH" \
        SESSION_STRING="${TELEGRAM_STRING_SESSION:-}" \
        MONGO_DB_URL="${DRAGON_DB_URL:-${MONGO_DB_URL:-}}" \
        DATABASE_URL="${DRAGON_DB_URL:-${DATABASE_URL:-}}" \
        DATABASE_TYPE="${DATABASE_TYPE:-mongodb}" \
        DATABASE_NAME="${DATABASE_NAME:-ftg}" \
        NON_INTERACTIVE="${NON_INTERACTIVE:-0}" \
        "$DRAGON_VENV/bin/python" "../scripts/run_dragon.py" >>"$LOG_FILE" 2>&1

    else
      echo "[FTG] Fallback to system Python for Dragon-Userbot" | tee -a "$LOG_FILE"
      # Fallback to the default python in the main venv if no specific version was found
      exec "$ROOT_DIR"/.venv/bin/python main.py 2>&1 | tee -a "$LOG_FILE"
    fi
  else
    echo "[FTG] Launching Friendly-Telegram from local repo..." | tee -a "$LOG_FILE"
    exec "$ROOT_DIR"/.venv/bin/python -m friendly-telegram 2>&1 | tee -a "$LOG_FILE"
  fi
fi

# Ensure Friendly-Telegram is installed; install from GitHub if missing
install_ok=0
if "$ROOT_DIR"/.venv/bin/python - <<'PY'
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec('friendly_telegram') else 1)
PY
then
  install_ok=0
else
  install_ok=1
fi

if [ $install_ok -ne 0 ]; then
  echo "[FTG] Friendly-Telegram not found. Installing..." | tee -a "$LOG_FILE"
  # Allow override via env (supports pip name or git+https URL)
  if [ -n "${FTG_INSTALL_SOURCE:-}" ]; then
    echo "[FTG] Installing from FTG_INSTALL_SOURCE=$FTG_INSTALL_SOURCE" | tee -a "$LOG_FILE"
    if ! "$ROOT_DIR"/.venv/bin/pip install -q "$FTG_INSTALL_SOURCE"; then echo "[FTG] Install failed from FTG_INSTALL_SOURCE" | tee -a "$LOG_FILE"; fi
  fi
  # Try known candidates
  candidates=(
    "friendly-telegram"
    "friendlytelegram"
    "git+https://github.com/FTG-Userbot/FTG-Userbot.git"
    "git+https://github.com/fast-geek/friendly-telegram.git"
  )
  for c in "${candidates[@]}"; do
    if "$ROOT_DIR"/.venv/bin/python - <<'PY'
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec('friendly_telegram') else 1)
PY
    then
      break
    fi
    echo "[FTG] Trying install: $c" | tee -a "$LOG_FILE"
    if "$ROOT_DIR"/.venv/bin/pip install -q "$c"; then
      echo "[FTG] Installed via $c" | tee -a "$LOG_FILE"
    fi
  done
  # Final check
  if ! "$ROOT_DIR"/.venv/bin/python - <<'PY'
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec('friendly_telegram') else 1)
PY
  then
    echo "[FTG] WARNING: Unable to install Friendly-Telegram automatically. Falling back to lite userbot." | tee -a "$LOG_FILE"
    exec "$ROOT_DIR"/.venv/bin/python -m ftg.lite_userbot 2>&1 | tee -a "$LOG_FILE"
  fi
fi

# Ensure AI module is installed into Friendly-Telegram modules directory
"$ROOT_DIR"/.venv/bin/python scripts/install_ai_module.py || true

# If user provided a remote FTG repo URL, clone/update into .ftg_repo
if [ -n "${FTG_REPO_URL:-}" ]; then
  REPO_DIR="${ROOT_DIR}/.ftg_repo"
  if [ ! -d "$REPO_DIR/.git" ]; then
    echo "[FTG] Cloning FTG repo: $FTG_REPO_URL" | tee -a "$LOG_FILE"
    git clone --depth=1 "$FTG_REPO_URL" "$REPO_DIR" || true
  else
    echo "[FTG] Updating FTG repo in $REPO_DIR" | tee -a "$LOG_FILE"
    (cd "$REPO_DIR" && git pull --rebase --autostash || true)
  fi
  export FTG_REPO_DIR="$REPO_DIR"
fi

# If user provided a local FTG repo, try to run from it
if [ -n "${FTG_REPO_DIR:-}" ] && [ -d "$FTG_REPO_DIR" ]; then
  echo "[FTG] Using local FTG repo: $FTG_REPO_DIR" | tee -a "$LOG_FILE"
  if [ -f "$FTG_REPO_DIR/requirements.txt" ]; then
    "$ROOT_DIR"/.venv/bin/pip install -q -r "$FTG_REPO_DIR/requirements.txt" || true
  fi
  cd "$FTG_REPO_DIR"
  # Detect entrypoint: Dragon-Userbot uses main.py (Pyrogram); FTG uses friendly-telegram module
  if [ -f "main.py" ]; then
    echo "[FTG] Detected Dragon-Userbot (main.py)." | tee -a "$LOG_FILE"
    # Optional: if DB URL is needed, use DRAGON_DB_URL env from .env
    if [ -n "${DRAGON_DB_URL:-}" ]; then export MONGO_DB_URL="$DRAGON_DB_URL"; fi
    exec "$ROOT_DIR"/.venv/bin/python main.py 2>&1 | tee -a "$LOG_FILE"
  else
    echo "[FTG] Launching Friendly-Telegram from local repo..." | tee -a "$LOG_FILE"
    exec "$ROOT_DIR"/.venv/bin/python -m friendly-telegram 2>&1 | tee -a "$LOG_FILE"
  fi
fi

echo "[FTG] Launching Friendly-Telegram..." | tee -a "$LOG_FILE"
exec "$ROOT_DIR"/.venv/bin/python -m friendly-telegram 2>&1 | tee -a "$LOG_FILE"
