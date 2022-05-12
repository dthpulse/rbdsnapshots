#!/usr/bin/env python3

'''
use mysql;
UPDATE user SET plugin='mysql_native_password' WHERE User='root';
FLUSH PRIVILEGES;
exit;
'''

import sys
import os
import yaml
import rbd
import rados
import pytz
import time
import shutil
import filecmp
import logging
from datetime import datetime
from novaclient import client as novaclient
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ProcessPoolExecutor
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


snapmanager_dir = '/var/lib/snapmanager'

try:
    os.mkdir(snapmanager_dir)
except:
    pass

'''
apscheduler settings
'''

MYSQL_SCHEDULED_SNAPS = {
    "url": "mysql+pymysql://localhost:3306/scheduled_snaps"
}
MYSQL_GENERAL_SNAPS = {
    "url": "mysql+pymysql://localhost:3306/general_snaps"
}
MYSQL_SERVICE = {
    "url": "mysql+pymysql://localhost:3306/service"
}
jobstores = {
    'mysql_scheduled_snaps': SQLAlchemyJobStore(**MYSQL_SCHEDULED_SNAPS),
    'mysql_general_snaps': SQLAlchemyJobStore(**MYSQL_GENERAL_SNAPS),
    'mysql_service': SQLAlchemyJobStore(**MYSQL_SERVICE)
}
executors = {
    'default': {'type': 'threadpool', 'max_workers': 20},
    'processpool': ProcessPoolExecutor(max_workers=50)
}
job_defaults = {
    'coalesce': True,
    'max_instances': 600
}
scheduler = BackgroundScheduler(timezone='Europe/Prague')
scheduler.configure(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone='Europe/Prague')
scheduler.start()

'''
watchdog takes care of watching the changes on snap_sched.yml and servers_list.txt
if changed, DB is recreated 
'''
def wd():
    patterns = ["*.yml-", "*.txt-"]
    ignore_patterns = None
    ignore_directories = False
    case_sensitive = True
    event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    return event_handler

def on_modified(event):
    if not filecmp.cmp('%s/server_list.txt' % snapmanager_dir, '%s/server_list.txt-' % snapmanager_dir, shallow=False):
        for job in scheduler.get_jobs('mysql_general_snaps'):
            job.remove()
        for job in scheduler.get_jobs('mysql_scheduled_snaps'):
            job.remove()
        create_scheduled_snap(snap_sched, server_details)
        create_general_snap(general_scheduled_servers)
    if not filecmp.cmp('%s/snap_sched.yml' % snapmanager_dir, '%s/snap_sched.yml-' % snapmanager_dir, shallow=False):
        for job in scheduler.get_jobs('mysql_scheduled_snaps'):
            job.remove()
        create_scheduled_snap(snap_sched, server_details)

def wtd(event_handler):
    event_handler.on_modified = on_modified
    go_recursively = True
    observer = Observer()
    observer.schedule(event_handler, snapmanager_dir, recursive=go_recursively)
    observer.start()
    return observer

'''
connect to OS
'''
os_conn = novaclient.Client(version = 2,
    username = 'foremannub',
    password = 'shei8rooReecieL5',
    project_name = 'prod',
    auth_url = 'http://openstack2.prod.nub:5000/v3',
    user_domain_id = 'b2571699c2044245ac79c60e7c6ff09d',
    project_domain_id = 'b2571699c2044245ac79c60e7c6ff09d')

'''
connect to Ceph
'''
cluster = rados.Rados(conffile='/etc/ceph/ceph.conf')
cluster.connect()
ioctx = cluster.open_ioctx('op2_volumes_ssd')

'''
get server list with IDs and volumes IDs from OpenStack
here we also checking if there is any update on OS by backing up the server list
and comparing it with new one. This function is scheduled with apscheduler to run regularly
we get dict with {'server_name':'[volume1, volume2, ...]'}
'''
def openstack_server_list():
    global server_details
    server_details = dict()
    servers_list = os_conn.servers.list()
    new_server_list = snapmanager_dir + '/server_list.txt'
    used_server_list = new_server_list + '-'
    for server in servers_list:
        volumes = []
        volumes_raw = server._info['os-extended-volumes:volumes_attached']
        for i in range(0, len(volumes_raw)):
            volumes.append(volumes_raw[i]['id'])
        server_details[server.name] = volumes
    with open(new_server_list, 'w') as f:
        for i in sorted(server_details):
            line=i, server_details[i]
            f.write(str(line)+'\n')
        f.close()
    if not os.path.exists(used_server_list) or not filecmp.cmp(new_server_list, used_server_list, shallow=False):
        shutil.copyfile(new_server_list, used_server_list)
    return server_details

'''
read yaml - snapshot schedule settings
snap_sched.yml is file defined by admins
here we also checking if there is any update by backing up the old one
and comparing it with new one. This function is scheduled with apscheduler to run regularly
we get snap_sched dict like {'7@mon-fri@2,4':'['server1', 'server2',...]'}
and the list of scheduled_servers
'''
def get_snap_sched():
    global snap_sched
    orig_yaml = snapmanager_dir + '/snap_sched.yml'
    used_yaml = orig_yaml + '-'
    if not os.path.exists(used_yaml) or not filecmp.cmp(orig_yaml, used_yaml, shallow=False):
        shutil.copyfile(orig_yaml, used_yaml)
    with open(used_yaml) as f:
        scheduled_servers = []
        snap_sched = yaml.safe_load(f)
        for schedule, servers in snap_sched.items():
            for i in snap_sched[schedule]:
                scheduled_servers.append(i)
    return snap_sched, scheduled_servers

'''
VMs not scheduled in yaml file will be backed up with general schedule
'''
def not_defined_servers(scheduled_servers, server_details):
    global general_scheduled_servers
    general_scheduled_servers = {}
    for server_name,server_volumes in server_details.items():
        if server_name not in scheduled_servers:
            general_scheduled_servers[server_name] = server_volumes
    return general_scheduled_servers

'''
creates scheduled snaps, servers defined in snap_sched.yml
'''
def create_scheduled_snap(snap_sched, server_details):
    for schedule, servers in snap_sched.items():
        scheduled_hours = schedule.split('@', 2)[2]
        scheduled_days  = schedule.split('@', 2)[1]
        keep_copies     = schedule.split('@', 2)[0]
        if (',' in scheduled_hours or '-' in scheduled_hours) and ('-' in scheduled_days or ',' in scheduled_days):
            snap_name = 'hourly'
        elif '-' not in scheduled_days and ',' not in scheduled_days:
            snap_name = 'weekly'
        elif ',' not in scheduled_hours and '-' not in scheduled_hours:
            snap_name = 'daily'
        for server in servers:
            for volume in server_details[server]:
                    scheduler.add_job(
                        create_rbd_snapshot,
                        'cron',
                        name='%s-%s' % (server, volume),
                        day_of_week=scheduled_days,
                        hour='%s' % scheduled_hours,
                        jobstore='mysql_scheduled_snaps',
                        replace_existing=True,
                        id='%s-%s' % (server, volume),
                        misfire_grace_time=600,
                        args=[volume, keep_copies, snap_name])

'''
creates general snaps, for all servers not defined in snap_sched.yml
'''
def create_general_snap(general_scheduled_servers):
    keep_copies = '5'
    snap_name = 'general'
    hours_to_snap = '6,11,15,19'
    for server, volumes in general_scheduled_servers.items():
        for volume in volumes:
            scheduler.add_job(
            create_rbd_snapshot,
            'cron',
            name='%s-%s' % (server, volume),
            day_of_week='mon-fri',
            hour=hours_to_snap,
            minute='15',
            jobstore='mysql_general_snaps',
            replace_existing=True,
            id='%s-%s' % (server, volume),
            misfire_grace_time=600,
            args=[volume, keep_copies, snap_name]) 

'''
using librbd we're connecting to the Ceph and creating snapshots
'''          
def create_rbd_snapshot(volume, keep_copies, snap_name):           
    if int(keep_copies) != 0:
        now = datetime.now()
        date_string = now.strftime('%d%m%Y%H')
        image = rbd.Image(ioctx, 'volume-' + volume)
        image_snap_list = list(image.list_snaps())
        snaps_delete = []
        if not image_snap_list:
            image.create_snap(snap_name + '_' + date_string)
        for image_snap in image_snap_list:
            if snap_name in image_snap['name']:
                snaps_delete.append(image_snap['name'])
        snaps_filtered = len(snaps_delete) - int(keep_copies) + 1
        if image_snap['name'] and date_string not in image_snap['name']:
            image.create_snap(snap_name + '_' + date_string)
        if snaps_filtered > 0:
            del snaps_delete[snaps_filtered:]
            for snap in snaps_delete:
                image.remove_snap(snap)
        image.close()

def create_service_schedule_job():
    scheduler.add_job(
        get_snap_sched,
        'interval',
        minutes=5,
        seconds=30,
        jobstore='mysql_service',
        replace_existing=True,
        id='snap_sched',
        misfire_grace_time=600)
    scheduler.add_job(
        openstack_server_list,
        'interval',
        hours=3,
        jobstore='mysql_service',
        replace_existing=True,
        id='server_list',
        misfire_grace_time=600)

def main():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        filename='/var/log/snapmanager.log')
    event_handler=wd()
    observer=wtd(event_handler)
    wtd(event_handler)
    openstack_server_list()
    get_snap_sched()
    server_details = openstack_server_list()
    snap_sched = get_snap_sched()[0]
    scheduled_servers = get_snap_sched()[1]
    general_scheduled_servers = not_defined_servers(scheduled_servers, server_details)
    create_service_schedule_job()
    create_scheduled_snap(snap_sched, server_details)
    create_general_snap(general_scheduled_servers)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
        
if __name__ == '__main__':
    main()
