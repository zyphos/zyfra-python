#!/usr/bin/env python

import os
import shutil
import subprocess

import time
import threading
import multiprocessing

import sqlite3

import ssh_rpc
import inotify
"""
TODO:
Client:
- on receive quit, disconnect ssh, and relaunch
- make loop for queue processing (to send, to treat) check nb2send, nb2treat
- make nb2send, nb2treat thread safe, or use a lock (so we can use wait, in the loop)

Check Ack, if no re send


Client
1. Read sql lite and threat
2. Do loop

Server
1. Read sql lite and threat
2. Do loop

On event:
- File Deleted or FIle moved:
 Client1 - 'file deleted' > Server Send to all -> do rm localy -> client do rm
- File added
 Client1 - 'file added' > Send 'push incomming'  > 'ok for rsync'
 > rsync push  > send 'rsync finished'
"""


'cmd,timestamp,'
'addchg,timestamp,filenames'
'del,timestamp,filenames'

dry_run = False

def rsync(cmds):
    return subprocess.check_output(['rsync', '-azuH'] + cmds)

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

inotify_threaded = True

class InotifyWatcher(inotify.PathWatcher):
    def _on_events(self, queue, events):
        queue.put(('inotify', events))

class MessageQueue(object):
    def __init__(self, dbname='stortangle.db'):
        self.db = sqlite3.connect(dbname)
        self.create_table()
        self.nb2send = self.get_nb2send() # nb2send must be threat safe
        self.nb2treat = self.get_nb2treat() # nb2treat must be threat safe
    
    def create_table(self):
        cr = self.db.cursor()
        cr.execute('''CREATE TABLE IF NOT EXISTS messages_to_send
             (id INTEGER PRIMARY KEY ASC, host TEXT, date TEXT, action TEXT, file1 TEXT, file2 TEXT)''')
        cr.execute('''CREATE TABLE IF NOT EXISTS messages_received
             (id INTEGER, host TEXT, date TEXT, action TEXT, file1 TEXT, file2 TEXT, treated INTEGER)''')
        self.db.commit()
    
    def get_nb2send(self):
        cr = self.db.cursor()
        cr.execute("SELECT count(*) AS nb FROM messages_to_send")
        res = cr.fetchone()
        self.db.commit()
        return res['nb']
    
    def get_nb2treat(self):
        cr = self.db.cursor()
        cr.execute("SELECT count(*) AS nb FROM messages_received WHERE treated=0")
        res = cr.fetchone()
        self.db.commit()
        return res['nb']
    
    def add_msg_to_send(self, target_host, date, action, file1='', file2=''):
        cr = self.db.cursor()
        cr.execute("INSERT INTO messages_to_send (host,date,action,file1,file2) VALUES ('%s','%s','%s','%s','%s')" % (target_host, date, action, file1, file2))
        self.db.commit()
    
    def add_msg_received(self, id, src_host, date, action, file1, file2):
        cr = self.db.cursor()
        cr.execute("SELECT id,host FROM messages_received WHERE id=%s AND host='%s'" % (id, src_host))
        res = cr.fetchone()
        if res:
            return
        cr.execute("INSERT INTO messages_received (id,host,date,action,file1,file2,treated) VALUES (%s,'%s','%s','%s','%s','%s',0)" % (id, src_host, date, action, file1, file2))
        self.db.commit()
    
    def confirm_received(self, id):
        cr = self.db.cursor()
        cr.execute('DELETE FROM messages_to_send WHERE id=%s' % id)
        self.db.commit()
    
    def confirm_treated(self, id, host):
        cr = self.db.cursor()
        cr.execute("DELETE FROM messages_received WHERE treated=1 AND host='%s'" % (host,))
        cr.execute("UPDATE messages_received SET treated=1 WHERE id=%s AND host='%s'" % (id, host))
        self.db.commit()
    
    def get_next2treat(self):
        cr = self.db.cursor()
        cr.execute("SELECT id,host,date,action,file1,file2 FROM messages_received ORDER BY date,id LIMIT 1")
        res = cr.fetchone()
        self.db.commit()
        return res
    
    def get_next2send(self):
        cr = self.db.cursor()
        cr.execute("SELECT id,host,date,action,file1,file2 FROM messages_to_send ORDER BY id LIMIT 1")
        res = cr.fetchone()
        self.db.commit()
        return res

#Decorator
def disable_inotify(fx):
    def new_fx(self, *args):
        self.__inotify.join()
        res = fx(self, *args)
        self.__inotify.start(threaded=inotify_threaded)
        return res
    return new_fx

class DiskAction(object):
    def __init__(self, inotify, rsync_target, storage_path, server_path):
        self.__inotify = inotify
        self.__rsync_target = rsync_target
        self.__storage_path = storage_path
        self.__server_path = server_path
    
    @disable_inotify
    def rm(self, filename):
        full_path = os.path.join(self.__storage_path, filename)
        if os.path.isdir(full_path):
            self.rm_dir(full_path)
        else:
            self.rm_file(full_path)
    
    def rm_file(self, filename):
        print 'rm file %s' % filename
        if not dry_run:
            os.remove(filename)
    
    def rm_dir(self, filename):
        print 'rm dir %s' % filename
        if not dry_run:
            shutil.rmtree(filename)
    
    @disable_inotify
    def mv(self, old, new):
        old = os.path.join(self.__storage_path, old)
        new = os.path.join(self.__storage_path, new)
        print 'rename %s -> %s' % (old, new)
        if not dry_run:
            os.rename(old, new)
    
    def rsync(self, cmds):
        cmds = ['rsync', '-auH'] + cmds
        print cmds
        if not dry_run:
            result = subprocess.check_output(cmds)
    
    def get_server_path(self, path):
        return self.__rsync_target + ':' + os.path.join(self.__server_path, path)
    
    def get_local_path(self, path):
        return os.path.join(self.__storage_path, path)
    
    def rsync_push(self, path=''):
        #self.ssh.send('disable_inotify')
        from_path = self.get_local_path(path)
        to_path = self.get_server_path(path)
        self.rsync([from_path, to_path])
        """self.send('rsync','')"""
        #self.ssh.send('enable_inotify')
    
    @disable_inotify
    def rsync_pull(self, path=''):
        from_path = self.get_server_path(path)
        to_path = self.get_local_path(path)
        self.rsync([from_path, to_path])

class Worker(object):
    queue_def_name = ''
    queue_nb_def_name = ''

    def __init__(self, message_queue):
        self.__running_event = threading.Event()
        self.__data_ready_event = threading.Event()
        self.__data_ready_event.set()
    
    def thread(self, running_event, data_ready_event, message_queue):
        while not running_event.is_set():
            data_ready_event.wait()
            data_ready_event.clear()
            if not running_event.is_set():
                while getattr(message_queue, queue_nb_def_name):
                    msg = getattr(message_queue, queue_def_name)
                    self.treat(msg)
    
    def treat(self, msg):
        pass

    def data_are_ready(self):
        self.__data_ready_event.set()
    
    def stop(self):
        self.__running_event.set()
        self.__data_ready_event.set()

class TreatmentWorker(Worker):
    queue_def_name = 'get_next2treat'
    queue_nb_def_name = 'get_nb2treat'
    
    def __init__(self, message_queue, disk_action):
        self.disk_action = disk_action
        super(TreatmentWorker, self).__init__(message_queue)

    def treat(self, msg):
        cmd = msg['action']
        file1 = msg['file1']
        if cmd in ['delete', 'delete_dir']:
            disk_action.rm(file1)
        elif cmd in ['move','move_dir']:
            disk_action.mv(file1, msg['file2'])
        elif cmd == 'rsync_push':
            disk_action.rsync_push(file1)
        elif cmd == 'rsync_pull':
            disk_action.rsync_pull(file1)
        message_queue.confirm_treated(msg['id'], msg['host'])

class SendWorker(Worker):
    queue_def_name = 'get_next2send'
    queue_nb_def_name = 'get_nb2send'
    
    def __init__(self, message_queue, channel_handler):
        self.channel_handler = channel_handler
        super(TreatmentWorker, self).__init__(message_queue)

    def treat(self, msg):
        self.channel_handler.send()

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
        self.log('parse_message [%s]: %s' % (cmd, param))
        if cmd == 'srvpath':
            self.server_path = param
            self.rsync_pull()
            self.rsync_push()
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
                    self.log('Do rsync')
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
            self.ssh.join()
            if self.ssh.is_running():
                print 'running'
            else:
                print 'not running'
            print 'sleep 5'
            time.sleep(5)
            print 'hello'
            self.ssh.connect()
            pass

    
    
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