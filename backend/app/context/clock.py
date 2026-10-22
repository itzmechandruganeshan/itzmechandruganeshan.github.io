"""Server-side "now" (FR A9). The LLM is told the time; it never works it out."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.data import Knowledge

DAY_PARTS = [  # (start_hour, name)
    (0, "late_night"), (5, "early_morning"), (8, "morning"), (12, "afternoon"),
    (17, "evening"), (21, "night"),
]
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass(frozen=True)
class ClockContext:
    now: datetime
    day_part: str
    weekday: str
    weekend: bool
    status: str
    status_line: list[str]
    holiday: dict | None
    next_holiday: tuple[dict, int] | None  # (holiday, days_until)
    pacing_multiplier: float
    visitor_tz: str | None
    visitor_local: datetime | None

    @property
    def greeting_part(self) -> str:
        return {
            "early_morning": "morning", "morning": "morning", "afternoon": "afternoon",
            "evening": "evening", "night": "night", "late_night": "night",
        }[self.day_part]

    def block(self) -> str:
        """Compact text block for the LLM prompt."""
        lines = [
            f"now: {self.now:%a %d %b %Y, %H:%M} IST · day_part: {self.day_part} · weekend: {'yes' if self.weekend else 'no'}",
            f"what chandru is doing: {self.status} ({' / '.join(self.status_line)})",
        ]
        if self.holiday:
            lines.append(f"today is {self.holiday['name']}")
        elif self.next_holiday and self.next_holiday[1] <= 7:
            h, d = self.next_holiday
            lines.append(f"{h['name']} is in {d} day{'s' if d != 1 else ''}")
        if self.visitor_local is not None:
            lines.append(f"visitor local time: {self.visitor_local:%H:%M} ({_day_part(self.visitor_local.hour)}) {self.visitor_tz}")
        return "\n".join(lines)


def _day_part(hour: int) -> str:
    part = DAY_PARTS[0][1]
    for start, name in DAY_PARTS:
        if hour >= start:
            part = name
    return part


def _parse_hm(s: str) -> time:
    h, m = s.split(":")
    h = int(h)
    return time(23, 59, 59) if h == 24 else time(h, int(m))


def _in_window(t: time, start: str, end: str) -> bool:
    a, b = _parse_hm(start), _parse_hm(end)
    if a <= b:
        return a <= t < b or (b == time(23, 59, 59) and t >= a)
    return t >= a or t < b  # wraps midnight


def _late_night_today(routine: dict, d: date) -> bool:
    cfg = routine.get("late_night_work") or {}
    p = float(cfg.get("probability", 0))
    if d.weekday() >= 5 or p <= 0:
        return False
    h = int(hashlib.sha256(d.isoformat().encode()).hexdigest()[:8], 16)
    return (h % 1000) / 1000 < p


def routine_status(routine: dict, now: datetime) -> str:
    t = now.time()
    # The late-night window can spill past midnight, so check today's and yesterday's flag.
    cfg = routine.get("late_night_work") or {}
    if cfg:
        start, end = cfg["window"]["from"], cfg["window"]["to"]
        if _in_window(t, start, end):
            day = now.date() if t >= _parse_hm(start) else now.date() - timedelta(days=1)
            if _late_night_today(routine, day):
                return cfg.get("status", "late_night_work")
    wd = now.weekday()
    key = "saturday" if wd == 5 else "sunday" if wd == 6 else "weekday"
    for slot in routine.get(key, []):
        if _in_window(t, slot["from"], slot["to"]):
            return slot["status"]
    return "evening"


def _holidays(kb: Knowledge, today: date) -> tuple[dict | None, tuple[dict, int] | None]:
    current, upcoming = None, None
    for h in kb.holidays:
        d = h["date"] if isinstance(h["date"], date) else date.fromisoformat(str(h["date"]))
        delta = (d - today).days
        if delta == 0:
            current = h
        elif delta > 0 and (upcoming is None or delta < upcoming[1]):
            upcoming = (h, delta)
    return current, upcoming


def build_clock(
    kb: Knowledge,
    *,
    now: datetime | None = None,
    visitor_tz: str | None = None,
    tz: str = "Asia/Kolkata",
    rng: random.Random | None = None,
) -> ClockContext:
    zone = ZoneInfo(tz)
    now = (now or datetime.now(zone)).astimezone(zone)
    rng = rng or random.Random()
    status = routine_status(kb.routine, now)
    lines = kb.routine.get("status_lines", {}).get(status) or [["around"]]
    mult = kb.routine.get("pacing_multipliers", {})
    holiday, upcoming = _holidays(kb, now.date())
    visitor_local = None
    if visitor_tz:
        try:
            visitor_local = now.astimezone(ZoneInfo(visitor_tz))
            if visitor_local.utcoffset() == now.utcoffset():
                visitor_local = None  # same zone as Chandru, nothing interesting to say
        except (ZoneInfoNotFoundError, ValueError):
            visitor_tz = None
    return ClockContext(
        now=now,
        day_part=_day_part(now.hour),
        weekday=WEEKDAYS[now.weekday()],
        weekend=now.weekday() >= 5,
        status=status,
        status_line=rng.choice(lines),
        holiday=holiday,
        next_holiday=upcoming,
        pacing_multiplier=float(mult.get(status, mult.get("default", 1.0))),
        visitor_tz=visitor_tz,
        visitor_local=visitor_local,
    )


def relative_day(then: datetime, now: datetime) -> str:
    """'today', 'yesterday', 'last week'... computed in code for news and dates."""
    days = (now.date() - then.astimezone(now.tzinfo).date()).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 14:
        return "last week"
    if days < 31:
        return f"{days // 7} weeks ago"
    return "a while back"
