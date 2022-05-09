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
from datetime import datetime
from novaclient import client as novaclient
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ProcessPoolExecutor

snapmanager_dir = '/var/lib/snapmanager'

try:
    os.mkdir(snapmanager_dir)
except:
    print('snapmanager dir %s exists' % snapmanager_dir)

'''
apscheduler settings
'''

MYSQL_SNAP = {
    "url": "mysql+pymysql://localhost:3306/denis"
}
MYSQL_SERVICE = {
    "url": "mysql+pymysql://localhost:3306/janicka"
}
jobstores = {
    'mysql_snap': SQLAlchemyJobStore(**MYSQL_SNAP),
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
        for job in scheduler.get_jobs():
            job.remove()

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
    general_scheduled_servers = {}
    for server_name,server_volumes in server_details.items():
        if server_name not in scheduled_servers:
            general_scheduled_servers[server_name] = server_volumes
    return general_scheduled_servers

'''
using librbd we're connecting to the Ceph and creating snapshots
'''
def create_scheduled_snap(snap_sched, server_details):
    week = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    day_of_week_to_snap = []
    hours_to_snap = []
    today = datetime.today().strftime('%a')
    hour = datetime.now().strftime('%-H')

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
                        day_of_week=scheduled_days,
                        hour=scheduled_hours,
                        jobstore='mysql_snap',
                        replace_existing=True,
                        id='%s-%s' % (server, volume),
                        misfire_grace_time=600,
                        args=[volume, keep_copies, snap_name])

def create_general_snap(general_scheduled_servers):
    keep_copies = '5'
    snap_name = 'general'
    day_of_week_to_snap = 'mon,tue,wed,thu,fri'
    hours_to_snap = '6,11,15,19'
    today = datetime.today().strftime('%a')
    hour = datetime.now().strftime('%H')
    for server, volumes in general_scheduled_servers.items():
        for volume in volumes:
            scheduler.add_job(
            create_rbd_snapshot,
            'cron',
            day_of_week='mon-fri',
            hour=hours_to_snap,
            minute='15',
            jobstore='mysql_snap',
            replace_existing=True,
            id='%s-%s' % (server, volume),
            misfire_grace_time=600,
            args=[volume, keep_copies, snap_name]) 
            
def create_rbd_snapshot(volume, keep_copies, snap_name):           
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
    openstack_server_list()
    get_snap_sched()
    server_details = openstack_server_list()
    snap_sched = get_snap_sched()[0]
    scheduled_servers = get_snap_sched()[1]
    general_scheduled_servers = not_defined_servers(scheduled_servers, server_details)
    create_service_schedule_job()
    create_scheduled_snap(snap_sched, server_details)
    create_general_snap(general_scheduled_servers)

    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
