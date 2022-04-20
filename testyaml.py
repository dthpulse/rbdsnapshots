#!/usr/bin/env python3


import yaml

with open('snap.yaml') as f:
    scheduled_servers = []
    snap_sched = yaml.safe_load(f)
    for schedule, servers in snap_sched.items():
        for i in snap_sched[schedule]:
            scheduled_servers.append(i)
    print(scheduled_servers)
    print(snap_sched)