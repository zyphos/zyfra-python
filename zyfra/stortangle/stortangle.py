#!/usr/bin/env python

import os
import shutil
import subprocess

import threading
import multiprocessing
import ssh_rpc
import inotify

'cmd,timestamp,'
'addchg,timestamp,filenames'
'del,timestamp,filenames'
def rsync(cmds):
    return subprocess.check_output(['rsync', '-a'] + cmds)

class ChannelHandlerClientStortangle(ssh_rpc.ChannelHandlerClient):
    def __init__(self, host, username, password, port=2200, queue=None, name=None):
        self.name = name
        ssh_rpc.ChannelHandlerClient.__init__(self, host, username, password, port, queue, threaded=True)
    
    def _init(self):
        self.send('name', name)
        
    def send(self, cmd, params):
        super(ChannelHandlerClientStortangle, self).send('%s,%s' % (cmd, params))
    
    def _on_receive_cmd(self, queue, cmd):
        cmd, param = cmd.split(',', 1)
        if cmd == 'who':
            self.send('name', self.name)
        queue.put((cmd, params))

class ChannelHandlerServerStortangle(ssh_rpc.ChannelHandlerServer):
    name = None
    
    def init(self, queue):
        self.queue = queue

    def _on_receive_cmd(self, queue, msg):
        cmd, params = cmd.split(',', 1)
        if cmd == 'name':
            self.name = params
            params = self.id
        if self.name is None:
            self.send('who', '')
            return
        queue((self.name, cmd, params))
    
    def send(self, cmd, params):
        super(ChannelHandlerServerStortangle, self).send('%s,%s' % (cmd, params))

"""def start_ssh_server(port, ):
    allowed_users = {'bucky': 'foo'}
    ssh_rpc.Server(ChannelHandlerServerStortangle, allowed_users=allowed_users)

def start_ssh_client(host, username, password, port, queue, name):
    ChannelHandlerClientStortangle(host, username, password, port, queue, name)"""

class InotifyWatcher(inotify.PathWatcher):
    def _on_events(self, queue, events):
        queue.put(('inotify', events))

class StortangleCommon(object):
    def __init__(self, storage_path='~/stortangle'):
        self.storage_path = storage_path
        self.queue = multiprocessing.Queue()
        #ssh_from_pipe, ssh_to_pipe = multiprocessing.Pipe()
        #inotify_from_pipe, inotify_to_pipe = multiprocessing.Pipe()
        pass
    
    def rm(self, filename):
        full_path = os.path.join(self.storage_path, filename)
        print 'rm file %s' % full_path
        #shutil.rmtree(full_path)
        
    def main_loop(self):
        while(True):
            if not self.queue.empty():
                while not self.queue.empty():
                    self.parse_message(self.queue.get())
                    self.queue.task_done()
    
    def parse_message(self, message):
        pass

class StortangleServer(StortangleCommon):
    def __init__(self, storage_path='~/stortangle', port=2200, allowed_users=None):
        StortangleCommon.__init__(self, storage_path)
        self.ssh = ssh_rpc.Server(ChannelHandlerServerStortangle, port=port, allowed_users=allowed_users, queue=self.queue, threaded=True)
        self.routing_table = {}
    
    def parse_message(self, message):
        src, cmd, param = message
        if cmd == name:
            self.routing_table[src] = self.ssh.get_handler_by_id(param)
            self.send(src, 'srvpath', self.storage_path)
        elif cmd == 'rsync':
            self.send_all_but_target(src, 'rsync', param)
    
    def send(self, target, cmd, param):
        self.routing_table[target].send(cmd, param)
    
    def send_all_but_target(self, the_target, cmd, param):
        for target in self.routing_table:
            if target == the_target:
                continue
            self.send(target, cmd, param)
    
    def send_all(self, cmd, param):
        for target in self.routing_table:
            self.send(target, cmd, param)
    # no inotify
    
    pass

class StortangleClient(StortangleCommon):
    def __init__(self, storage_path='~/stortangle', host, username, password, port=2200, name=None):
        StortangleCommon.__init__(self, storage_path)
        self.inotify = InotifyWatcher(self.storage_path,queue=self.queue)
        self.inotify.start(threaded=True)
        self.server_path = None
        self.ssh = ChannelHandlerClientStortangle(host, username, password, port, self.queue, name)
        # add inotify watch
        # read action from server
        pass
    
    def parse_message(self, message):
        cmd, param = message
        print 'parse_message [%s]: %s' % (cmd, param)
        if cmd == 'srvpath':
            self.server_path = param
        elif cmd == 'rsync':
            self.rsync_pull(param)
        elif cmd == 'delete':
            self.inotify.join()
            self.rm(param)
            self.inotify.start()

    def rsync(self, cmds):
        cmds = ['rsync', '-a'] + cmds
        print cmds
        #result = subprocess.check_output(cmds)
    
    def get_server_path(self, path):
        return self.target + ':' + os.path.join(self.server_path, path)
    
    def get_local_path(self, path):
        return os.path.join(self.storage_path, path)
    
    def rsync_push(self, path):
        #self.ssh.send('disable_inotify')
        from_path = self.get_local_path(path)
        to_path = self.get_server_path(path)
        self.rsync([from_path, to_path])
        self.ssh.send('rsync','done')
        #self.ssh.send('enable_inotify')
    
    def rsync_pull(self, path):
        self.inotify.join()
        from_path = self.get_server_path(path)
        to_path = self.get_local_path(path)
        self.rsync([from_path, to_path])
        self.inotify.start()


if __name__ == "__main__":
    import sys
    args = sys.argv
    print 'args', args
    exit(0)
    if len(args) == 1:
        allowed_users = {'bucky': 'foo'}
        Server(ChannelHandlerServerTest, allowed_users=allowed_users)
    else:
        client('localhost', 'bucky', 'foo', ChannelHandlerClientTest)
# 1 Thread inotify add to queue
# 1 thread ssh add to queue
# 1 main thread, save