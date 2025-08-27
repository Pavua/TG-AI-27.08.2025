from __future__ import annotations

from telethon import events

from ..utils.llm_client import chat as llm_chat
from ..utils.text import trim


SYSTEM_PROMPT_DEFAULT = "You are a concise helpful assistant."


def setup(client):
    @client.on(events.NewMessage(pattern=r"^\.ai\s+(.+)", outgoing=True))
    async def ai_cmd(e):
        prompt = e.pattern_match.group(1)
        try:
            ans = await llm_chat(prompt, system=SYSTEM_PROMPT_DEFAULT)
        except Exception as exc:  # noqa: BLE001
            ans = f"LLM error: {exc}"
        await e.reply(trim(ans))

    @client.on(events.NewMessage(pattern=r"^\.sum$", outgoing=True))
    async def sum_cmd(e):
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
    async def tr_cmd(e):
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
