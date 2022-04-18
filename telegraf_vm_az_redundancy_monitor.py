#!/usr/bin/env python3

from prometheus_client import Gauge, generate_latest
import openstack
import pathlib
import sqlite3
import os
import string
import sys

OS_CONFIG = "/home/dp/openstack_credentials_nub"


def create_connection():
    os_config = get_config()
    return openstack.connect(
                    auth_url          = os_config['OS_AUTH_URL'],
                    project_name      = os_config['OS_PROJECT_NAME'],
                    username          = os_config['OS_USERNAME'],
                    password          = os_config['OS_PASSWORD'],
                    user_domain_id    = os_config['OS_USER_DOMAIN_ID'],
                    project_domain_id = os_config['OS_PROJECT_DOMAIN_ID']
                    )

def list_all_vms(conn):
    vms    = []
    os_vms = conn.compute.servers(details=True, all_projects=True)
    for os_vm in os_vms:
        vms.append(os_vm)
    print(vms)
    return vms

def get_config():
    conf        = {}
    config_file = pathlib.Path(OS_CONFIG)
    with config_file.open() as cfile:
        lines = [line for line in cfile.readlines() if line.startswith('export')]
        for line in lines:
            newline    = line.rstrip('\n').lstrip('export ')
            key, value = newline.split('=')
            conf[key]  = value
        return conf

def create_db():
    conndb = sqlite3.connect('/tmp/test.db')
    conndb.execute('''CREATE TABLE IF NOT EXISTS vm_az_layout
            (ID integer primary key autoincrement,
            FQDN           TEXT(100)   NOT NULL,
            VOLUME      TEXT(100)   NOT NULL);''')
    return conndb

def fillup_db(vms, conndb):
    for i in range(0, len(vms)):
       vm_details  = vms[i]
       vm_fqdn     = vm_details['name']
       vm_az       = vm_details['location']['zone']
       vm_alias    = vm_fqdn.partition('.')[0]
       vm_domain   = vm_fqdn.partition('.')[2]
       vm_basename = vm_alias.rstrip(string.digits)
       ooo = vm_details['os-extended-volumes:volumes_attached'][0]
       print(ooo)
       sys.exit()
    #    if vm_basename.endswith('-'):
        #    vm_basename = vm_basename[:-1]
    #    conndb.execute("INSERT INTO vm_az_layout (ID, FQDN, AZ, ALIAS, DOMAIN, BASENAME) \
        #  VALUES (NULL, ?, ?, ?, ?, ?);", (str(vm_fqdn), str(vm_az), str(vm_alias), str(vm_domain), str(vm_basename)))
    # conndb.commit()

# def get_nonredundant_vms(conndb):
    # nonredundant_vms = conndb.execute("SELECT az, basename, GROUP_CONCAT(fqdn) FROM vm_az_layout \
        # WHERE domain LIKE '%prod.nub' GROUP BY basename,domain \
        # HAVING COUNT(*)>1 AND COUNT(DISTINCT(az))=1;").fetchall()
    # return nonredundant_vms

# def metrics(nonredundant_vms):
    # gauge_line = Gauge('openstack_check_az_vm_group', 'Reports about VMs from one group deployed on just one AZ',('vms', 'vmgroup', 'availability_zone',))
    # for k in nonredundant_vms:
        # availability_zone = k[0]
        # vmgroup           = k[1]
        # nr_vms            = k[2]
        # if vmgroup not in blacklisted_vmgroups:
            # gauge_line.labels(nr_vms, vmgroup, availability_zone).set(1)
    # print(generate_latest(gauge_line).decode())

def main():
    conn = create_connection()
    vms  = list_all_vms(conn)
    conndb = create_db()
    fillup_db(vms, conndb)
    # nonredundant_vms = get_nonredundant_vms(conndb)
    # metrics(nonredundant_vms)
    # os.remove('/var/tmp/vm_az_check.db')

if __name__ == "__main__":
    main()

