#!/usr/bin/env python3

from novaclient import client as novaclient
import json
import sys
import yaml

## connect to OS
nova = novaclient.Client(version = 2,
              username = 'foremannub',
              password = 'shei8rooReecieL5',
              project_name = 'prod',
              auth_url = 'http://openstack2.prod.nub:5000/v3',
              user_domain_id = 'b2571699c2044245ac79c60e7c6ff09d',
              project_domain_id = 'b2571699c2044245ac79c60e7c6ff09d')

## read yaml - snapshot schedule settings
with open('snap.yaml') as f:
    print(yaml.safe_load(f))

sys.exit()

## get server list with IDs and volumes IDs
server_details = dict()
server = nova.servers.list()
for server in nova.servers.list():
    volumes = []
    volumes_raw = server._info['os-extended-volumes:volumes_attached']
    for i in range(0, len(volumes_raw)):
        volumes.append(volumes_raw[i]['id'])
    server_details[server.name] = server.id, volumes
    print(server_details)


## create rbd snapshot on image
#!/usr/bin/env python3

import rbd
import rados

cluster = rados.Rados(conffile='/etc/ceph/ceph.conf')
cluster.connect()
ioctx = cluster.open_ioctx('rbd')
image = rbd.Image(ioctx, 'image1')
image.create_snap('snapshottest')
image.close()
ioctx.close()
cluster.shutdown()
