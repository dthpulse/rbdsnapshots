#!/usr/bin/env python3

from novaclient import client as novaclient

def connect_to_os():
    os_conn = novaclient.Client(version = 2,
        username = 'foremannub',
        password = 'shei8rooReecieL5',
        project_name = 'prod',
        auth_url = 'http://openstack2.prod.nub:5000/v3',
        user_domain_id = 'b2571699c2044245ac79c60e7c6ff09d',
        project_domain_id = 'b2571699c2044245ac79c60e7c6ff09d')
    return os_conn

def server_list(os_conn):
    server_details = dict()
    server = os_conn.servers.list()
    for server in os_conn.servers.list():
        volumes = []
        volumes_raw = server._info['os-extended-volumes:volumes_attached']
        for i in range(0, len(volumes_raw)):
            volumes.append(volumes_raw[i]['id'])
        # server_details[server.name] = server.id, volumes
        server_details[server.name] = volumes
    with open('new_server_list.txt', 'w') as f:
        for i in sorted(server_details):
            line = i, server_details[i]
            line = list(line)
            f.write(str(line)+'\n')
        f.close()
    with open('new_server_list.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = list(line)
            print(line[1])

    
    return server_details

## compare server details
def compare_server_details(server_details, os_conn):
    server_details_old = server_details
    server_list(os_conn)
    if server_details_old == server_details:
        print('yep')
    
def main():
    os_conn = connect_to_os()
    server_details = server_list(os_conn)
    compare_server_details(server_details, os_conn)

if __name__ == "__main__":
    main()