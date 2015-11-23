#!/usr/bin/env python

import os
import shutil
import subprocess
import traceback

import time
from datetime import datetime
import threading
from Queue import Queue
#import multiprocessing

import sqlite3

import ssh_rpc
import inotify
from .. import message_queue
import threaded_loop
"""
TODO:
- Server: remove ghost ssh client instance: partialy done
- Add inotify on server too
"""


'cmd,timestamp,'
'addchg,timestamp,filenames'
'del,timestamp,filenames'

dry_run = False

def str2timestamp(txt):
    return time.mktime(datetime.strptime(txt, "%Y-%m-%d %H:%M:%S.%f").timetuple())

def rsync(cmds):
    return subprocess.check_output(['rsync', '-azuH'] + cmds)

class ChannelHandlerClientStortangle(ssh_rpc.ChannelHandlerClient):
    def __init__(self, host, username, password, port=2200, queue=None, send_queue=None, name=None):
        self.name = name
        self.__send_queue = send_queue
        ssh_rpc.ChannelHandlerClient.__init__(self, host, username, password, port, queue, threaded=True)
    
    def _init(self):
        self.send({'action': 'name', 'name': self.name})
    
    def _on_receive_data(self, queue, cmd):
        print 'SSH on_received %s' % cmd
        action = cmd['action']
        if action == 'who':
            self.send({'action': 'name', 'name': self.name})
            return
        if 'id' in cmd:
            id = cmd['id']
            del cmd['id']
        else:
            id = None
        
        if action == 'ack' and id is not None:
            self.__send_queue.mark_as_treated(id=id)
            return
        queue.put(cmd)
        #queue.add(**cmd)
        if id is not None:
            print 'ACK id[%s]' % id
            self.send({'action': 'ack', 'id': id})

class ChannelHandlerServerStortangle(ssh_rpc.ChannelHandlerServer):
    name = None
    
    def __init__(self, client_socket, id, allowed_users, client_addr, treat_queue=None, log_level=0, send_queue=None, **kargs):
        self.__send_queue = send_queue
        ssh_rpc.ChannelHandlerServer.__init__(self, client_socket, id, allowed_users, client_addr, queue=treat_queue, log_level=log_level, **kargs)
    
    def _on_receive_data(self, queue, cmd):
        print 'SSH on_received %s' % cmd
        action = cmd['action']
        if action == 'name':
            self.name = cmd['name']
            cmd['myid'] = self._id
        if self.name is None:
            self.send({'action':'who'})
            return
        id = cmd.get('id')
        if action == 'ack' and id is not None:
            self.__send_queue.mark_as_treated(id=id, host=self.name)
            return
        #if id is not None and queue.exists(id=id, host=self.name):
        #    return
        cmd['host'] = self.name
        queue.put(cmd)
        if id is not None:
            print 'ACK id[%s]' % id
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
    id = message_queue.FieldInt() # No primary key
    host = message_queue.FieldText()

class MessageQueueMsg2sendClt(ActionMessageQueue):
    _db_name = 'msg_queue2send_clt.db'
    
    def add(self, **kargs):
        if 'id' in kargs:
            del kargs['id']
        super(MessageQueueMsg2sendClt, self).add(**kargs)

class InotifyWatcher(inotify.PathWatcher):
    def _on_events(self, events):
        last_action = None
        for event in events:
            action, params = event
            if last_action == 'add' and action == 'add':
                continue
            if action in ['move', 'move_dir']:
                file1, file2 = params
                self._queue.put({'action': action, 'file1': file1, 'file2': file2, 'inotify': True})
            else:
                self._queue.put({'action': action, 'file1': params, 'inotify': True})
            last_action = action

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
        if self._inotify is None:
            return fx(self, *args)
        self._inotify.join()
        res = fx(self, *args)
        self._inotify.start(threaded=inotify_threaded)
        return res
    return new_fx

def tryfalse(fx):
    def new_fx(self, *args, **kargs):
        try:
            return fx(self, *args)
        except:
            traceback.print_exc()
            return False
    return new_fx

class DiskAction(object):
    def __init__(self, storage_path, inotify=None, rsync_target=None):
        self._inotify = inotify
        self.__rsync_target = rsync_target
        self.__storage_path = storage_path
        self.__server_path = None
    
    def set_server_path(self, server_path):
        print 'Server path set to: %s' % server_path
        self.__server_path = server_path
    
    @disable_inotify
    @tryfalse
    def rm(self, filename, timestamp=None):
        full_path = os.path.join(self.__storage_path, filename)
        
        if timestamp is not None and timestamp <= os.stat(full_path).st_mtime:
            return True # the file on disk is more recent, do not delete
        if os.path.isdir(full_path):
            self._rm_dir(full_path)
        else:
            self._rm_file(full_path)
        return True
    
    def _rm_file(self, filename):
        print 'rm file %s' % filename
        if not dry_run:
            os.remove(filename)
    
    def _rm_dir(self, filename):
        print 'rm dir %s' % filename
        if not dry_run:
            shutil.rmtree(filename)
    
    @disable_inotify
    @tryfalse
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
            print 'Doing rsync'
            result = subprocess.check_output(cmds)
    
    def get_server_path(self, path):
        print 'get_server_path: [%s] srv_path[%s]' % (path, self.__server_path)
        return self.__rsync_target + ':' + os.path.join(self.__server_path, path)
    
    def get_local_path(self, path):
        return os.path.join(self.__storage_path, path)
    
    @tryfalse
    def rsync_push(self, path=''):
        if self.__server_path is None:
            return False
        #self.ssh.send('disable_inotify')
        path='' # Alway sync all
        from_path = self.get_local_path(path)
        to_path = self.get_server_path(path)
        self.rsync([from_path, to_path])
        return True
        """self.send('rsync','')"""
        #self.ssh.send('enable_inotify')
    
    @disable_inotify
    @tryfalse
    def rsync_pull(self, path=''):
        if self.__server_path is None:
            return False
        path='' # Alway sync all
        from_path = self.get_server_path(path)
        to_path = self.get_local_path(path)
        self.rsync([from_path, to_path])
        return True


class Worker(threaded_loop.ThreadedLoop):
    def __init__(self, message_queue, log_level=0):
        self._message_queue = message_queue
        self._log_level = log_level
        super(Worker, self).__init__(log_level=log_level)
    
    def get_next(self):
        return self._message_queue.get_next()
    
    def _loop(self):
        while self._message_queue.is_msg_available() and self.is_running():
            message = self.get_next()
            if self.treat(message):
                self._message_queue.mark_as_treated(id=message.id)
    
    def treat(self, msg):
        pass

class DiskTreatmentWorker(Worker):
    def __init__(self, message_queue, disk_action, sending_queue=None, main_queue=None, log_level=0):
        self.__disk_action = disk_action
        self.__sending_queue = sending_queue
        self.__main_queue = main_queue
        self.__remote_ready = threading.Event()
        super(DiskTreatmentWorker, self).__init__(message_queue, log_level)
    
    def add2main_queue(self, data):
        if self.__main_queue is not None:
            self.__main_queue.put(data)
    
    def set_remote_ready(self):
        self.__remote_ready.set()
    
    def treat(self, msg):
        cmd = msg.action
        timestamp = str2timestamp(msg.date)
        if cmd in ['delete', 'delete_dir']:
            self.__disk_action.rm(msg.file1, timestamp=timestamp)
        elif cmd in ['move','move_dir']:
            self.__disk_action.mv(msg.file1, msg.file2)
        elif cmd == 'rsync_push':
            self.__remote_ready.clear()
            while True:
                self.add2main_queue({'action': 'get_server_lock'})
                if self.__remote_ready.wait(1):
                    break
                if not self.is_running():
                    return False
            
            push_ok = self.__disk_action.rsync_push(msg.file1)
            self.__sending_queue.add(action='release_server_lock')
            if push_ok:
                if self.__sending_queue is not None:
                    msg['action'] = 'rsync_pull'
                    #del msg['id']
                    print 'Sending_queue adding: %s' % msg
                    self.__sending_queue.add(**msg)
            #return False
        elif cmd == 'rsync_pull':
            self.__disk_action.rsync_pull(msg.file1)
        elif cmd == 'srvpath':
            print msg
            self.__disk_action.set_server_path(msg.file1)
        return True

class SendWorkerClient(Worker):
    def __init__(self, message_queue, channel_handler, log_level=0):
        self.__channel_handler = channel_handler
        super(SendWorkerClient, self).__init__(message_queue, log_level=log_level)

    def treat(self, data):
        if data is None:
            return False
        print 'sendworker client treat %s' % data
        self.__channel_handler.send(data)
        self._message_queue.wait_treated(5, **data) #5 seconds timeout
        return False

class SendWorkerServer(Worker):
    def __init__(self, message_queue, channel_handler, log_level=0):
        self.__channel_handler = channel_handler
        self.__last_host = None
        super(SendWorkerServer, self).__init__(message_queue, log_level=log_level)
    
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
        if data is None:
            return False
        print 'sendworker srv treat %s' % data
        self.__channel_handler.send_now(data['host'], data)
        self._message_queue.wait_treated(5, **data) #5 seconds timeout
        return False

class StortangleCommon(object):
    def __init__(self, storage_path='~/stortangle'):
        self.storage_path = storage_path
        self.__event = threading.Event()
        self.__event.set()
        self.queue = Queue()
        #ssh_from_pipe, ssh_to_pipe = multiprocessing.Pipe()
        #inotify_from_pipe, inotify_to_pipe = multiprocessing.Pipe()
        pass
    
    def stop(self):
        self.__event.clear()
    
    def is_running(self):
        return self.__event.is_set()
    
    def log(self, msg, level=1):
        print 'Stortangle %s' % msg
    
    def loop(self):
        pass
        
    def _main_loop(self):
        while self.__event.is_set():
            self.loop()
            try:
                msg = self.queue.get(timeout=0.5)
            except KeyboardInterrupt:
                print 'StortangleCommon Quitting'
                break
            except:
                continue
            self.parse_message(msg)
            self.queue.task_done()
            if not self.queue.empty():
                while not self.queue.empty():
                    self.parse_message(self.queue.get())
                    self.queue.task_done()
    
    def parse_message(self, message):
        pass
    
    def strip_path(self, path):
        new_path = path[len(self.storage_path):]
        if new_path[0] == '/':
            new_path = new_path[1:]
        return new_path

class StortangleServer(StortangleCommon):
    def __init__(self, storage_path='~/stortangle', port=2200, allowed_users=None, node_names=None):
        # allowed_users (dict of string): {'username': 'password'}
        # node_names (list of string): used for send to all
        StortangleCommon.__init__(self, storage_path)
        self.sending_queue = MessageQueueMsg2sendSrv()
        worker = SendWorkerServer(self.sending_queue, self)
        self.disk_action = DiskAction(storage_path=storage_path)
        self._node_names = node_names
        self._server_lock = None
        try:
            self.ssh = ssh_rpc.Server(ChannelHandlerServerStortangle, port=port, allowed_users=allowed_users, queue=self.queue, threaded=True, send_queue=self.sending_queue)
            self.routing_table = {}
            self.last_received_id = {}
            e = None
            worker.start()
            self._main_loop()
        except Exception as e:
            traceback.print_exc()
            #traceback.print_stack()
            pass
        except KeyboardInterrupt as e:
            pass
        except SystemExit as e:
            pass
        print 'Stortangle Exception in server loop'
        try:
            self.send_all({'action':'quit'}, now=True)
        except:
            pass
        #for client in self.routing_table:
            #self.routing_table[client].disconnect()
        worker.join()
        self.ssh.stop()
        if isinstance(e, Exception):
            raise e
    
    #def loop(self):
        #print 'routing table: %s' % ','.join(self.routing_table.keys())
    
    def parse_message(self, message):
        print 'Message %s' % repr(message)
        src = message['host']
        cmd = message['action']
        self.log('parse_message from %s [%s]: %s' % (src, cmd, message))
        id = message.get('id')
        if id is not None and self.last_received_id.get(src) == id:
            return
        self.last_received_id[src] = id
        if cmd == 'name':
            #self.routing_table[src] = param
            self.routing_table[src] = self.ssh.get_handler_by_id(message['myid'])
            self.send_now(src, {'action': 'srvpath', 'file1':self.storage_path})
        elif cmd == 'rsync_pull':
            self.send_all_but_target(src, message)
        elif cmd in ['delete', 'delete_dir']:
            try:
                timestamp = str2timestamp(message['date'])
                self.disk_action.rm(message['file1'], timestamp=timestamp)
                self.send_all_but_target(src, message)
            except:
                traceback.print_exc()
        elif cmd in ['move','move_dir']:
            try:
                self.disk_action.mv(message['file1'], message['file2'])
                self.send_all_but_target(src, message)
            except:
                traceback.print_exc()
        elif cmd == 'get_server_lock':
            if not self._server_lock:
                self._server_lock = src
                self.send_now(src, {'action':'got_server_lock'})
            elif self._server_lock == src:
                self.send_now(src, {'action':'got_server_lock'})
        elif cmd == 'release_server_lock':
            if self._server_lock == src:
                self._server_lock = None
    
    def send_now(self, target, data):
        self.log('send_now(%s,%s)' % (target, repr(data)))
        if target not in self.routing_table:
            return
        self.routing_table[target].send_from_ext(data)
    
    def send(self, target, data):
        data = data.copy()
        data['host'] = target
        self.log('send(%s,%s)' % (target, repr(data)))
        self.sending_queue.add(**data)
        #self.ssh.send_to_id(self.routing_table[target], (cmd, param))
        #self.routing_table[target].send(cmd, param)
    
    def get_all_node_names(self):
        if self._node_names:
            return self._node_names
        return self.routing_table.keys()
    
    def send_all_but_target(self, the_target, data):
        self.log('send_all_but_target(%s,%s)' % (the_target, repr(data))) 
        for target in self.get_all_node_names():
            if target == the_target:
                continue
            self.send(target, data)
    
    def send_all(self, data, now=False):
        for target in self.get_all_node_names():
            if now:
                self.send_now(target, data)
            else:
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
        self.inotify = InotifyWatcher(self.storage_path,queue=self.queue, relative_path=self.storage_path)
        self.disk_action = DiskAction(storage_path=storage_path, inotify=self.inotify, rsync_target=self.rsync_target)
        self.inotify_threaded = True
        self.inotify.start(threaded=self.inotify_threaded)
        self.server_path = None
        self.ssh = ChannelHandlerClientStortangle(server_host, username, password, port, queue=self.queue, send_queue=self.message2send, name=name)
        self.disk_worker = DiskTreatmentWorker(self.message2treat, self.disk_action, self.message2send, main_queue=self.queue, log_level=0)
        sending_worker = SendWorkerClient(self.message2send, self)
        sending_worker.start()
        self.disk_worker.start()
        e = None
        try:
            self._main_loop()
        except Exception as e:
            traceback.print_exc()
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
        self.disk_worker.stop()
        sending_worker.stop()
        self.disk_worker.join()
        sending_worker.join()
        self.ssh.disconnect()
        if isinstance(e, Exception):
            raise e
    
    def parse_message(self, message):
        cmd = message['action']
        self.log('parse_message ik %s' % (repr(message), ))
        if cmd == 'srvpath':
            self.disk_action.set_server_path(message['file1'])
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
        elif cmd == 'get_server_lock':
            self.send(message)
        elif cmd == 'got_server_lock':
            self.disk_worker.set_remote_ready()
        elif message.get('inotify'):
            if cmd == 'add':
                message['action'] = 'rsync_push'
                self.message2treat.add(**message)
            else:
                self.message2send.add(**message)
        else:
            self.message2treat.add(**message)
    
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
        StortangleServer(storage_path=storage_path, port=2200, allowed_users=allowed_users, node_names=['a','b'])
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