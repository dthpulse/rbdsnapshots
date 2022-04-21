#!/usr/bin/env python3

from novaclient import client as novaclient

os_conn = novaclient.Client(version = 2,
    username = 'foremannub',
    password = 'shei8rooReecieL5',
    project_name = 'prod',
    auth_url = 'http://openstack2.prod.nub:5000/v3',
    user_domain_id = 'b2571699c2044245ac79c60e7c6ff09d',
    project_domain_id = 'b2571699c2044245ac79c60e7c6ff09d')

server_details = dict()
servers_list = os_conn.servers.list()
snapmanager_dir = '/var/lib/snapmanager'
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


