#!/usr/bin/env python3

from novaclient import client as novaclient
# import json
import sys
import yaml
import rbd
import rados


## connect to OS
def connect_to_os():
    conn = novaclient.Client(version = 2,
        username = 'foremannub',
        password = 'shei8rooReecieL5',
        project_name = 'prod',
        auth_url = 'http://openstack2.prod.nub:5000/v3',
        user_domain_id = 'b2571699c2044245ac79c60e7c6ff09d',
        project_domain_id = 'b2571699c2044245ac79c60e7c6ff09d')
    return conn

## read yaml - snapshot schedule settings
def snap_sched():
    with open('snap.yaml') as f:
        scheduled_servers = []
        snap_sched = yaml.safe_load(f)
        for schedule, servers in snap_sched.items():
            for i in snap_sched[schedule]:
                scheduled_servers.append(i)
    # print(scheduled_servers)
    return snap_sched, scheduled_servers

## get server list with IDs and volumes IDs
def server_list(conn):
    server_details = dict()
    server = conn.servers.list()
    for server in conn.servers.list():
        volumes = []
        volumes_raw = server._info['os-extended-volumes:volumes_attached']
        for i in range(0, len(volumes_raw)):
            volumes.append(volumes_raw[i]['id'])
        # server_details[server.name] = server.id, volumes
        server_details[server.name] = volumes
    return server_details

def blabla(snap_sched, scheduled_servers, server_details):
    # print(scheduled_servers)
    for server_name,server_volumes in server_details.items():
        # print(server_name)
        if server_name in scheduled_servers:
            print(server_name)

## create rbd snapshot on image
def ceph_rbd():
    cluster = rados.Rados(conffile='/etc/ceph/ceph.conf')
    cluster.connect()
    ioctx = cluster.open_ioctx('rbd')
    image = rbd.Image(ioctx, 'image1')
    image.create_snap('snapshottest')
    image.close()
    ioctx.close()
    cluster.shutdown()


def main():
    conn = connect_to_os()
    s = snap_sched()[0]
    srv = snap_sched()[1]
    server_details = server_list(conn)
    blabla(s, srv, server_details)
    #ceph_rbd()

if __name__ == "__main__":
    main()