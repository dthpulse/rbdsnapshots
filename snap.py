#!/usr/bin/env python3

import sys
from novaclient import client
from novaclient.v2 import servers
import time
import schedule
import json

# from prometheus_client import Gauge, generate_latest
# # from novaclient.v2 import volumes
# import openstack
# import pathlib
# import sqlite3
# import os
# import string


OS_CONFIG = "/etc/openstackcli/openstack_credentials_nub"
nova = client.Client(version = 2,
              username = 'foremannub',
              password = 'shei8rooReecieL5',
              project_name = 'prod',
              auth_url = 'http://openstack2.prod.nub:5000/v3',
              user_domain_id = 'b2571699c2044245ac79c60e7c6ff09d',
              project_domain_id = 'b2571699c2044245ac79c60e7c6ff09d') # Right here
print(nova.volumes.get_server_volumes('8ff4d0c1-c704-43f3-90b4-a6a1b22f05ec').to_dict())
sys.exit()
#instance = nova.servers.list()
#print(instance.name)
for instance in nova.servers.list():
    print(instance.name)
    print(instance.id)
    print(nova.volumes.get_server_volumes(instance.id))

sys.exit()

