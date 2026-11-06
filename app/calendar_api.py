import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

def service():
    token_file = os.environ["GOOGLE_TOKEN_FILE"]
    credentials = Credentials.from_authorized_user_file(token_file, SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials.valid:
        raise RuntimeError("Google OAuth credentials invalid; authorize again")
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)

def events(master, start, end):
    result = service().events().list(
        calendarId=master["calendar_id"],
        timeMin=start.astimezone(timezone.utc).isoformat(),
        timeMax=end.astimezone(timezone.utc).isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=2500
    ).execute()
    items = result.get("items", [])
    while result.get("nextPageToken"):
        result = service().events().list(
            calendarId=master["calendar_id"],
            timeMin=start.astimezone(timezone.utc).isoformat(),
            timeMax=end.astimezone(timezone.utc).isoformat(),
            singleEvents=True, orderBy="startTime", maxResults=2500,
            pageToken=result["nextPageToken"]
        ).execute()
        items += result.get("items", [])
    return items

def intervals(master, start, end):
    tz = ZoneInfo(master["timezone"])
    available, booked = [], []
    for event in events(master, start, end):
        if event.get("status") == "cancelled":
            continue
        a, b = event.get("start", {}), event.get("end", {})
        if "dateTime" not in a or "dateTime" not in b:
            continue
        first = datetime.fromisoformat(a["dateTime"]).astimezone(tz)
        last = datetime.fromisoformat(b["dateTime"]).astimezone(tz)
        if last <= first:
            continue
        if event.get("summary", "").strip().casefold() == "доступен для записи":
            available.append((first, last))
        elif event.get("extendedProperties", {}).get("private", {}).get("easyslot_booking") == "1":
            booked.append((first, last))
    return available, booked

def free_slots(master, start, end):
    available, booked = intervals(master, start, end)
    duration = timedelta(minutes=master["slot_minutes"])
    result = set()
    for a, b in available:
        # Hourly grid aligned to local wall clock (09:00, 10:00, ...).
        cursor = a.replace(minute=0, second=0, microsecond=0)
        if cursor < a:
            cursor += timedelta(hours=1)
        while cursor + duration <= b:
            if cursor >= start and cursor + duration <= end and not any(
                cursor < busy_end and cursor + duration > busy_start
                for busy_start, busy_end in booked
            ):
                result.add(cursor.isoformat())
            cursor += timedelta(hours=1)
    return sorted(result)

def create_booking(master, start, name, phone):
    end = start + timedelta(minutes=master["slot_minutes"])
    body = {
        "summary": f"Запись: {name}",
        "description": f"Клиент: {name}\nТелефон: {phone}\nСоздано EasySlot",
        "start": {"dateTime": start.isoformat(), "timeZone": master["timezone"]},
        "end": {"dateTime": end.isoformat(), "timeZone": master["timezone"]},
        "extendedProperties": {"private": {"easyslot_booking": "1"}}
    }
    return service().events().insert(calendarId=master["calendar_id"], body=body).execute()
