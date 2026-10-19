from datetime import datetime, time, timedelta

from django.utils import timezone


def doha_day_bounds(date):
    """The instants where a Doha calendar Day starts and ends (exclusive), ADR 0005.

    TIME_ZONE is Asia/Qatar, so the default timezone is the office's zone.
    """
    zone = timezone.get_default_timezone()
    start = datetime.combine(date, time.min, tzinfo=zone)
    end = datetime.combine(date + timedelta(days=1), time.min, tzinfo=zone)
    return start, end
