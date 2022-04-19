#!/usr/bin/env python3
import pytz
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

def job_function():
    print("Hello World")

sched = BlockingScheduler(timezone=pytz.timezone('Europe/Prague'))

# Runs from Monday to Friday at 5:30 (am) until
sched.add_job(job_function, 'cron', day_of_week='mon-fri', hour=15, minute=15)
sched.add_job(job_function, 'cron', day_of_week='mon,tue,fri', hour=15, minute=24)
sched.start()
