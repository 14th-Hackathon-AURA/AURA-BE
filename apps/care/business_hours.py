"""Shared weekly opening-hours rules for availability and reservation writes."""
import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone


STORE_TIMEZONE = ZoneInfo("Asia/Seoul")
SLOT_DURATION = timedelta(minutes=30)
DAYS = "월화수목금토일"


class UnknownBusinessHours(ValueError):
    pass


def parse_business_hours(value):
    """Return seven daily intervals; reject unknown or ambiguous schedules.

    Supported: 매일 10:00-19:00, 월-목 ... / 금-일 ..., 일 휴무.
    Omitted weekdays are closed. Overnight hours are deliberately unsupported.
    """
    if not value or not value.strip():
        raise UnknownBusinessHours("매장 영업시간이 등록되지 않았습니다. 매장에 문의해 주세요.")
    schedule = {}
    for part in value.strip().split("/"):
        match = re.fullmatch(
            r"\s*(매일|[월화수목금토일](?:\s*[-~]\s*[월화수목금토일])?)\s+"
            r"(휴무|\d{1,2}:\d{2}\s*[-~]\s*\d{1,2}:\d{2})\s*", part
        )
        if not match:
            raise UnknownBusinessHours("매장 영업시간 형식을 확인해 주세요.")
        day_text, hours = match.groups()
        days = re.findall(r"[월화수목금토일]", day_text)
        if day_text == "매일":
            weekdays = list(range(7))
        else:
            start, end = DAYS.index(days[0]), DAYS.index(days[-1])
            weekdays = [(start + offset) % 7 for offset in range((end - start) % 7 + 1)]
        interval = None
        if hours != "휴무":
            try:
                start_text, end_text = re.split(r"\s*[-~]\s*", hours)
                opening = time(*map(int, start_text.split(":")))
                closing = time(*map(int, end_text.split(":")))
                if opening >= closing:
                    raise ValueError
                interval = (opening, closing)
            except ValueError as exc:
                raise UnknownBusinessHours("매장 영업시간 범위를 확인해 주세요.") from exc
        for weekday in weekdays:
            if weekday in schedule:
                raise UnknownBusinessHours("매장 영업시간의 요일이 중복되어 있습니다.")
            schedule[weekday] = interval
    return schedule


def reservation_slots(opening_hours, selected_date):
    interval = parse_business_hours(opening_hours).get(selected_date.weekday())
    if interval is None:
        return []
    opening, closing = interval
    current = datetime.combine(selected_date, opening, tzinfo=STORE_TIMEZONE)
    end = datetime.combine(selected_date, closing, tzinfo=STORE_TIMEZONE)
    # Preserve the existing :00 / :30 reservation grid, even for odd opening times.
    if current.minute % 30:
        current += timedelta(minutes=30 - current.minute % 30)
    slots = []
    while current + SLOT_DURATION <= end:
        slots.append(current)
        current += SLOT_DURATION
    return slots


def local_visit_datetime(value):
    return timezone.localtime(value, STORE_TIMEZONE)
