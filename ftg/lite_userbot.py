from __future__ import annotations

import asyncio
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from .utils.llm_client import chat as llm_chat
from .utils.text import trim


SYSTEM_PROMPT_DEFAULT = "You are a concise helpful assistant."


async def run() -> None:
    api_id = int(os.getenv("TELEGRAM_API_ID", "0") or 0)
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    string_session = os.getenv("STRING_SESSION")
    if not api_id or not api_hash:
        raise SystemExit("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env")

    # Prefer StringSession to avoid sqlite locks. If not provided, create new.
    if not string_session:
        print("[FTG-LITE] STRING_SESSION not found. You will be prompted to login; a new string will be created.")
        session = StringSession()
    else:
        session = StringSession(string_session)

    client = TelegramClient(session, api_id, api_hash)
    await client.start()
    # After successful start, if we created a new StringSession, print it once
    if not string_session:
        try:
            ss = client.session.save()
            print("[FTG-LITE] STRING_SESSION (store in .env):\n" + ss)
        except Exception:
            pass

    @client.on(events.NewMessage(pattern=r"^\.ai\s+(.+)", outgoing=True))
    async def ai_cmd(e):  # type: ignore[no-redef]
        prompt = e.pattern_match.group(1)
        try:
            ans = await llm_chat(prompt, system=SYSTEM_PROMPT_DEFAULT)
        except Exception as exc:  # noqa: BLE001
            ans = f"LLM error: {exc}"
        await e.reply(trim(ans))

    @client.on(events.NewMessage(pattern=r"^\.sum$", outgoing=True))
    async def sum_cmd(e):  # type: ignore[no-redef]
        if not e.is_reply:
            return await e.reply("Reply to a message to summarize.")
        msg = await e.get_reply_message()
        content = (msg.message or "").strip()
        if not content:
            return await e.reply("Nothing to summarize.")
        prompt = f"Summarize concisely in 3-5 bullet points. Text:\n\n{content}"
        try:
            ans = await llm_chat(prompt, system=SYSTEM_PROMPT_DEFAULT)
        except Exception as exc:  # noqa: BLE001
            ans = f"LLM error: {exc}"
        await e.reply(trim(ans))

    @client.on(events.NewMessage(pattern=r"^\.tr\s+(ru|en|es|uk)$", outgoing=True))
    async def tr_cmd(e):  # type: ignore[no-redef]
        if not e.is_reply:
            return await e.reply("Reply to a message to translate.")
        target = e.pattern_match.group(1)
        msg = await e.get_reply_message()
        content = (msg.message or "").strip()
        if not content:
            return await e.reply("Nothing to translate.")
        prompt = (
            f"Translate the following text to {target}. Preserve meaning and tone.\n\n{content}"
        )
        try:
            ans = await llm_chat(prompt, system=SYSTEM_PROMPT_DEFAULT)
        except Exception as exc:  # noqa: BLE001
            ans = f"LLM error: {exc}"
        await e.reply(trim(ans))

    print("[FTG-LITE] Running. Use .ai/.sum/.tr in Saved Messages.")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(run())


