import asyncio
import logging
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .db import initialize, find_master
from .calendar_api import free_slots, create_booking
from .telegram import notify
from .services import categories_for, find_service

log = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")
locks = {}

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(title="EasySlot", lifespan=lifespan)

def master_for(request):
    # Trust Host only when reverse proxy preserves/validates it.
    hostname = request.headers.get("host", "").split(":")[0].lower().rstrip(".")
    master = find_master(hostname)
    if not master:
        raise HTTPException(404, "Мастер не найден")
    return master

def window(master):
    tz = ZoneInfo(master["timezone"])
    now = datetime.now(tz)
    return now, now + timedelta(days=30)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    master = master_for(request)
    filename = master["template"]
    if not re.fullmatch(r"[a-zA-Z0-9_-]+\.html", filename):
        raise HTTPException(500, "Invalid template")
    return templates.TemplateResponse(request, filename, {"master": master})

@app.get("/api/slots")
def slots(request: Request, service_id: str | None = Query(default=None)):
    master = master_for(request)
    service_info = resolve_service(master, service_id)
    start, end = window(master)
    try:
        return {"slots": free_slots(
            master, start, end,
            duration_minutes=service_info["duration_minutes"] if service_info else None,
            step_minutes=30 if service_info else 60,
        ), "timezone": master["timezone"]}
    except Exception:
        log.exception("Failed to load slots")
        raise HTTPException(503, "Календарь временно недоступен")

@app.get("/api/services")
def services(request: Request):
    return {"categories": categories_for(master_for(request))}

def resolve_service(master, service_id):
    if not categories_for(master):
        if service_id is not None:
            raise HTTPException(422, "Для этого мастера выбор услуг не предусмотрен")
        return None
    if not service_id:
        raise HTTPException(422, "Выберите услугу")
    service_info = find_service(master, service_id)
    if not service_info:
        raise HTTPException(422, "Неизвестная услуга")
    return service_info

class Booking(BaseModel):
    slot: datetime
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=5, max_length=32)
    service_id: str | None = Field(default=None, max_length=64)

@app.post("/api/book")
async def book(request: Request, data: Booking):
    master = master_for(request)
    service_info = resolve_service(master, data.service_id)
    if data.slot.tzinfo is None:
        raise HTTPException(400, "Укажите часовой пояс")
    if not re.fullmatch(r"[+0-9()\s-]{5,32}", data.phone):
        raise HTTPException(422, "Неверный формат телефона")
    tz = ZoneInfo(master["timezone"])
    selected = data.slot.astimezone(tz)
    lock = locks.setdefault(master["calendar_id"], asyncio.Lock())
    async with lock:
        start, end = window(master)
        try:
            available = await asyncio.to_thread(
                free_slots, master, start, end,
                duration_minutes=service_info["duration_minutes"] if service_info else None,
                step_minutes=30 if service_info else 60,
            )
            if selected.isoformat() not in available:
                raise HTTPException(409, "Это время уже занято")
            event = await asyncio.to_thread(
                create_booking, master, selected,
                data.name.strip(), data.phone.strip(), service_info,
            )
        except HTTPException:
            raise
        except Exception:
            log.exception("Failed to create booking")
            raise HTTPException(503, "Не удалось сохранить запись")
    try:
        await notify(master, data.name.strip(), data.phone.strip(), selected, service_info)
    except Exception:
        log.exception("Telegram notification failed; booking exists")
    return {"ok": True, "event_id": event["id"]}
