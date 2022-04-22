#!/usr/bin/env python3

schedule = '7@mon@2,3'
scheduled_hours = schedule.split('@', 2)[2]
scheduled_days  = schedule.split('@', 2)[1]
keep_copies     = schedule.split('@', 2)[0]

if (',' in scheduled_hours or '-' in scheduled_hours) and ('-' in scheduled_days or ',' in scheduled_days):
    snap_name = 'hourly'
elif '-' not in scheduled_days and ',' not in scheduled_days:
    snap_name = 'weekly'
elif ',' not in scheduled_hours and '-' not in scheduled_hours:
    snap_name = 'daily'

print(schedule, '=', snap_name)
