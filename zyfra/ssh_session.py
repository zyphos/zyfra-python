#! /usr/bin/env python
# -*- coding: UTF-8 -*-

import paramiko

pool = {}

class SshLink(paramiko.SSHClient):
    def __init__(self, target, password):
        self.target = target
        pool[target] = self
        paramiko.SSHClient.__init__(self)
        username, host = ([''] + target.split('@'))[-2:]
        self.load_system_host_keys()
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.connect(host, username=username, password=password)
    
    def cmd(self, commmand):
        return self.exec_command(commmand)[1].read()
        

def get_ssh_link(target, password=''):
    """target is something like: user@host"""
    if target in pool:
        return pool[target]
    else:
        return SshLink(target, password)
