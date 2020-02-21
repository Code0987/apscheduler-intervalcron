.. image:: https://img.shields.io/badge/license-%20MPL--v2.0-blue.svg
   :target: ../master/LICENSE
.. image:: https://github.com/Code0987/apscheduler-trigger-intervalcron/workflows/ci/badge.svg
   :target: ../../actions

IntervalCron
===========

Triggers on specified intervals and then adjusts the date-time based on cron data.
It is assumed, interval will be used for higher level fields and cron for lower level fields.
It is required to give start_date, as calculations will always happens from start_date.

Example: every 3 weeks on monday, every 3 months on 3rd friday
