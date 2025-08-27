import asyncio
import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession


async def main():
    api_id = int(os.getenv("TELEGRAM_API_ID", "0") or 0)
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    if not api_id or not api_hash:
        print("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in env or .env")
        return
    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        print("STRING_SESSION:")
        print(client.session.save())


if __name__ == "__main__":
    asyncio.run(main())
