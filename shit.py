#!/usr/bin/env python3

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
os.mkdir(snapmanager_dir)

'''
apscheduler settings
'''
def scheduler_conf():
    MYSQL_SNAP = {
        "url": "mysql+pymysql://localhost:3306/snapshot_schedule"
    }
    MYSQL_SERVICE = {
        "url": "mysql+pymysql://localhost:3306/service_schedule"
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
    try:
        scheduler.start()
    except:
        print("scheduler is already running")

'''
connect to OS
'''
def connect_to_os():
    os_conn = novaclient.Client(version = 2,
        username = 'foremannub',
        password = 'shei8rooReecieL5',
        project_name = 'prod',
        auth_url = 'http://openstack2.prod.nub:5000/v3',
        user_domain_id = 'b2571699c2044245ac79c60e7c6ff09d',
        project_domain_id = 'b2571699c2044245ac79c60e7c6ff09d')
    return os_conn

'''
connect to Ceph
'''
def ceph_conn():
    cluster = rados.Rados(conffile='/etc/ceph/ceph.conf')
    cluster.connect()
    ioctx = cluster.open_ioctx('rbd')

'''
using librbd we're connecting to the Ceph and creating snapshots
'''
def create_general_snap(general_scheduled_servers):
    ceph_conn()
    keep_copies = '5'
    snap_name = 'general'
    for server, volumes in general_scheduled_servers.items():
        for volume in volumes:
            now = datetime.now()
            date_string = now.strftime('%d%m%Y%H%M')
            image = rbd.Image(ioctx, 'volume-' + volume)
            image.create_snap(snap_name + '_' + date_string)
            image_snap_list = list(image.list_snaps())
            snaps_delete = []
            for i in image_snap_list:
                if snap_name in i:
                    snaps_delete.append(i)
            snaps_filtered = len(snaps_delete) - keep_copies
            if snaps_filtered > 0:
                del snaps_delete[:-snaps_filtered]
            for snap in snaps_delete:
                image.remove_snap[image_snap_list[0][snap]]
            image.close()
    ioctx.close()
    cluster.shutdown()

'''
using librbd we're connecting to the Ceph and creating snapshots
'''
def create_scheduled_snap(snap_sched, server_details):
    ceph_conn()
    for schedule, server in snap_sched.items():
        scheduled_hours = schedule.split('@', 2)[2]
        scheduled_days  = schedule.split('@', 2)[1]
        keep_copies     = schedule.split('@', 2)[0]
        if (',' in scheduled_hours or '-' in scheduled_hours) and ('-' in scheduled_days or ',' in scheduled_days):
            snap_name = 'hourly'
        elif '-' not in scheduled_days and ',' not in scheduled_days:
            snap_name = 'weekly'
        elif ',' not in scheduled_hours and '-' not in scheduled_hours:
            snap_name = 'daily'
        for volume in server_details[server]:
            now = datetime.now()
            date_string = now.strftime('%d%m%Y%H%M')
            image = rbd.Image(ioctx, 'volume-' + volume)
            image.create_snap(snap_name + '_' + date_string)
            image_snap_list = list(image.list_snaps())
            snaps_delete = []
            for i in image_snap_list:
                if snap_name in i:
                    snaps_delete.append(i)
            snaps_filtered = len(snaps_delete) - keep_copies
            if snaps_filtered > 0:
                del snaps_delete[:-snaps_filtered]
            for snap in snaps_delete:
                image.remove_snap[image_snap_list[0][snap]]
            image.close()
    ioctx.close()
    cluster.shutdown()

'''
read yaml - snapshot schedule settings
snap_sched.yml is file defined by admins
here we also checking if there is any update by backing up the old one 
and comparing it with new one. This function is scheduled with apscheduler to run regularly
we get snap_sched dict like {'7@mon-fri@2,4':'['server1', 'server2',...]'}
and the list of scheduled_servers
'''
def snap_sched():
    orig_yaml = snapmanager_dir + '/snap_sched.yml'
    used_yaml = orig_yaml + '-'
    try:
        file_check = used_yaml.resolve(strict=True)
    except:
        shutil.copyfile(orig_yaml, used_yaml)
    finally:
        compare_result = filecmp.cmp(orig_yaml, used_yaml, shallow=False)
    
    if not compare_result:
        shutil.copyfile(orig_yaml, used_yaml)
        scheduler_conf()
        scheduler.remove_all_jobs(jobstore='mysql_snap')
        scheduler.shutdown()

    with open(used_yaml) as f:
        scheduled_servers = []
        snap_sched = yaml.safe_load(f)
        for schedule, servers in snap_sched.items():
            for i in snap_sched[schedule]:
                scheduled_servers.append(i)

    return snap_sched, scheduled_servers

'''
get server list with IDs and volumes IDs from OpenStack
here we also checking if there is any update on OS by backing up the server list 
and comparing it with new one. This function is scheduled with apscheduler to run regularly
we get dict with {'server_name':'[volume1, volume2, ...]'}
'''
def openstack_server_list(os_conn):
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
    
    try:
        file_check = used_server_list.resolve(strict=True)
    except:
        shutil.copyfile(new_server_list, used_server_list)
    finally:
        compare_result = filecmp.cmp(new_server_list, used_server_list, shallow=False)
    
    if not compare_result:
        shutil.copyfile(new_server_list, used_server_list)
        scheduler_conf()
        scheduler.remove_all_jobs(jobstore='mysql_snap')
        scheduler.shutdown()
    
    return server_details

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
mel by volat funkci create_general_snap - ale potrebuji ji jeste upravit,
aby nevyzadovala zadny argument
'''
def create_general_snap_job(general_scheduled_servers):
    hour = '6,12,18'
    day_of_week = 'mon-fri'
    scheduler_conf()
    for server, volumes in general_scheduled_servers.items():
        for volume in volumes:
            scheduler.add_job(
                job_function, 
                'cron', 
                day_of_week=day_of_week, 
                hour=hour, 
                minute='15', 
                jobstore='mysql_snap', 
                replace_existing=True, 
                id=volume + '_general',
                misfire_grace_time=600)
    scheduler.shutdown()

def create_service_schedule_job():
    scheduler_conf()
    scheduler.add_job(
        snap_sched, 
        'cron', 
        day_of_week='mon-sun', 
        hour='9,11,13,15,17,19', 
        minute='25', 
        jobstore='mysql_service', 
        replace_existing=True, 
        id='snap_sched',
        misfire_grace_time=600)
    scheduler.add_job(
        server_list, 
        'cron', 
        day_of_week='mon-sun', 
        hour='9,11,13,15,17,19', 
        minute='45', 
        jobstore='mysql_service', 
        replace_existing=True, 
        id='server_list',
        misfire_grace_time=600)
    scheduler.shutdown()

def main():
    os_conn = connect_to_os()
    s = snap_sched()[0]
    srv = snap_sched()[1]
    server_details = server_list(os_conn)
    blabla(s, srv, server_details)
    #ceph_rbd()

if __name__ == "__main__":
    main()