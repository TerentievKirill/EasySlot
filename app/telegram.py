import os
import httpx

async def notify(master, name, phone, start):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = master.get("telegram_chat_id")
    if not token or not chat:
        return
    message = (f"Новая запись — {master['name']}\n"
               f"{start.strftime('%d.%m.%Y %H:%M')}\n"
               f"Клиент: {name}\nТелефон: {phone}")
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": message}
        )
        response.raise_for_status()
