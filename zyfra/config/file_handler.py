#! /usr/bin/env python
# -*- coding: UTF-8 -*-

import ssh_session

class FileLocal(object):
    def __init__(self, filename):
        self.filename = filename
    
    def read(self):
        with open(self.filename) as f:
            content = f.readlines()
        return content

class FileSsh(object):
    def __init__(self, target, filename, password):
        self.target = target
        self.filename = filename
        self.password = password
    
    def read(self):
        ssh = ssh_session.get_ssh_link(self.target, self.password)
        sftp = ssh.open_sftp()
        f = sftp.open(self.filename)
        content = f.readlines()
        f.close()
        return content

class File(object):
    def __new__(cls, uri, password=''):
        target, filename = ([''] + uri.split(':', 1))[-2:]
        if len(target.strip()):
            return FileSsh(target, filename, password)
        else:
            return FileLocal(filename)
        