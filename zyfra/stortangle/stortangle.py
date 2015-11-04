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
import message_queue
import threaded_loop
"""
TODO:
Finished, to test

Client:
- on receive quit, disconnect ssh, and relaunch
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
    def __init__(self, host, username, password, port=2200, treat_queue=None, send_queue=None, name=None):
        self.name = name
        self.__send_queue = send_queue
        ssh_rpc.ChannelHandlerClient.__init__(self, host, username, password, port, queue, threaded=True)
    
    def _init(self):
        self.send({'action': 'name', 'name': self.name})
    
    def _on_receive_cmd(self, queue, cmd):
        #print 'SSH on_received %s' % cmd
        action = cmd['action']
        if action == 'who':
            self.send({'action': 'name', 'name': self.name})
            return
        id = cmd['id']
        if action == 'ack':
            self.__send_queue.mark_as_treated(id=id)
            return
        queue.put(cmd)
        self.send({'action': 'ack', 'id': id})

class ChannelHandlerServerStortangle(ssh_rpc.ChannelHandlerServer):
    name = None
    
    def __init__(self, client_socket, id, allowed_users, client_addr, treat_queue=None, log_level=2, send_queue=None, **kargs):
        self.__send_queue = send_queue
        ssh_rpc.ChannelHandlerServer.__init__(self, client_socket, id, allowed_users, client_addr, queue=treat_queue, log_level=2, **kargs)
    
    def _on_receive_cmd(self, queue, cmd):
        #print 'SSH on_received %s' % cmd
        action = cmd['action']
        if action == 'name':
            self.name = cmd['name']
            cmd['myid'] = self._id
        if self.name is None:
            self.send({'action':'who'})
            return
        id = cmd['id']
        if action == 'ack':
            self.__send_queue.mark_as_treated(id=id, host=self.name)
            return
        if queue.exists(id=id, host=self.name):
            return
        cmd['host'] = self.name
        queue.put(cmd)
        self.send({'action': 'ack', 'id': id})
    
    #def send(self, msg):
    #    cmd, params = msg
        #print 'SSH send %s(%s)' % (cmd, params)
    #    super(ChannelHandlerServerStortangle, self).send('%s,%s' % (cmd, params))
    
    def _in_loop_call(self):
        pass

"""def start_ssh_server(port, ):
    allowed_users = {'bucky': 'foo'}
    ssh_rpc.Server(ChannelHandlerServerStortangle, allowed_users=allowed_users)

def start_ssh_client(host, username, password, port, queue, name):
    ChannelHandlerClientStortangle(host, username, password, port, queue, name)"""

inotify_threaded = True

class ActionMessageQueue(message_queue.MessageQueue):
    action = message_queue.FieldText()
    file1 = message_queue.FieldText()
    file2 = message_queue.FieldText()

class MessageQueueMsg2sendSrv(ActionMessageQueue):
    _db_name = 'msg_queue2send_srv.db'
    id = FieldInt() # No primary key
    host = message_queue.FieldText()

class MessageQueueMsg2sendClt(ActionMessageQueue):
    _db_name = 'msg_queue2send_clt.db'

class InotifyWatcher(inotify.PathWatcher):
    def _on_events(self, events):
        for event in events:
            action, params = event
            if action in ['move', 'move_dir']:
                file1, file2 = params
                self._queue.add(action=action, file1=file1, file2=file2)
            else:
                self._queue.add(action=action, file1=params)

class MessageQueue2treat(ActionMessageQueue):
    _db_name = 'msg_queue2treat.db'

"""class MessageQueueT(object):
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
        return res"""

#Decorator
def disable_inotify(fx):
    def new_fx(self, *args):
        if self.__inotify is None:
            return fx(self, *args)
        self.__inotify.join()
        res = fx(self, *args)
        self.__inotify.start(threaded=inotify_threaded)
        return res
    return new_fx

class DiskAction(object):
    def __init__(self, storage_path, inotify=None, rsync_target=None):
        self.__inotify = inotify
        self.__rsync_target = rsync_target
        self.__storage_path = storage_path
        self.__server_path = None
    
    def set_server_path(self, server_path):
        self.__server_path = server_path
    
    @disable_inotify
    def rm(self, filename):
        full_path = os.path.join(self.__storage_path, filename)
        if os.path.isdir(full_path):
            self.rm_dir(full_path)
        else:
            self.rm_file(full_path)
        return True
    
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
        return True
    
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
        if self.__server_path is None:
            return False
        #self.ssh.send('disable_inotify')
        from_path = self.get_local_path(path)
        to_path = self.get_server_path(path)
        self.rsync([from_path, to_path])
        return True
        """self.send('rsync','')"""
        #self.ssh.send('enable_inotify')
    
    @disable_inotify
    def rsync_pull(self, path=''):
        if self.__server_path is None:
            return False
        from_path = self.get_server_path(path)
        to_path = self.get_local_path(path)
        self.rsync([from_path, to_path])
        return True


class Worker(threaded_loop.ThreadedLoop):
    def __init__(self, message_queue):
        self._message_queue = message_queue
        super(Worker, self).__init__()
    
    def get_next(self):
        return self._message_queue.get_next()
    
    def loop(self):
        while self._message_queue.is_msg_available():
            message = self.get_next()
            if self.treat(message):
                self._message_queue.mark_as_treated(id=message.id)
    
    def treat(self, msg):
        pass

class DiskTreatmentWorker(Worker):
    def __init__(self, message_queue, disk_action):
        self.__disk_action = disk_action
        super(Worker, self).__init__(message_queue)
        
    def treat(self, msg):
        cmd = msg.action
        if cmd in ['delete', 'delete_dir']:
            self.__disk_action.rm(msg.file1)
        elif cmd in ['move','move_dir']:
            self.__disk_action.mv(msg.file1, msg.file2)
        elif cmd == 'rsync_push':
            self.__disk_action.rsync_push(msg.file1)
        elif cmd == 'rsync_pull':
            self.__disk_action.rsync_pull(msg.file1)
        return True

class SendWorkerClient(Worker):
    def __init__(self, message_queue, channel_handler):
        self.__channel_handler = channel_handler
        super(Worker, self).__init__(message_queue)

    def treat(self, data):
        self.__channel_handler.send(data)
        self.message_queue.wait_treated(5, **data) #5 seconds timeout
        return False

class SendWorkerServer(Worker):
    def __init__(self, message_queue, channel_handler):
        self.__channel_handler = channel_handler
        self.__last_host = None
        super(Worker, self).__init__(message_queue)
    
    def get_next(self):
        hosts = [r.host for r in self._message_queue.get_next_group_by('host')]
        if len(hosts) == 1 or self.__last_host not in hosts:
            self.__last_host = hosts[0]
        else:
            hosts.sort()
            index = hosts.index(self.__last_host)
            index += 1
            if index >= len(hosts):
                index = 0
            self.__last_host = hosts[index]
            
        return self._message_queue.get_next(host=self.__last_host)

    def treat(self, data):
        self.__channel_handler.send_now(data['host'], data)
        self.message_queue.wait_treated(5, **data) #5 seconds timeout
        return False

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
        self.sending_queue = MessageQueueMsg2sendSrv()
        worker = SendWorkerServer(self.sending_queue, self)
        self.disk_action = DiskAction(storage_path=storage_path)
        self.ssh = ssh_rpc.Server(ChannelHandlerServerStortangle, port=port, allowed_users=allowed_users, queue=self.queue, threaded=True, send_queue=sending_queue)
        self.routing_table = {}
        self.last_received_id = {}
        e = None
        worker.start()
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
            self.send_all({'action':'quit'})
        except:
            pass
        #for client in self.routing_table:
            #self.routing_table[client].disconnect()
        worker.join()
        self.ssh.stop()
        if isinstance(e, Exception):
            raise e
    
    def parse_message(self, message):
        src = message['host']
        cmd = message['action']
        self.log('parse_message from %s [%s]: %s' % (src, cmd, message))
        id = message['id']
        if self.last_received_id.get(src) == id:
            return
        self.last_received_id[src] = id
        if cmd == 'name':
            #self.routing_table[src] = param
            self.routing_table[src] = self.ssh.get_handler_by_id(message['myid'])
            self.send(src, {'action': 'srvpath', 'path':self.storage_path})
        elif cmd == 'rsync':
            self.send_all_but_target(src, message)
        elif cmd in ['delete', 'delete_dir']:
            self.disk_action.rm(message['file1'])
            self.send_all_but_target(src, message)
        elif cmd in ['move','move_dir']:
            self.disk_action.mv(message['file1'], message['file2'])
            self.send_all_but_target(src, message)
    
    def send_now(self, target, data):
        self.log('send_now(%s,%s)' % (target, repr(data)))
        if target not in self.routing_table:
            return
        self.routing_table[target].send_from_ext(data)
    
    def send(self, target, data):
        self.log('send(%s,%s)' % (target, repr(data)))
        self.sending_queue.add(data)
        #self.ssh.send_to_id(self.routing_table[target], (cmd, param))
        #self.routing_table[target].send(cmd, param)
    
    def send_all_but_target(self, the_target, data):
        for target in self.routing_table:
            if target == the_target:
                continue
            self.send(target, data)
    
    def send_all(self, data):
        for target in self.routing_table:
            self.send(target, data)
    # no inotify
    
    pass

class StortangleClient(StortangleCommon):
    def __init__(self, server_host, username, password, storage_path='~/stortangle', port=2200, name=None, rsync_username=None):
        StortangleCommon.__init__(self, storage_path)
        if rsync_username is None:
            rsync_username = username
        self.rsync_target = '%s@%s' % (rsync_username, server_host)
        self.message2send = MessageQueueMsg2sendClt()
        self.message2treat = MessageQueue2treat()
        self.inotify = InotifyWatcher(self.storage_path,queue=self.queue)
        self.disk_action = DiskAction(storage_path=storage_path, inotify=self.inotify, rsync_target=self.rsync_target)
        self.inotify_threaded = True
        self.inotify.start(threaded=self.inotify_threaded)
        self.server_path = None
        self.ssh = ChannelHandlerClientStortangle(server_host, username, password, port, self.message2treat, send_queue=self.message2send, name=name)
        disk_worker = DiskTreatmentWorker(self.message2treat, self.disk_action)
        sending_worker = SendWorkerClient(self.message2send, self)
        sending_worker.start()
        disk_worker.start()
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
            self.send({'action':'quit'})
        except:
            pass
        print 'Disconnect ssh'
        disk_worker.stop()
        sending_worker.stop()
        disk_worker.join()
        sending_worker.join()
        self.ssh.disconnect()
        if isinstance(e, Exception):
            raise e
    
    def parse_message(self, message):
        cmd = message['action']
        self.log('parse_message [%s]: %s' % (cmd, param))
        if cmd == 'srvpath':
            self.disk_action.set_server_path(message['path'])
            #self.rsync_pull()
            #self.rsync_push()
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
        else:
            self.message2treat.add(message)
    
    def send(self, data):
        self.ssh.send_from_ext(data)


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