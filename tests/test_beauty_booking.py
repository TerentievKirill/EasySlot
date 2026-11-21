import sqlite3
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app import calendar_api, db, main
from app.services import CATALOGS, find_service


MASTER = {
    "name": "Тестовый мастер",
    "calendar_id": "test@group.calendar.google.com",
    "timezone": "Asia/Almaty",
    "slot_minutes": 60,
    "catalog": "beauty",
    "template": "beauty.html",
}


def test_catalog_ids_unique_and_durations_valid():
    services = [item for group in CATALOGS["beauty"] for item in group["services"]]
    assert len({item["id"] for item in services}) == len(services)
    assert len(CATALOGS["beauty"]) == 3
    assert all(item["duration_minutes"] > 0 for item in services)
    assert find_service(MASTER, "manicure-gel")["duration_minutes"] == 120


def test_long_service_requires_full_free_window():
    tz = ZoneInfo("Asia/Almaty")
    start = datetime(2026, 11, 23, 9, tzinfo=tz)
    end = start + timedelta(hours=5)
    availability = [(start, end, {"id": "available"})]
    booked = [(start + timedelta(hours=2), start + timedelta(hours=3))]
    with patch.object(calendar_api, "intervals", return_value=(availability, booked)):
        long_slots = calendar_api.free_slots(MASTER, start, end, duration_minutes=120, step_minutes=30)
        short_slots = calendar_api.free_slots(MASTER, start, end, duration_minutes=30, step_minutes=30)

    assert start.isoformat() in long_slots
    assert (start + timedelta(minutes=30)).isoformat() not in long_slots
    assert (start + timedelta(hours=1)).isoformat() not in long_slots
    assert (start + timedelta(hours=3)).isoformat() in long_slots
    assert (start + timedelta(hours=1, minutes=30)).isoformat() in short_slots


def test_old_master_keeps_hourly_fixed_duration():
    tz = ZoneInfo("Asia/Almaty")
    start = datetime(2026, 11, 23, 9, tzinfo=tz)
    with patch.object(calendar_api, "intervals", return_value=([(start, start + timedelta(hours=2), {})], [])):
        assert calendar_api.free_slots(MASTER, start, start + timedelta(hours=2)) == [
            start.isoformat(), (start + timedelta(hours=1)).isoformat()
        ]


def test_beauty_window_shows_exactly_fourteen_calendar_dates():
    start, end = main.window(MASTER)
    assert main.booking_window_days(MASTER) == main.BEAUTY_BOOKING_WINDOW_DAYS == 14
    assert (end.date() - start.date()).days == 14
    assert (end.hour, end.minute, end.second, end.microsecond) == (0, 0, 0, 0)

    old_master = {**MASTER, "catalog": ""}
    old_start, old_end = main.window(old_master)
    assert main.booking_window_days(old_master) == 30
    assert old_end - old_start == timedelta(days=30)


def test_century_long_availability_only_generates_slots_in_horizon():
    tz = ZoneInfo("Asia/Almaty")
    start = datetime(2026, 11, 23, 9, tzinfo=tz)
    end = start + timedelta(days=14)
    availability = [(
        datetime(2020, 1, 1, tzinfo=tz),
        datetime(2100, 1, 1, tzinfo=tz),
        {"id": "century-long"},
    )]
    with patch.object(calendar_api, "intervals", return_value=(availability, [])):
        slots = calendar_api.free_slots(MASTER, start, end, duration_minutes=30, step_minutes=30)
    assert len(slots) == 14 * 48
    assert slots[0] == start.isoformat()
    assert slots[-1] == (end - timedelta(minutes=30)).isoformat()


def test_api_requires_known_service_and_passes_its_duration():
    slot = (datetime.now(ZoneInfo("Asia/Almaty")) + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0
    ).isoformat()
    with (patch.object(main, "find_master", return_value=MASTER),
          patch.object(main, "free_slots", return_value=[slot]) as free,
          patch.object(main, "create_booking", return_value={"id": "created"}) as create,
          patch.object(main, "notify", new_callable=AsyncMock) as notify):
        client = TestClient(main.app)
        assert client.get("/api/services").json()["categories"][0]["name"] == "Маникюр"
        assert client.get("/api/slots").status_code == 422
        assert client.get("/api/slots?service_id=nope").status_code == 422
        response = client.get("/api/slots?service_id=manicure-gel")
        assert response.status_code == 200
        assert response.json()["slots"] == [slot]
        assert response.json()["window_days"] == 14
        assert free.call_args.kwargs == {"duration_minutes": 120, "step_minutes": 30}

        response = client.post("/api/book", json={
            "slot": slot, "name": "Анна", "phone": "+77001234567", "service_id": "manicure-gel"
        })
        assert response.status_code == 200
        assert create.call_args.args[4]["name"] == "Маникюр с гель-лаком"
        assert create.call_args.args[4]["duration_minutes"] == 120
        assert notify.call_args.args[4]["category"] == "Маникюр"


def test_existing_master_booking_does_not_need_service():
    old_master = {**MASTER, "catalog": "", "template": "default.html"}
    slot = (datetime.now(ZoneInfo("Asia/Almaty")) + timedelta(days=1)).replace(
        hour=10, minute=0, second=0, microsecond=0
    ).isoformat()
    with (patch.object(main, "find_master", return_value=old_master),
          patch.object(main, "free_slots", return_value=[slot]) as free,
          patch.object(main, "create_booking", return_value={"id": "created"}) as create,
          patch.object(main, "notify", new_callable=AsyncMock)):
        client = TestClient(main.app)
        assert client.get("/api/slots").status_code == 200
        assert client.get("/api/slots").json()["window_days"] == 30
        assert free.call_args.kwargs == {"duration_minutes": None, "step_minutes": 60}
        response = client.post("/api/book", json={"slot": slot, "name": "Анна", "phone": "+77001234567"})
        assert response.status_code == 200
        assert create.call_args.args[4] is None


def test_beauty_photo_is_served_and_legacy_template_unchanged():
    client = TestClient(main.app)
    with patch.object(main, "find_master", return_value=MASTER):
        response = client.get("/", headers={"host": "beauty.heartlab.app"})
    assert response.status_code == 200
    assert 'src="/static/beauty-master.png"' in response.text
    assert "document.createElement('details')" in response.text
    assert "Время" in response.text

    photo = client.get("/static/beauty-master.png")
    assert photo.status_code == 200
    assert photo.headers["content-type"].startswith("image/png")
    assert photo.content.startswith(b"\x89PNG\r\n\x1a\n")

    old_master = {**MASTER, "template": "default.html", "catalog": ""}
    with patch.object(main, "find_master", return_value=old_master):
        old_page = client.get("/", headers={"host": "stella.heartlab.app"})
    assert old_page.status_code == 200
    assert "beauty-master.png" not in old_page.text


def test_calendar_event_contains_service_and_occupies_full_duration():
    tz = ZoneInfo("Asia/Almaty")
    start = datetime(2026, 11, 23, 10, tzinfo=tz)
    source = {"id": "availability"}
    calls = []

    class Operation:
        def __init__(self, result):
            self.result = result

        def execute(self):
            return self.result

    class Events:
        def insert(self, **kwargs):
            calls.append(("insert", kwargs))
            return Operation({"id": "booking-created"})

        def patch(self, **kwargs):
            calls.append(("patch", kwargs))
            return Operation({})

    class API:
        def events(self):
            return Events()

    service_info = find_service(MASTER, "manicure-gel")
    with (patch.object(calendar_api, "intervals", return_value=(
            [(start - timedelta(hours=1), start + timedelta(hours=4), source)], [])),
          patch.object(calendar_api, "service", return_value=API())):
        calendar_api.create_booking(MASTER, start, "Анна", "+77001234567", service_info)
    booking_body = calls[0][1]["body"]
    assert booking_body["end"]["dateTime"] == (start + timedelta(hours=2)).isoformat()
    assert "Маникюр с гель-лаком" in booking_body["summary"]
    assert "Услуга: Маникюр" in booking_body["description"]
    assert calls[1][1]["body"]["end"]["dateTime"] == start.isoformat()
    assert calls[2][1]["body"]["start"]["dateTime"] == (start + timedelta(hours=2)).isoformat()


def test_migration_preserves_existing_master(tmp_path):
    path = tmp_path / "existing.db"
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE masters (
        id INTEGER PRIMARY KEY, hostname TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
        calendar_id TEXT NOT NULL, telegram_chat_id TEXT,
        template TEXT NOT NULL DEFAULT 'default.html',
        slot_minutes INTEGER NOT NULL DEFAULT 60,
        timezone TEXT NOT NULL DEFAULT 'Asia/Almaty',
        active INTEGER NOT NULL DEFAULT 1)""")
    conn.execute("INSERT INTO masters(hostname,name,calendar_id) VALUES (?,?,?)",
                 ("example.org", "Старый мастер", "calendar@example.org"))
    conn.commit()
    conn.close()
    with patch.object(db, "PATH", str(path)):
        db.initialize()
        db.initialize()
        old_master = db.find_master("example.org")
    assert old_master["name"] == "Старый мастер"
    assert old_master["catalog"] == ""
