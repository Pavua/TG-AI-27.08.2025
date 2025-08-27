import os
import asyncio
import platform
import sys
from pathlib import Path

# Add the Dragon-Userbot repo to the python path
# Assumes this script is run from the ftg-suite root
# and the userbot is in .ftg_repo
FTG_REPO_PATH = Path(__file__).parent.parent / ".ftg_repo"
if str(FTG_REPO_PATH) not in sys.path:
    sys.path.insert(0, str(FTG_REPO_PATH))


def run_main():
    """
    Imports and runs the main function from Dragon-Userbot's main.py
    """
    try:
        # Dynamically import the main function from the userbot's code
        from main import main as dragon_main
        print("[run_dragon.py] Successfully imported main from Dragon-Userbot")
        asyncio.run(dragon_main())
    except ImportError as e:
        print(f"[run_dragon.py] Error: Could not import main from main.py: {e}", file=sys.stderr)
        print(f"[run_dragon.py] Make sure Dragon-Userbot is cloned at {FTG_REPO_PATH}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[run_dragon.py] An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Load .env early to populate environment variables expected by Dragon-Userbot
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        try:
            # Lazy import to avoid hard dependency
            from dotenv import load_dotenv  # type: ignore
            load_dotenv(env_path)
            print("[run_dragon.py] Loaded .env via python-dotenv")
        except Exception:
            # Fallback: minimal .env parser
            for line in env_path.read_text().splitlines():
                if not line or line.strip().startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip("'\""))
            print("[run_dragon.py] Loaded .env via fallback parser")

    # Map TELEGRAM_* to variables required by Dragon-Userbot (environs expects these names)
    if os.getenv("API_ID") is None and os.getenv("TELEGRAM_API_ID"):
        os.environ["API_ID"] = os.environ["TELEGRAM_API_ID"]
    if os.getenv("API_HASH") is None and os.getenv("TELEGRAM_API_HASH"):
        os.environ["API_HASH"] = os.environ["TELEGRAM_API_HASH"]
    # Database mapping
    if os.getenv("MONGO_DB_URL") is None and os.getenv("DRAGON_DB_URL"):
        os.environ["MONGO_DB_URL"] = os.environ["DRAGON_DB_URL"]
    if os.getenv("DATABASE_URL") is None and os.getenv("DRAGON_DB_URL"):
        os.environ["DATABASE_URL"] = os.environ["DRAGON_DB_URL"]
    os.environ.setdefault("DATABASE_TYPE", "mongodb")
    os.environ.setdefault("DATABASE_NAME", "ftg")
    # Session mapping (try several common names)
    if os.getenv("TELEGRAM_STRING_SESSION"):
        for k in ("SESSION_STRING", "STRING_SESSION", "SESSION"):
            os.environ.setdefault(k, os.environ["TELEGRAM_STRING_SESSION"])

    # One-time preflight: if we have a session string but no my_account.session file,
    # create it so Dragon-Userbot won't prompt for phone/token.
    try:
        session_file = FTG_REPO_PATH / "my_account.session"
        sess = os.getenv("TELEGRAM_STRING_SESSION") or os.getenv("SESSION_STRING") or os.getenv("STRING_SESSION")
        if sess and not session_file.exists():
            from pyrogram import Client  # type: ignore
            api_id = int(os.getenv("API_ID") or os.getenv("TELEGRAM_API_ID") or 0)
            api_hash = os.getenv("API_HASH") or os.getenv("TELEGRAM_API_HASH") or ""
            if api_id and api_hash:
                print("[run_dragon.py] Creating my_account.session from TELEGRAM_STRING_SESSION...")
                # Ensure working directory is repo so the file is created in the right place
                os.chdir(str(FTG_REPO_PATH))
                with Client("my_account", api_id=api_id, api_hash=api_hash, session_string=sess) as app:  # type: ignore
                    pass
    except Exception as e:
        print(f"[run_dragon.py] Preflight session creation failed: {e}", file=sys.stderr)

    # Workaround for `RuntimeError: Task attached to a different loop` on macOS
    if platform.system() == "Darwin":
        print("[run_dragon.py] Applying macOS asyncio policy workaround")
        # uvloop is not used in Dragon-Userbot, so this should be safe.
        # This is a common fix for Pyrogram on newer Python versions on macOS.
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    run_main()
