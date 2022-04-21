#!/usr/bin/env python3


import yaml

with open('snap.yaml') as f:
    scheduled_servers = []
    snap_sched = yaml.safe_load(f)
    print(snap_sched)
    # for schedule, servers in snap_sched.items():
        
# creating a new dictionary
# my_dict ={"java":100, "python":112, "c":11}
# my_dict2 ={'c':11}

# for i,v in my_dict2.items():
    # del my_dict[i]
# print(my_dict)

 
# # list out keys and values separately
# key_list = list(my_dict.keys())
# val_list = list(my_dict.values())
 
# # print key with val 100
# position = val_list.index(100)
# print(key_list[position])
 
# # print key with val 112
# position = val_list.index(112)
# print(key_list[position])
