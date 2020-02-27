from datetime import timedelta, datetime, date, time
from dateutil.relativedelta import relativedelta
from math import ceil

from tzlocal import get_localzone

from apscheduler.triggers.base import BaseTrigger
from apscheduler.util import convert_to_datetime, timedelta_seconds, datetime_repr, astimezone
from apscheduler.triggers.cron import CronTrigger

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

    :param int|str hour: hour (0-23)
    :param int|str minute: minute (0-59)
    :param int|str second: second (0-59)

    :param datetime|str start_date: earliest possible date/time to trigger on (inclusive)
    :param datetime|str end_date: latest possible date/time to trigger on (inclusive)

    :param datetime.tzinfo|str timezone: time zone to use for the date/time calculations (defaults
        to scheduler timezone)

    :param int|None jitter: advance or delay the job execution by ``jitter`` seconds at most.
    """

    __slots__ = 'interval', 'day', 'day_of_week', 'time', 'start_date', 'end_date', 'timezone', 'jitter'

    def __init__(self,
                 months=0, weeks=0, days=0,
                 day=None, day_of_week=None,
                 hour=0, minute=0, second=0,
                 start_date=None, end_date=None, timezone=None, jitter=None
                ):
        # Pre-requisites
        assert not (start_date is None)

        # Extract timezone info
        if timezone:
            self.timezone = timezone
        elif isinstance(start_date, datetime) and start_date.tzinfo:
            self.timezone = start_date.tzinfo
        elif isinstance(end_date, datetime) and end_date.tzinfo:
            self.timezone = end_date.tzinfo
        else:
            self.timezone = get_localzone()

        self.start_date = convert_to_datetime(start_date, self.timezone, 'start_date')
        self.end_date = convert_to_datetime(end_date, self.timezone, 'end_date')

        # Compute interval
        self.interval = relativedelta(months=months, weeks=weeks, days=days)

        # Cron trigger
        self.day = day
        self.day_of_week = day_of_week
        
        self.time = time(hour=hour, minute=minute, second=second)

        # Jitter will be applied on final output
        self.jitter = jitter

    def get_interval_next_fire_time(self, previous_fire_time, now, can_cron):
        next_fire_time = self.timezone.localize(
            datetime.combine(self.start_date.date(), 
            self.time))

        while (next_fire_time + self.interval) <= now:
            next_fire_time += self.interval

        # Shift to next interval
        # if cannot cron, i.e. interval mode only
        if not can_cron:
            next_fire_time += self.interval

        return next_fire_time

    def can_cron(self):
        return (not self.day is None) or (not self.day_of_week is None)

    def get_cron_next_fire_time(self, end, now):
        # Calculate end_date for cron
        # to prevent it from repeating within interval
        if not (self.day is None):
            end += relativedelta(months=1)
        elif not (self.day_of_week is None):
            end += relativedelta(weeks=1)
        else:
            return None

        cron_trigger = CronTrigger(
            day=self.day, day_of_week=self.day_of_week, 
            hour=self.time.hour, minute=self.time.minute, second=self.time.second,
            start_date=now, end_date=end, timezone=self.timezone)

        cron_fire_time = cron_trigger.get_next_fire_time(now, now)

        return cron_fire_time

    def get_next_fire_time(self, previous_fire_time, now):
        can_cron = self.can_cron()

        # Get interval next fire time
        next_fire_time = self.get_interval_next_fire_time(previous_fire_time, now, can_cron)

        # Cron
        if can_cron:
            cron_now = max(next_fire_time, now)

            # Get cron next fire time
            cron_fire_time = self.get_cron_next_fire_time(next_fire_time, cron_now)

            # Add interval if cron fire time is null
            # this is for when cron hits last value within interval
            # so we need to goto next interval
            if cron_fire_time is None:
                next_fire_time += self.interval
                cron_fire_time = self.get_cron_next_fire_time(next_fire_time, next_fire_time)

            # Take final output
            if not (cron_fire_time is None):
                next_fire_time = cron_fire_time

        # Apply jitter
        next_fire_time = self._apply_jitter(next_fire_time, self.jitter, now)

        # Check end date
        if not self.end_date or next_fire_time <= self.end_date:
            return self.timezone.normalize(next_fire_time)

    def __str__(self):
        return 'intervalcron[interval={}, day={}, day_of_week={}, time={}, start_date={}, end_date={}, timezone={}, jitter={}]'.format(self.interval, self.day, self.day_of_week, self.time, self.start_date, self.end_date, self.timezone, self.jitter)
