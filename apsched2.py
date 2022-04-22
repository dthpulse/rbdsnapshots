#!/usr/bin/env python3

import pytz

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ProcessPoolExecutor
import time

def job_function():
    names = ('anna','roman','janicka','roza')
    for i in names:
        print("Hello ", i )

    with open('/tmp/readme.txt', 'w') as f:
        f.write('Create a new text file!')

MYSQL = {
"url": "mysql+pymysql://localhost:3306/schedule"
}

jobstores = {
    'mysql': SQLAlchemyJobStore(**MYSQL)
}
executors = {
    'default': {'type': 'threadpool', 'max_workers': 20},
    'processpool': ProcessPoolExecutor(max_workers=5)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}
scheduler = BackgroundScheduler(timezone='Europe/Prague')
#scheduler.add_jobstore('sqlalchemy', url='sqlite:////sched.db')
# scheduler.add_job(function, args=(1, ), trigger='interval', seconds=3, jobstore='sqlalchemy')

# .. do something else here, maybe add jobs etc.
scheduler.add_job(job_function, 'cron', day_of_week='mon,tue,fri', hour=22, minute='*', jobstore='mysql', replace_existing=True, id='test5')

scheduler.configure(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=utc)

scheduler.print_jobs()
scheduler.start()

while True:
   time.sleep(1)
