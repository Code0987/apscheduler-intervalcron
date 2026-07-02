from datetime import datetime, time

from dateutil.relativedelta import relativedelta
from tzlocal import get_localzone

from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.util import astimezone, convert_to_datetime, localize, normalize


class IntervalCronTrigger(BaseTrigger):
    """
    Triggers on specified intervals and then adjusts the date-time based on cron data.
    It is assumed, interval will be used for higher level fields and cron for lower level fields.
    It is required to give start_date, as calculations will always happens from start_date.

    Example: every 3 weeks on monday, every 3 months on 3rd friday

    :param int months: number of months to wait
    :param int weeks: number of weeks to wait
    :param int days: number of days to wait

    :param int|str day: day of the (1-31) or nth weekday (1st mon, 3rd fri,...)
    :param int|str day_of_week: number or name of weekday (0-6 or mon,tue,wed,thu,fri,sat,sun)

    :param int hour: hour (0-23)
    :param int minute: minute (0-59)
    :param int second: second (0-59)

    :param datetime|str start_date: earliest possible date/time to trigger on (inclusive)
    :param datetime|str end_date: latest possible date/time to trigger on (inclusive)

    :param datetime.tzinfo|str timezone: time zone to use for the date/time calculations (defaults
        to scheduler timezone)

    :param int|None jitter: advance or delay the job execution by ``jitter`` seconds at most.
    """

    __slots__ = 'interval', 'day', 'day_of_week', 'time', 'start_date', 'end_date', 'timezone', 'jitter'

    # Safety cap when walking intervals looking for a cron match
    _MAX_CRON_INTERVAL_STEPS = 10000

    def __init__(self,
                 months=0, weeks=0, days=0,
                 day=None, day_of_week=None,
                 hour=0, minute=0, second=0,
                 start_date=None, end_date=None, timezone=None, jitter=None
                 ):
        if start_date is None:
            raise ValueError('start_date is required')

        if months < 0 or weeks < 0 or days < 0:
            raise ValueError('months, weeks, and days must be >= 0')

        # Zero interval: imply a step from cron fields, or fail (avoids infinite loop)
        if months == 0 and weeks == 0 and days == 0:
            if day is not None:
                months = 1
            elif day_of_week is not None:
                weeks = 1
            else:
                raise ValueError(
                    'At least one of months, weeks, or days must be > 0 '
                    '(or set day / day_of_week to imply a monthly/weekly interval)'
                )

        # Resolve timezone (strings, pytz, zoneinfo, datetime.timezone)
        if timezone is not None:
            self.timezone = astimezone(timezone)
        elif isinstance(start_date, datetime) and start_date.tzinfo:
            self.timezone = astimezone(start_date.tzinfo)
        elif isinstance(end_date, datetime) and end_date.tzinfo:
            self.timezone = astimezone(end_date.tzinfo)
        else:
            self.timezone = astimezone(get_localzone())

        self.start_date = convert_to_datetime(start_date, self.timezone, 'start_date')
        self.end_date = convert_to_datetime(end_date, self.timezone, 'end_date')

        self.interval = relativedelta(months=months, weeks=weeks, days=days)

        self.day = day
        self.day_of_week = day_of_week

        self.time = time(hour=hour, minute=minute, second=second)

        self.jitter = jitter

    def _at_wall_time(self, when):
        """Build an aware datetime for ``when``'s calendar date at ``self.time`` in our timezone.

        Re-localizing each time avoids DST drift from adding intervals to aware datetimes.
        """
        if isinstance(when, datetime):
            d = when.date()
        else:
            d = when
        naive = datetime.combine(d, self.time)
        return localize(naive, self.timezone)

    def _add_interval(self, dt):
        """Advance by ``self.interval`` in wall-clock calendar space, then re-localize."""
        naive = datetime.combine(dt.date(), self.time) + self.interval
        return localize(naive, self.timezone)

    def get_interval_next_fire_time(self, previous_fire_time, now, can_cron):
        next_fire_time = self._at_wall_time(self.start_date)

        while self._add_interval(next_fire_time) <= now:
            next_fire_time = self._add_interval(next_fire_time)

        # Shift to next interval if cannot cron, i.e. interval mode only
        if not can_cron:
            next_fire_time = self._add_interval(next_fire_time)

        return next_fire_time

    def can_cron(self):
        return (self.day is not None) or (self.day_of_week is not None)

    def get_cron_next_fire_time(self, end, now):
        # Limit cron search window so it does not repeat within the interval
        if self.day is not None:
            end = self._add_interval_delta(end, relativedelta(months=1))
        elif self.day_of_week is not None:
            end = self._add_interval_delta(end, relativedelta(weeks=1))
        else:
            return None

        cron_trigger = CronTrigger(
            day=self.day, day_of_week=self.day_of_week,
            hour=self.time.hour, minute=self.time.minute, second=self.time.second,
            start_date=now, end_date=end, timezone=self.timezone)

        return cron_trigger.get_next_fire_time(now, now)

    def _add_interval_delta(self, dt, delta):
        """Apply an arbitrary relativedelta in wall-clock space, then re-localize."""
        naive = datetime.combine(dt.date(), self.time) + delta
        return localize(naive, self.timezone)

    def get_next_fire_time(self, previous_fire_time, now):
        can_cron = self.can_cron()

        next_fire_time = self.get_interval_next_fire_time(previous_fire_time, now, can_cron)

        # Cron: advance intervals until a matching fire time is found.
        # Never fall back to a bare interval boundary (that may not match day / day_of_week).
        if can_cron:
            for _ in range(self._MAX_CRON_INTERVAL_STEPS):
                if self.end_date is not None and next_fire_time > self.end_date:
                    return None

                cron_now = max(next_fire_time, now)
                cron_fire_time = self.get_cron_next_fire_time(next_fire_time, cron_now)
                if cron_fire_time is not None:
                    next_fire_time = cron_fire_time
                    break

                next_fire_time = self._add_interval(next_fire_time)
            else:
                return None

        next_fire_time = self._apply_jitter(next_fire_time, self.jitter, now)

        if not self.end_date or next_fire_time <= self.end_date:
            return normalize(next_fire_time)

    def __str__(self):
        return (
            'intervalcron[interval={}, day={}, day_of_week={}, time={}, '
            'start_date={}, end_date={}, timezone={}, jitter={}]'
        ).format(
            self.interval, self.day, self.day_of_week, self.time,
            self.start_date, self.end_date, self.timezone, self.jitter,
        )
