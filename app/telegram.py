import os
import httpx

from .services import format_price

async def notify(master, name, phone, start, service_info=None):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = master.get("telegram_chat_id")
    if not token or not chat:
        return
    service_line = (f"Услуга: {service_info['category']} / {service_info['name']} "
                    f"({service_info['duration_minutes']} мин)\n") if service_info else ""
    price_line = (f"Стоимость: {format_price(service_info['price_kzt'])}\n"
                  if service_info and "price_kzt" in service_info else "")
    message = (f"Новая запись — {master['name']}\n"
               f"{start.strftime('%d.%m.%Y %H:%M')}\n"
               f"{service_line}"
               f"{price_line}"
               f"Клиент: {name}\nТелефон: {phone}")
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": message}
        )
        response.raise_for_status()
