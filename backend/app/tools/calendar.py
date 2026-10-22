"""C3: offer free slots from Chandru's calendar and book with a Meet link, via Composio MCP (ADR-010)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import Settings
from app.integrations.composio_mcp import find_intervals, pick_args


@dataclass
class Slot:
    id: str
    start: datetime
    end: datetime

    def label(self, tz: str) -> str:
        z = ZoneInfo(tz)
        s = self.start.astimezone(z)
        return f"{s:%a %d %b, %I:%M %p}".replace(" 0", " ")


def _candidates(now: datetime, s: Settings) -> list[tuple[datetime, datetime]]:
    zone = ZoneInfo(s.timezone)
    start_h, end_h = s.meeting_work_hours
    dur = timedelta(minutes=s.meeting_minutes)
    out = []
    earliest = now + timedelta(hours=3)
    for d in range(s.meeting_days_ahead + 1):
        day = (now + timedelta(days=d)).astimezone(zone).date()
        if day.weekday() >= 5:
            continue
        t = datetime(day.year, day.month, day.day, start_h, tzinfo=zone)
        while t + dur <= datetime(day.year, day.month, day.day, end_h, tzinfo=zone):
            if t >= earliest:
                out.append((t, t + dur))
            t += timedelta(minutes=30)
    return out


def _free(cands, busy, buffer_min: int):
    buf = timedelta(minutes=buffer_min)
    return [(a, b) for a, b in cands if all(b + buf <= bs or a - buf >= be for bs, be in busy)]


PREFERRED_HOURS = [11, 15, 12, 16, 14]  # a person offers a mix: late morning, mid-afternoon, noon...


def _spread(free, n: int) -> list[tuple[datetime, datetime]]:
    """One slot per day on different days, each near a different time of day."""
    by_day: dict = {}
    for a, b in free:
        by_day.setdefault(a.date(), []).append((a, b))
    picked = []
    for i, day in enumerate(sorted(by_day)[:n]):
        want = PREFERRED_HOURS[i % len(PREFERRED_HOURS)]
        picked.append(min(by_day[day], key=lambda ab: abs(ab[0].hour + ab[0].minute / 60 - want)))
    for a, b in free:  # fewer free days than n: fill from what's left
        if len(picked) >= n:
            break
        if (a, b) not in picked:
            picked.append((a, b))
    return sorted(picked)


def _dt(v: str) -> datetime:
    return datetime.fromisoformat(str(v).replace("Z", "+00:00"))


async def free_slots(s: Settings, now: datetime, cx) -> list[Slot]:
    """Busy/free times from Google Calendar via Composio MCP; slot choice stays deterministic code."""
    cands = _candidates(now, s)
    if not cands:
        return []
    args = pick_args(cx.schema("free_slots"), {
        "time_min": ["time_min", "timeMin", "start_time", "start_datetime"],
        "time_max": ["time_max", "timeMax", "end_time", "end_datetime"],
        "items": ["items", "calendar_ids", "calendars"],
        "timezone": ["timezone", "time_zone", "timeZone"],
    }, {"time_min": cands[0][0].isoformat(), "time_max": cands[-1][1].isoformat(),
        "items": [s.calendar_id], "timezone": s.timezone})
    data = await cx.call("free_slots", args)
    busy = [(_dt(a), _dt(b)) for a, b in find_intervals(data, "busy")]
    free_windows = [(_dt(a), _dt(b)) for a, b in find_intervals(data, "free")]
    ok = _free(cands, busy, s.meeting_buffer_min)
    if not busy and free_windows:  # tool returned free windows only: keep candidates fully inside one
        ok = [(a, b) for a, b in cands if any(fa <= a and b <= fb for fa, fb in free_windows)]
    chosen = _spread(ok, s.meeting_slots_offered)
    return [Slot(id=f"s{i + 1}", start=a, end=b) for i, (a, b) in enumerate(chosen)]


def _find(data, keys: tuple[str, ...]):
    if isinstance(data, dict):
        for k in keys:
            if data.get(k):
                return data[k]
        for v in data.values():
            hit = _find(v, keys)
            if hit:
                return hit
    elif isinstance(data, list):
        for v in data:
            hit = _find(v, keys)
            if hit:
                return hit
    return None


async def book(s: Settings, slot: Slot, *, attendee_email: str, attendee_name: str | None,
               idempotency_key: str, about: str | None, cx) -> dict:
    """Create the event with a Google Meet link via Composio MCP. Idempotency is enforced by our bookings table."""
    zone = ZoneInfo(s.timezone)
    local = "%Y-%m-%dT%H:%M:%S"  # GOOGLECALENDAR_CREATE_EVENT wants local time + a separate timezone field
    args = pick_args(cx.schema("create_event"), {
        "summary": ["summary", "title"],
        "description": ["description"],
        "start": ["start_datetime", "start_time", "start"],
        "end": ["end_datetime", "end_time", "end"],   # not event_duration_minutes: that one only takes 0-59
        "attendees": ["attendees", "attendee_emails"],
        "meet": ["create_meeting_room", "add_meet_link", "conference", "create_conference"],
        "timezone": ["timezone", "time_zone", "timeZone"],
        "calendar": ["calendar_id", "calendarId"],
        "notify": ["send_updates", "sendUpdates"],
    }, {"summary": f"Chat with {attendee_name or attendee_email} × Chandru",
        "description": about or "Booked via itzmechandruganeshan.github.io",
        "start": slot.start.astimezone(zone).strftime(local), "end": slot.end.astimezone(zone).strftime(local),
        "attendees": [attendee_email], "meet": True, "timezone": s.timezone, "calendar": s.calendar_id,
        "notify": "all"})
    ev = await cx.call("create_event", args)
    event_id = _find(ev, ("id", "event_id", "eventId"))
    if not event_id:
        raise RuntimeError(f"create_event returned no id: {str(ev)[:200]}")
    meet = _find(ev, ("hangoutLink", "hangout_link", "meet_link", "meeting_url"))
    return {"event_id": str(event_id), "meet_url": meet}
