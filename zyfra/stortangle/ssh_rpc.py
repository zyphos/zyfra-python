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
    def __init__(self, queue=None, threaded=False, processed=False):
        self.__event = threading.Event()
        self.__event.set()
        if queue is None:
            self.__queue = Queue()
        else:
            self.__queue = queue
        self.__thread = None
        if processed:
            self.__thread = Process(target=self._start)
            self.__thread.start()
        elif threaded:
            self.__thread = threading.Thread(target=self._start)
            self.__thread.start()
        else:
            self._start()
    
    def _start(self):
        self._init()
        self._loop()
    
    def _init(self):
        pass

    def _loop(self):
        for cmd in self._get_cmd():
            if self.__event.is_set():
                self._on_receive_cmd(cmd)
    
    def send(self, cmd):
        self._channel.send(cmd + '\n')
    
    def _get_cmd(self, data=''):
        while self.__event.is_set():
            try:
                res = self._channel.recv(10000)
                if len(res) == 0:
                    raise ChannelException('Channel closed')
                data += res
                cmds = data.split('\n')
                for r in cmds[:-1]:
                    yield r
                data = cmds[-1]
            except socket.timeout:
                pass
    
    """def check_pipe_msg(self):
        if self.__pipe is None:
            return
        while(self.__pipe.poll()):
            self.on_pipe_msg(self.__pipe.recv())"""
    
    def _on_receive_cmd(self, queue, cmd):
        queue.put(cmd)
    
    """def _on_pipe_msg(self, msg):
        pass"""
    
    def disconnect(self):
        self.__event.clear()
    
    def is_running(self):
        return self.__event.is_set()
    
    def join(self):
        self.disconnect()
        if self.__thread is None:
            return
        self.__thread.join()
    
    def get_queue(self):
        return self.__queue

class ChannelHandlerServer(ChannelHandler):
    def __init__(self, client_socket, id, allowed_users, client_addr, queue=None):
        self.__id = id
        self.__client_socket = client_socket
        self.__client_addr = client_addr
        self.__allowed_users = allowed_users
        ChannelHandler.__init__(self, queue=queue, processed=True)
    
    def _on_receive_cmd(self, queue, cmd):
        queue.put((self.id, cmd))

    def _start(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            t = paramiko.Transport(self.__client_socket)
            try:
                t.load_server_moduli()
            except:
                raise ServerException('(Failed to load moduli -- gex will be unsupported.)')
            host_key = paramiko.RSAKey(filename=private_key)
            t.add_server_key(host_key)
            server = ParamikoServer(self.__allowed_users)
            try:
                t.start_server(server=server)
            except paramiko.SSHException, x:
                raise ServerException('*** SSH negotiation failed.')
        
            # wait for auth
            self._channel = t.accept(20)
            if self._channel is None:
                raise ServerException('*** No channel.')
            print 'Authenticated!'
        
            server.event.wait(10)
            if not server.event.isSet():
                raise ServerException('*** Client never asked for a shell.')
            try:
                ChannelHandler._start(self)
            except ChannelException:
                pass
            print 'Closing session'
            self._channel.close()
        
        except:
            try:
                t.close()
            except:
                pass
            raise

class Server(object):
    def __init__(self, channel_handler, port=2200, allowed_users=None, queue=None, threaded=False):
        self.__event = threading.Event()
        self.__lock = threading.Lock()
        self.__event.set()
        self.__channel_handler = channel_handler
        self.__queue = queue
        self.__port = port
        if allowed_users is None:
            self.__allowed_users = {}
        else:
            self.__allowed_users = allowed_users.copy()
        if threaded:
            self.__thread = threading.Thread(target=self._start)
            self.__thread.start()
        else:
            self.__start()

    def __start(self):
        # now connect
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.__port))
        except Exception, e:
            raise ServerException('*** Bind failed: ' + str(e))
        
        sock.listen(100)
        print 'Listening for connection ...'
        id = 0
        self.__handlers = {}
        while self.__event.is_set():
            try:
                client_socket, addr = sock.accept()
                print 'Got a connection from %s:%s' % (addr[0], addr[1])
                p = self.__channel_handler(client_socket, id, self.__allowed_users, addr, self.__queue)
                self.__lock.acquire()
                self.__handlers[nb] = p
                self.__lock.release()
                id += 1
            except KeyboardInterrupt:
                print 'Quitting, waiting for end of connections'
                break
        for id in self.__handlers:
            self.__handlers[id].join()
    
    def get_handler_by_id(self, id):
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
    def __init__(self, host, username, password, port=2200, queue=None, threaded=False):
        hosts_filename = os.path.expanduser("~/.ssh/paramiko_known_hosts")
        #print hosts_filename
        
        client = paramiko.client.SSHClient()
        if os.path.isfile(hosts_filename):
            client.load_host_keys(hosts_filename) #'~/.ssh/known_hosts'
        client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        #print client.get_host_keys()
        client.connect(host, port, username=username, password=password)
        client.save_host_keys(hosts_filename)
        #print client.get_host_keys()
        self._channel = client.invoke_shell()
        self._channel.settimeout(0)
        ChannelHandler.__init__(self, queue, threaded=threaded)

class ChannelHandlerClientTest(ChannelHandlerClient):
    def _init(self):
        print 'ping'
        self.send('ping')
    
    def _on_receive_cmd(self, queue, cmd):
        print cmd
        self.disconnect()

class ChannelHandlerServerTest(ChannelHandlerServer):
    def _on_receive_cmd(self, queue, cmd):
        print '%s from %s' % (cmd, self.id)
        self.send('pong')

if __name__ == "__main__":
    import sys
    args = sys.argv
    
    if len(args) == 1:
        allowed_users = {'bucky': 'foo'}
        Server(ChannelHandlerServerTest, allowed_users=allowed_users)
    else:
        ChannelHandlerClientTest('localhost', 'bucky', 'foo')
