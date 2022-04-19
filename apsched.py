#!/usr/bin/env python3
import pytz
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler

def job_function():
    names = ('anna','roman','janicka','roza')
    for i in names:
        print("Hello ", i )
    with open('/home/dp/Downloads/readme.txt', 'w') as f:
        f.write('Create a new text file!')

# sched = BlockingScheduler(timezone=pytz.timezone('Europe/Prague'))
sched = BackgroundScheduler(timezone=pytz.timezone('Europe/Prague'))

# Runs from Monday to Friday at 5:30 (am) until
sched.add_job(job_function, 'cron', day_of_week='mon-fri', hour=15, minute=15)
sched.add_job(job_function, 'cron', day_of_week='mon,tue,fri', hour=19, minute=11)
# sched.remove_all_jobs()
sched.start()
sched.print_jobs()
