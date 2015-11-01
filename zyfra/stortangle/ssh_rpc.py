#!/usr/bin/env python

"""
TODO:
handle send to client 
"""

import base64
from binascii import hexlify
import os
import socket
import sys
import threading
from multiprocessing import Process, Pipe, Event, Queue
import traceback
import signal
import time
import json

import paramiko
#import zyfra.thread_process

private_key = os.path.expanduser("~/.ssh/id_rsa")
public_key = os.path.expanduser("~/.ssh/id_rsa.pub")


def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

def processed(fn):
    def wrapper(*args, **kwargs):
        Process(target=fn, args=args, kwargs=kwargs).start()
    return wrapper
# setup logging
#paramiko.util.log_to_file('demo_server.log')


class ParamikoServer (paramiko.ServerInterface):
    # 'data' is the output of base64.encodestring(str(key))
    # (using the "user_rsa_key" files)
    data = 'AAAAB3Nza1yc2EAAAABIwAAAIEAyO4it3fHlmGZWJaGrfeHOVY7RWO3P9M7hp' + \
           'fAu7jJ2d7eothvfeuoRFtJwhUmZDluRdFyhFY/hFAh76PJKGAusIqIQKlkJxMC' + \
           'KDqIexkgHAfID/6mqvmnSJf0b5W8v5h2pI/stOSwTQ+pxVhwJ9ctYDhRSlF0iT' + \
           'UWT10hcuO4Ks8='
     #good_pub_key = paramiko.RSAKey(filename=public_key)

    def __init__(self, allowed_users=None):
        if allowed_users is None:
            allowed_users = {}
        self._allowed_users = allowed_users
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        if username in self._allowed_users and self._allowed_users[username] == password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    #def check_auth_publickey(self, username, key):
    #    print 'Auth attempt with key: ' + hexlify(key.get_fingerprint())
    #    if (username == 'robey') and (key == self.good_pub_key):
    #        return paramiko.AUTH_SUCCESSFUL
    #    return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth,
                                  pixelheight, modes):
        return True
class ServerException(Exception):
    pass

class ChannelException(Exception):
    pass

class ChannelHandler(object):
    def __init__(self, queue=None, threaded=False, processed=False, log_level=0):
        self.__log_level = log_level
        self._event = threading.Event()
        self.__in_queue = Queue()
        if queue is None:
            self.__queue = Queue()
        else:
            self.__queue = queue
        self.connect()
    
    def connect(self):
        self._log('connecting', 2)
        self.__thread = None
        if processed:
            self.__thread = Process(target=self._start)
            self.__thread.start()
        elif threaded:
            self.__thread = threading.Thread(target=self._start)
            self.__thread.start()
        else:
            self._start()
    
    def _log(self, msg, level=1):
        if level <= self.__log_level:
            print 'SSH', msg
    
    def _start(self):
        self._event.set()
        self._init()
        self._loop()
        self._log('stopped', 2)
    
    def _init(self):
        pass
    
    def _in_loop_call(self):
        pass

    def _loop(self):
        data = ''
        while self._event.is_set() and self._is_ssh_connection_active():
            if self._channel.recv_ready():
                self._log('data ready', 3)
                res = self._channel.recv(1024)
                if len(res) == 0:
                    raise ChannelException('Channel closed')
                data += res
                recv_datas = data.split('\n')
                for recv_data in recv_datas[:-1]:
                    recv_data = base64.b64decode(recv_data)
                    recv_data = json.loads(recv_data)
                    self._log('_on_receive_data(%s)' % repr(recv_data), 2)
                    self._on_receive_data(self.__queue, recv_data)
                data = recv_datas[-1]
            if not self.__in_queue.empty():
                while not self.__in_queue.empty():
                    msg = self.__in_queue.get()
                    self.send(msg)
            self._in_loop_call()
            self._log('In _loop' + repr(self._event.is_set()), 3)
            time.sleep(0.5)
        self._log('Exiting loop: event(%s) ssh(%s)' % (repr(self._event.is_set()), repr(self._is_ssh_connection_active())), 3)
    
    def _is_ssh_connection_active(self):
        #transport = self._channel.get_transport() if self._channel else None
        return self._transport and self._transport.is_active()
    
    def send(self, data):
        self._log('send(%s)' % repr(data), 2)
        if not self._is_ssh_connection_active():
            raise ChannelException('Channel not active')
        data = json.dumps(data)
        data = base64.b64encode(data)
        self._channel.send(data + '\n')
    
    def send_from_ext(self, cmd):
        self.__in_queue.put(cmd)
    
    """def check_pipe_msg(self):
        if self.__pipe is None:
            return
        while(self.__pipe.poll()):
            self.on_pipe_msg(self.__pipe.recv())"""
    
    def _on_receive_data(self, queue, data):
        queue.put(data)
    
    """def _on_pipe_msg(self, msg):
        pass"""
    
    def disconnect(self):
        self._log('disconnecting', 2)
        self._event.clear()
    
    def is_running(self):
        return self._event.is_set()
    
    def join(self):
        self._log('joining', 2)
        self.disconnect()
        if self.__thread is None:
            return
        self.__thread.join()
    
    def get_queue(self):
        return self.__queue

class ChannelHandlerServer(ChannelHandler):
    def __init__(self, client_socket, id, allowed_users, client_addr, queue=None, log_level=2, **kargs):
        self._id = id
        self.__client_socket = client_socket
        self.__client_addr = client_addr
        self.__allowed_users = allowed_users
        self._transport = None
        ChannelHandler.__init__(self, queue=queue, processed=True, log_level=log_level)
    
    def _on_receive_data(self, queue, data):
        queue.put((self._id, data))
    
    def _get_id(self):
        return self._id

    def _start(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            self._transport = paramiko.Transport(self.__client_socket)
            try:
                self._transport.load_server_moduli()
            except:
                raise ServerException('(Failed to load moduli -- gex will be unsupported.)')
            host_key = paramiko.RSAKey(filename=private_key)
            self._transport.add_server_key(host_key)
            server = ParamikoServer(self.__allowed_users)
            try:
                self._transport.start_server(server=server)
            except paramiko.SSHException, x:
                raise ServerException('*** SSH negotiation failed.')
        
            # wait for auth
            self._channel = self._transport.accept(20)
            #self._channel.settimeout(0.01)
            if self._channel is None:
                raise ServerException('*** No channel.')
            self._log('Authenticated!')
        
            server.event.wait(10)
            if not server.event.isSet():
                raise ServerException('*** Client never asked for a shell.')
            try:
                ChannelHandler._start(self)
            except ChannelException as e:
                self._log('Channel Exception %s' % e)
                pass
            self._log('Closing session')
            self._channel.close()
        
        except:
            try:
                self._transport.close()
            except:
                pass
            raise

class Server(object):
    def __init__(self, channel_handler, port=2200, allowed_users=None, queue=None, threaded=False, **kargs):
        self.__event = threading.Event()
        self.__lock = threading.Lock()
        self.__event.set()
        self.__channel_handler = channel_handler
        self.__queue = queue
        self.__in_queue = Queue()
        self.__port = port
        self.__kargs = kargs
        if allowed_users is None:
            self.__allowed_users = {}
        else:
            self.__allowed_users = allowed_users.copy()
        if threaded:
            self.__thread = threading.Thread(target=self.__start)
            self.__thread.start()
        else:
            self.__start()
    
    def _loop_action(self):
        pass

    def __start(self):
        # now connect
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(0)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.__port))
        except Exception, e:
            raise ServerException('*** Bind failed: ' + str(e))
        
        sock.listen(100)
        print 'SSH Listening for connection ...'
        id = 0
        self.__handlers = {}
        while self.__event.is_set():
            try:
                client_socket, addr = sock.accept()
                print '\nSSH Got a connection from %s:%s' % (addr[0], addr[1])
                loglevel = 2
                p = self.__channel_handler(client_socket, id, self.__allowed_users, addr, self.__queue, loglevel, self.__kargs)
                self.__lock.acquire()
                self.__handlers[id] = p
                self.__lock.release()
                id += 1
            except KeyboardInterrupt:
                print 'SSH Quitting, waiting for end of connections'
                break
            except socket.error:
                time.sleep(0.1)
                #print 'SSH server Looping'
            if not self.__in_queue.empty():
                while not self.__in_queue.empty():
                    id, msg = self.__in_queue.get()
                    self.__handlers[id].send_from_ext(msg)
            self._loop_action()
        print 'Stoping server, waiting children'
        for id in self.__handlers:
            self.__handlers[id].join()
    
    def send_to_id(id, msg):
        self.__in_queue.put((id, msg))
    
    def get_handler_by_id(self, id):
        print 'SSH get_handler_by_id(%s)' % id
        self.__lock.acquire()
        handler = self.__handlers[id]
        self.__lock.release()
        return handler
    
    def stop(self):
        self.__event.clear()
    
    def is_running(self):
        return self.__event.is_set()
    
    def join(self):
        self.stop()
        if self.__thread is None:
            return
        self.__thread.join()

class ChannelHandlerClient(ChannelHandler):
    def __init__(self, host, username, password, port=2200, queue=None, threaded=False, log_level=3):
        hosts_filename = os.path.expanduser("~/.ssh/paramiko_known_hosts")
        #print hosts_filename
        self.__host = host
        self.__username = username
        self.__password = password
        self.__port = port
        self.__hosts_filename = hosts_filename
        self._transport = None
        #print client.get_host_keys()
        ChannelHandler.__init__(self, queue, threaded=threaded, log_level=log_level)
    
    def _start(self):
        self._event.set()
        while self._event.is_set():
            self._log('Trying to connect', 3)
            try:
                self._connect()
                #self._log('connect is active (%s)' % (repr(self._is_ssh_connection_active())))
                self._init()
                self._loop()
            except socket.error as e:
                self._log('Socket error %s' % e)
                time.sleep(1)
            except ChannelException as e:
                self._log('ChannelException: %s' % e)
                time.sleep(1)
        self._log('Ssh stopped')
    
    def _connect(self):
        self._client = paramiko.client.SSHClient()
        if os.path.isfile(self.__hosts_filename):
            self._client.load_host_keys(self.__hosts_filename) #'~/.ssh/known_hosts'
        self._client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        self._client.connect(self.__host, self.__port, username=self.__username, password=self.__password)
        self._client.save_host_keys(self.__hosts_filename)
        #print client.get_host_keys()
        self._channel = self._client.invoke_shell()
        self._transport = self._channel.get_transport()
        #self._log('connect is active (%s)' % (repr(self._is_ssh_connection_active())))
        #self._channel.settimeout(0.01)

class ChannelHandlerClientTest(ChannelHandlerClient):
    def _init(self):
        print 'ping'
        self.send('ping')
    
    def _on_receive_data(self, queue, data):
        print data
        self.disconnect()

class ChannelHandlerServerTest(ChannelHandlerServer):
    def _on_receive_data(self, queue, data):
        print '%s from %s' % (data, self._get_id())
        self.send('pong')

if __name__ == "__main__":
    import sys
    args = sys.argv
    
    if len(args) == 1:
        allowed_users = {'bucky': 'foo'}
        srv = Server(ChannelHandlerServerTest, allowed_users=allowed_users,threaded=True)
        try:
            while True:
                pass
        except:
            pass
        srv.stop()
    else:
        ChannelHandlerClientTest('localhost', 'bucky', 'foo')
