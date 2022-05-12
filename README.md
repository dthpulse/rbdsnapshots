{toc}

h1. Snapmanager

h2. Describtion

Managing snapshots of OpenStack VMs on Ceph RBD images.  

h2. Requirements

- Access to OpenStack and Ceph
- mysql DB
- python3
- extra python modules
  - rbd
  - Rados
  - novaclient
  - watchdog
  - apscheduler

h2. How it works

Script requires one file */var/lib/snapmanager/snap_sched.yml*. It reads schedule and retention for the OpenStack VMs and creates scheduled jobs based on it stored in the MySQL DB. For the VMs not defined in this file general snapshot retention will be used. 

Snapshot name is the basename of a Snapshot copy set, for example, hourly. 

Schedule spec is made up of count[@day_list] [@hour_list].

*count* is the number of Snapshot copies to retain for this Snapshot copy set. A zero (0) in this field means no new instance of this Snapshot copy will be created.

*@day_list* is a comma-separated list that specifies the days on which a new Snapshot copy for this set is created. Valid entries are mon tue wed thu fri sat sun. They are not case-sensitive. You can specify a range using a dash (-), for example, mon-fri.

*@hour_list* specifies the hours at which a new Snapshot copy is created for this set. Valid entries are whole numbers from 0 to 23. You must use a comma-separated list, for example, 7, 19, 21, 23. 

Snapmanager is taking list of VMs and their volumes from OpenStack periodically (every 3h by default) and keeps the list in */var/lib/snapmanager/server_list.txt*.

File name with '-' suffix is file currently used by the snapmanager. It is compared periodically with the original file and if there are differencies it copies original the file to one with suffix. In this way original file is always primary one.
If file changes snapmanager automatically recreates it's schedule database to keep it current.

On every start script is checkig and updating it's database. 
It's usign 3 different databases according schedule type:

- *service* for the jobs checking changes of snap_sched.yml and server_list.txt files
- *scheduled_snaps* for jobs based on definitions in the snap_sched.yml file
- *general_snaps* for jobs which scheduling is not defined in snap_sched.yml file

Log is in */var/log/snapmanager.log*