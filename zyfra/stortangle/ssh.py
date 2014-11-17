#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time

from paramiko.client import SSHClient, AutoAddPolicy, socket

hosts_filename = os.path.expanduser("~/.ssh/paramiko_known_hosts")
#print hosts_filename

client = SSHClient()
if os.path.isfile(hosts_filename):
    client.load_host_keys(hosts_filename) #'~/.ssh/known_hosts'
client.set_missing_host_key_policy(AutoAddPolicy())
print client.get_host_keys()
client.connect('localhost', 2200, username='robey', password='foo')
client.save_host_keys(hosts_filename)
#print client.get_host_keys()
channel = client.invoke_shell()
channel.settimeout(0)
#time.sleep(1)
def datas(data=''):
    while True:
        try:
            res = channel.recv(10000)
            if len(res) == 0:
                exit(0)
            data += res
            cmds = data.split('\n')
            for r in cmds[:-1]:
                yield r
            data = cmds[-1]
        except socket.timeout:
            pass

for r in datas():
    print repr(r)
    if r == 'Username: ':
        print '!! user !!!'
        channel.send('Ydfdf   dfop\n')
    
#if channel.recv_ready():
#print '[' + read() + ']'
#channel.send('Ydfdf   dfop\n')
#print '[' + read() + ']'
#stdin, stdout, stderr = channel.exec_command('coucou')
#print stdout.read(1000)
