import asyncio
import logging
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .db import initialize, find_master
from .calendar_api import free_slots, create_booking
from .telegram import notify

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
def slots(request: Request):
    master = master_for(request)
    start, end = window(master)
    try:
        return {"slots": free_slots(master, start, end), "timezone": master["timezone"]}
    except Exception:
        log.exception("Failed to load slots")
        raise HTTPException(503, "Календарь временно недоступен")

class Booking(BaseModel):
    slot: datetime
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=5, max_length=32)

@app.post("/api/book")
async def book(request: Request, data: Booking):
    master = master_for(request)
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
            available = await asyncio.to_thread(free_slots, master, start, end)
            if selected.isoformat() not in available:
                raise HTTPException(409, "Это время уже занято")
            event = await asyncio.to_thread(create_booking, master, selected, data.name.strip(), data.phone.strip())
        except HTTPException:
            raise
        except Exception:
            log.exception("Failed to create booking")
            raise HTTPException(503, "Не удалось сохранить запись")
    try:
        await notify(master, data.name.strip(), data.phone.strip(), selected)
    except Exception:
        log.exception("Telegram notification failed; booking exists")
    return {"ok": True, "event_id": event["id"]}
