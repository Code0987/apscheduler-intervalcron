import pytest
import time
import os
from datetime import datetime, timedelta, time
from tzlocal import get_localzone
import pytz
import pickle
from pytz.tzinfo import DstTzInfo
from apscheduler.util import convert_to_datetime
from apscheduler.schedulers.background import BackgroundScheduler

from intervalcron import IntervalCronTrigger

timezone = pytz.utc

def test_everyday():
    now = timezone.localize(datetime(2020, 2, 1, 1, 0))
    trigger = IntervalCronTrigger(days=1, hour=2, start_date=now, timezone=timezone)

    expected = timezone.localize(datetime(2020, 2, 2, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 2, 3, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 2, 4, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual


def test_start_date_required():
    with pytest.raises(ValueError, match='start_date is required'):
        IntervalCronTrigger(days=1, timezone=timezone)


def test_negative_interval_raises():
    now = timezone.localize(datetime(2020, 2, 1, 0, 0))
    with pytest.raises(ValueError, match='must be >= 0'):
        IntervalCronTrigger(days=-1, start_date=now, timezone=timezone)
    with pytest.raises(ValueError, match='must be >= 0'):
        IntervalCronTrigger(weeks=-1, start_date=now, timezone=timezone)
    with pytest.raises(ValueError, match='must be >= 0'):
        IntervalCronTrigger(months=-1, start_date=now, timezone=timezone)


def test_zero_interval_without_cron_raises():
    now = timezone.localize(datetime(2020, 2, 1, 0, 0))
    with pytest.raises(ValueError, match='At least one of months, weeks, or days'):
        IntervalCronTrigger(start_date=now, timezone=timezone)


def test_zero_interval_with_day_defaults_to_one_month():
    now = timezone.localize(datetime(2020, 2, 1, 0, 0))
    trigger = IntervalCronTrigger(day='13', hour=2, start_date=now, timezone=timezone)

    from dateutil.relativedelta import relativedelta
    assert trigger.interval == relativedelta(months=1)

    expected = timezone.localize(datetime(2020, 2, 13, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 3, 13, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual


def test_zero_interval_with_day_of_week_defaults_to_one_week():
    now = timezone.localize(datetime(2020, 2, 1, 0, 0))
    trigger = IntervalCronTrigger(day_of_week='mon', hour=2, start_date=now, timezone=timezone)

    from dateutil.relativedelta import relativedelta
    assert trigger.interval == relativedelta(weeks=1)

    expected = timezone.localize(datetime(2020, 2, 3, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 2, 10, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual


def test_day_31_skips_short_months():
    """Months without a 31st must skip to the next 31st, not fire on the 1st."""
    now = timezone.localize(datetime(2020, 1, 1, 0, 0))
    trigger = IntervalCronTrigger(months=1, day='31', hour=2, start_date=now, timezone=timezone)

    expected = timezone.localize(datetime(2020, 1, 31, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 3, 31, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 5, 31, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 7, 31, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual


def test_day_31_from_mid_february():
    now = timezone.localize(datetime(2020, 2, 15, 0, 0))
    trigger = IntervalCronTrigger(
        months=1, day='31', hour=2,
        start_date=timezone.localize(datetime(2020, 1, 1)),
        timezone=timezone,
    )
    expected = timezone.localize(datetime(2020, 3, 31, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual


def test_fifteenth_and_friday_skips_non_matching_months():
    """Require both day=15 and Friday; never return a non-matching interval boundary."""
    now = timezone.localize(datetime(2020, 1, 1, 0, 0))
    trigger = IntervalCronTrigger(
        months=1, day='15', day_of_week='fri', hour=2,
        start_date=now, timezone=timezone,
    )
    # 2020-05-15 is a Friday
    expected = timezone.localize(datetime(2020, 5, 15, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    # Next Friday the 15th after that is 2021-01-15
    expected = timezone.localize(datetime(2021, 1, 15, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual


def test_1_weeks_mon():
    now = timezone.localize(datetime(2020, 2, 1, 0, 0))
    trigger = IntervalCronTrigger(weeks=1, day_of_week='mon', hour=2, start_date=now, timezone=timezone)

    expected = timezone.localize(datetime(2020, 2, 3, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

def test_1_weeks_mon_tue_wed():
    now = timezone.localize(datetime(2020, 2, 1, 0, 0))
    trigger = IntervalCronTrigger(weeks=1, day_of_week='mon,tue,wed', hour=2, start_date=now, timezone=timezone)
    
    expected = timezone.localize(datetime(2020, 2, 3, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual
    
    expected = timezone.localize(datetime(2020, 2, 4, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual
    
    expected = timezone.localize(datetime(2020, 2, 5, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual
    
    expected = timezone.localize(datetime(2020, 2, 10, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

def test_1_months_13th():
    now = timezone.localize(datetime(2020, 2, 1, 0, 0))
    trigger = IntervalCronTrigger(months=1, day='13', hour=2, start_date=now, timezone=timezone)
    
    expected = timezone.localize(datetime(2020, 2, 13, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 3, 13, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

def test_3_months_13th():
    now = timezone.localize(datetime(2020, 2, 1, 0, 0))
    trigger = IntervalCronTrigger(months=3, day='13', hour=2, start_date=now, timezone=timezone)
    
    expected = timezone.localize(datetime(2020, 2, 13, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 5, 13, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

def test_3_months_1stmon():
    now = timezone.localize(datetime(2020, 2, 1, 3, 0))
    trigger = IntervalCronTrigger(months=3, day='1st mon', hour=2, start_date=now, timezone=timezone)
    
    expected = timezone.localize(datetime(2020, 2, 3, 2, 0))
    actual = trigger.get_next_fire_time(now, now)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 5, 4, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

def test_1_months_lastday():
    now = timezone.localize(datetime(2020, 2, 13, 0, 0))
    trigger = IntervalCronTrigger(months=1, day='last', start_date=now, timezone=timezone)

    expected = timezone.localize(datetime(2020, 2, 29, 0, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 3, 31, 0, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 4, 30, 0, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 5, 31, 0, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

def test_1_months_firstday():
    now = timezone.localize(datetime(2020, 2, 13, 0, 0))
    trigger = IntervalCronTrigger(months=1, day='1', start_date=now, timezone=timezone)

    expected = timezone.localize(datetime(2020, 3, 1, 0, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 4, 1, 0, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

def test_1_months_firstday_2():
    now = timezone.localize(datetime(2020, 2, 1, 0, 0))
    trigger = IntervalCronTrigger(months=1, day='1', start_date=now, timezone=timezone)

    expected = timezone.localize(datetime(2020, 3, 1, 0, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 4, 1, 0, 0))
    actual = trigger.get_next_fire_time(timezone.localize(datetime(2020, 3, 1, 0, 5)), timezone.localize(datetime(2020, 3, 1, 2, 5)))
    assert expected == actual

def test_every_3_day():
    now = timezone.localize(datetime(2020, 3, 7, 0, 0))
    trigger = IntervalCronTrigger(days=3, hour=2, start_date=now, timezone=timezone)
    
    expected = timezone.localize(datetime(2020, 3, 10, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual
    
    expected = timezone.localize(datetime(2020, 3, 13, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual
    
    expected = timezone.localize(datetime(2020, 3, 16, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual
    
    expected = timezone.localize(datetime(2020, 3, 19, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

def test_every_3mo_on_last_fri():
    now = timezone.localize(datetime(2020, 1, 1, 0, 0))
    trigger = IntervalCronTrigger(months=3, day="last fri", hour=2, start_date=now, timezone=timezone)
    
    expected = timezone.localize(datetime(2020, 1, 31, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 4, 24, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 7, 31, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

def test_every_2yrs_on_1st_mon():
    now = timezone.localize(datetime(2000, 1, 1, 0, 0))
    trigger = IntervalCronTrigger(months=24, day="1st mon", hour=2, start_date=now, timezone=timezone)
    
    expected = timezone.localize(datetime(2000, 1, 3, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual
    
    expected = timezone.localize(datetime(2002, 1, 7, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

    expected = timezone.localize(datetime(2004, 1, 5, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

def test_next_iter_only():
    now = timezone.localize(datetime(2020, 2, 1, 2, 0))
    trigger = IntervalCronTrigger(days=1, hour=2, start_date=now, timezone=timezone)

    expected = timezone.localize(datetime(2020, 2, 2, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 2, 3, 2, 0))
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

def test_start_date():
    now = timezone.localize(datetime(2020, 2, 1, 2, 0))
    trigger = IntervalCronTrigger(days=3, hour=7, minute=3, start_date=now, timezone=timezone)

    expected = timezone.localize(datetime(2020, 2, 4, 7, 3))
    actual = trigger.get_next_fire_time(timezone.localize(datetime(2020, 2, 1, 7, 7)), timezone.localize(datetime(2020, 2, 1, 7, 10)))
    assert expected == actual

def test_end_date():
    now = timezone.localize(datetime(2020, 2, 1, 2, 0))
    end = timezone.localize(datetime(2020, 2, 3, 0, 0))
    trigger = IntervalCronTrigger(days=1, hour=2, start_date=now, end_date=end, timezone=timezone)

    expected = timezone.localize(datetime(2020, 2, 2, 2, 0))
    actual = trigger.get_next_fire_time(None, now)
    assert expected == actual

    expected = None
    actual = trigger.get_next_fire_time(actual, actual)
    assert expected == actual

def test_large_gap_1():
    start = timezone.localize(datetime(2020, 2, 1, 1, 0))
    trigger = IntervalCronTrigger(days=1, hour=2, start_date=start, timezone=timezone)

    expected = timezone.localize(datetime(2020, 2, 2, 2, 0))
    actual = trigger.get_next_fire_time(None, start)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 2, 9, 2, 0))
    actual = trigger.get_next_fire_time(timezone.localize(datetime(2020, 2, 2, 2, 3)), timezone.localize(datetime(2020, 2, 8, 2, 9)))
    assert expected == actual

def test_large_gap_2():
    start = timezone.localize(datetime(2020, 2, 1, 1, 0))
    trigger = IntervalCronTrigger(weeks=1, day_of_week='mon', hour=2, start_date=start, timezone=timezone)

    expected = timezone.localize(datetime(2020, 2, 3, 2, 0))
    actual = trigger.get_next_fire_time(None, start)
    assert expected == actual

    expected = timezone.localize(datetime(2020, 2, 10, 2, 0))
    actual = trigger.get_next_fire_time(timezone.localize(datetime(2020, 2, 3, 2, 3)), timezone.localize(datetime(2020, 2, 5, 7, 9)))
    assert expected == actual

    expected = timezone.localize(datetime(2020, 2, 17, 2, 0))
    actual = trigger.get_next_fire_time(timezone.localize(datetime(2020, 2, 3, 2, 3)), timezone.localize(datetime(2020, 2, 10, 7, 9)))
    assert expected == actual

def test_now():
    start = timezone.localize(datetime.now())
    trigger = IntervalCronTrigger(days=1, start_date=start, timezone=timezone)

    expected = timezone.localize(datetime.combine(datetime.now().date(), time())) + timedelta(days=1)
    actual = trigger.get_next_fire_time(None, start)
    assert expected == actual

    expected = timezone.localize(datetime.combine(start.date(), time())) + timedelta(days=2)
    actual = trigger.get_next_fire_time(actual, actual + timedelta(minutes=5))
    assert expected == actual
