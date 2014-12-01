#!/usr/bin/env python

import os
import shutil
import subprocess

import time
import threading
import multiprocessing

import ssh_rpc
import inotify
"""
TODO:
Check Ack, if no re send


Client
1. Read sql lite and threat
2. Do loop

Server
1. Read sql lite and threat
2. Do loop
"""


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
        self.send(('name', self.name))
        
    def send(self, msg):
        cmd, params = msg
        #print 'SSH send %s(%s)' % (cmd, params)
        super(ChannelHandlerClientStortangle, self).send('%s,%s' % (cmd, params))
    
    def _on_receive_cmd(self, queue, cmd):
        #print 'SSH on_received %s' % cmd
        cmd, param = cmd.split(',', 1)
        if cmd == 'who':
            self.send('name', self.name)
        queue.put((cmd, param))

class ChannelHandlerServerStortangle(ssh_rpc.ChannelHandlerServer):
    name = None
    
    def _on_receive_cmd(self, queue, cmd):
        #print 'SSH on_received %s' % cmd
        cmd, params = cmd.split(',', 1)
        if cmd == 'name':
            self.name = params
            params = self._id
        if self.name is None:
            self.send('who', '')
            return
        queue.put((self.name, cmd, params))
    
    def send(self, msg):
        cmd, params = msg
        #print 'SSH send %s(%s)' % (cmd, params)
        super(ChannelHandlerServerStortangle, self).send('%s,%s' % (cmd, params))
    
    def _in_loop_call(self):
        pass

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
        self.__event = multiprocessing.Event()
        self.__event.set()
        self.queue = multiprocessing.Queue()
        #ssh_from_pipe, ssh_to_pipe = multiprocessing.Pipe()
        #inotify_from_pipe, inotify_to_pipe = multiprocessing.Pipe()
        pass
    
    def stop(self):
        self.__event.clear()
    
    def is_running(self):
        return self.__event.is_set()
    
    def log(self, msg, level=1):
        print 'Stortangle %s' % msg
    
    def rm(self, filename):
        full_path = os.path.join(self.storage_path, filename)
        print 'rm file %s' % full_path
        #shutil.rmtree(full_path)
    
    def mv(self, old, new):
        old = os.path.join(self.storage_path, old)
        new = os.path.join(self.storage_path, new)
        print 'rename %s -> %s' % (old, new)
        #os.rename(old, new)
        
    def main_loop(self):
        while self.__event.is_set():
            if not self.queue.empty():
                while not self.queue.empty():
                    self.parse_message(self.queue.get())
                    #self.queue.task_done()
    
    def parse_message(self, message):
        pass
    
    def strip_path(self, path):
        new_path = path[len(self.storage_path):]
        if new_path[0] == '/':
            new_path = new_path[1:]
        return new_path

class StortangleServer(StortangleCommon):
    def __init__(self, storage_path='~/stortangle', port=2200, allowed_users=None):
        StortangleCommon.__init__(self, storage_path)
        self.ssh = ssh_rpc.Server(ChannelHandlerServerStortangle, port=port, allowed_users=allowed_users, queue=self.queue, threaded=True)
        self.routing_table = {}
        e = None
        try:
            self.main_loop()
        except Exception as e:
            pass
        except KeyboardInterrupt as e:
            pass
        except SystemExit as e:
            pass
        print 'Stortangle Exception in server loop'
        try:
            self.send_all('quit', '')
        except:
            pass
        #for client in self.routing_table:
            #self.routing_table[client].disconnect()
        self.ssh.stop()
        if isinstance(e, Exception):
            raise e
    
    def parse_message(self, message):
        src, cmd, param = message
        self.log('parse_message from %s [%s]: %s' % (src, cmd, param))
        if cmd == 'name':
            #self.routing_table[src] = param
            self.routing_table[src] = self.ssh.get_handler_by_id(param)
            self.send(src, 'srvpath', self.storage_path)
        elif cmd == 'rsync':
            self.send_all_but_target(src, 'rsync', param)
        elif cmd in ['delete', 'delete_dir']:
            self.rm(param)
            self.send_all_but_target(src, cmd, param)
        elif cmd in ['move','move_dir']:
            self.mv(*param.split(','))
            self.send_all_but_target(src, cmd, param)
    
    def send(self, target, cmd, param):
        self.log('send(%s,%s,%s)' % (target, cmd, param))
        self.routing_table[target].send_from_ext((cmd, param))
        #self.ssh.send_to_id(self.routing_table[target], (cmd, param))
        #self.routing_table[target].send(cmd, param)
    
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
    def __init__(self, server_host, username, password, storage_path='~/stortangle', port=2200, name=None, rsync_username=None):
        StortangleCommon.__init__(self, storage_path)
        if rsync_username is None:
            rsync_username = username
        self.rsync_target = '%s@%s' % (rsync_username, server_host)
        self.inotify = InotifyWatcher(self.storage_path,queue=self.queue)
        self.inotify_threaded = True
        self.inotify.start(threaded=self.inotify_threaded)
        self.server_path = None
        self.ssh = ChannelHandlerClientStortangle(server_host, username, password, port, self.queue, name)
        e = None
        try:
            self.main_loop()
        except Exception as e:
            pass
        except KeyboardInterrupt as e:
            pass
        except SystemExit as e:
            pass
        print 'Stop inotify'
        self.inotify.stop()
        try:
            print 'Send stop to server'
            self.send('quit', '')
        except:
            pass
        print 'Disconnect ssh'
        self.ssh.disconnect()
        if isinstance(e, Exception):
            raise e
    
    def parse_message(self, message):
        cmd, param = message
        print 'parse_message [%s]: %s' % (cmd, param)
        if cmd == 'srvpath':
            self.server_path = param
        elif cmd == 'rsync':
            self.rsync_pull(param)
        elif cmd == 'inotify':
            for action, arg in param:
                if action in ['delete', 'delete_dir']:
                    self.send(action, self.strip_path(arg))
                elif action in ['add', 'add_dir']:
                    """
                    TODO: Get the real path to do rsync only on specified path
                    """
                    print 'Do rsync'
                    self.rsync_push('')
                elif action in ['move', 'move_dir']:
                    arg = (self.strip_path(arg[0]), self.strip_path(arg[1]))
                    self.send(action, ','.join(arg))
        elif cmd in ['delete', 'delete_dir']:
            self.inotify.join()
            self.rm(param)
            self.inotify.start(threaded=self.inotify_threaded)
        elif cmd in ['move','move_dir']:
            self.inotify.join()
            self.mv(*param.split(','))
            self.inotify.start(threaded=self.inotify_threaded)
        elif cmd == 'quit':
            #self.stop()
            pass

    def rsync(self, cmds):
        cmds = ['rsync', '-a'] + cmds
        print cmds
        #result = subprocess.check_output(cmds)
    
    def get_server_path(self, path):
        return self.rsync_target + ':' + os.path.join(self.server_path, path)
    
    def get_local_path(self, path):
        return os.path.join(self.storage_path, path)
    
    def rsync_push(self, path):
        #self.ssh.send('disable_inotify')
        from_path = self.get_local_path(path)
        to_path = self.get_server_path(path)
        self.rsync([from_path, to_path])
        self.send('rsync','')
        #self.ssh.send('enable_inotify')
    
    def rsync_pull(self, path):
        self.inotify.join()
        from_path = self.get_server_path(path)
        to_path = self.get_local_path(path)
        self.rsync([from_path, to_path])
        self.inotify.start()
    
    def send(self, action, param):
        self.ssh.send_from_ext((action, param))


if __name__ == "__main__":
    import sys
    args = sys.argv
    print 'args', args
    if len(args) == 1:
        print 'Usage:'
        print 'Server:'
        print '%s <storage_path>' % args[0]
        print
        print 'Client:'
        print '%s <storage_path> <node_name>' % args[0]
    elif len(args) == 2:
        storage_path = args[1]
        allowed_users = {'bucky': 'foo'}
        StortangleServer(storage_path=storage_path, port=2200, allowed_users=allowed_users)
    else:
        serverhost = 'localhost'
        username = 'bucky'
        password = 'foo'
        storage_path = args[1]
        node_name = args[2]
        StortangleClient(serverhost, username, password, storage_path=storage_path, port=2200, name=node_name)

# 1 Thread inotify add to queue
# 1 thread ssh add to queue
# 1 main thread, save