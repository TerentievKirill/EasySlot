import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
AVAILABLE = "доступен для записи"
BOOKING_PREFIX = "запись:"


def service():
    token_file = os.environ["GOOGLE_TOKEN_FILE"]
    credentials = Credentials.from_authorized_user_file(token_file, SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials.valid:
        raise RuntimeError("Google OAuth credentials invalid; authorize again")
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def events(master, start, end):
    api = service()
    params = dict(
        calendarId=master["calendar_id"],
        timeMin=start.astimezone(timezone.utc).isoformat(),
        timeMax=end.astimezone(timezone.utc).isoformat(),
        singleEvents=True, orderBy="startTime", maxResults=2500
    )
    items = []
    while True:
        result = api.events().list(**params).execute()
        items.extend(result.get("items", []))
        if not result.get("nextPageToken"):
            return items
        params["pageToken"] = result["nextPageToken"]


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
        title = event.get("summary", "").strip().casefold()
        if title == AVAILABLE:
            available.append((first, last, event))
        elif title.startswith(BOOKING_PREFIX):
            booked.append((first, last))
    return available, booked


def free_slots(master, start, end):
    available, booked = intervals(master, start, end)
    duration = timedelta(minutes=master["slot_minutes"])
    result = set()
    for a, b, _ in available:
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
    # Find the availability window that contains the selected hour.
    available, booked = intervals(master, start, end)
    if any(start < b and end > a for a, b in booked):
        raise ValueError("Slot already booked")
    window = next(((a, b, e) for a, b, e in available if a <= start and end <= b), None)
    if window is None:
        raise ValueError("Availability window not found")
    a, b, source = window
    api = service()
    calendar_id = master["calendar_id"]

    def timing(first, last):
        return {
            "start": {"dateTime": first.isoformat(), "timeZone": master["timezone"]},
            "end": {"dateTime": last.isoformat(), "timeZone": master["timezone"]},
        }

    body = {
        "summary": f"Запись: {name}",
        "description": f"Клиент: {name}\nТелефон: {phone}\nВремя: {start:%d.%m.%Y %H:%M}–{end:%H:%M}",
        **timing(start, end),
    }
    booking = api.events().insert(calendarId=calendar_id, body=body).execute()

    # Remove the booked hour from the availability event. Keep the original
    # event for one remainder and create a second one if the hour was in the middle.
    try:
        remaining = [(a, start)] if a < start else []
        if end < b:
            remaining.append((end, b))
        if remaining:
            first, last = remaining[0]
            api.events().patch(
                calendarId=calendar_id, eventId=source["id"],
                body=timing(first, last)
            ).execute()
            for first, last in remaining[1:]:
                api.events().insert(
                    calendarId=calendar_id,
                    body={"summary": "Доступен для записи", **timing(first, last)}
                ).execute()
        else:
            api.events().delete(calendarId=calendar_id, eventId=source["id"]).execute()
    except Exception:
        # Booking is already present and will block duplicate reservations.
        # Surface the error so an operator can repair the calendar manually.
        raise

    return booking
