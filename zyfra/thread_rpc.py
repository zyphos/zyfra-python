#-*- coding:utf-8 -*-

##############################################################################
#
#    Copyright (C) 2010 De Smet Nicolas (<http://ndesmet.be>).
#    All Rights Reserved
#    
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import Queue

""" This module handle RPC at thread level
Usage:
import zyfra

class MyClassServer(zyfra.thread_rpc.Server):
    def calculate(self, a, b):
        return a + b + 5


def client_def(server_queue):
    rpc = zyfra.thread_rpc.Client(server_queue)
    print rpc.calculate(4, 5)
    print rpc.calculate(b=5, a=4)
    rpc._quit #Kill server


server = MyClassServer()
server_queue =  server._rpc_get_queue()

# init client thread
import threading
client_thread = threading.Thread(target=client_def, args=(server_queue,))
client_thread.start()
server._rpc_run() #Main_loop of server
client_thread.join() #Wait for child   
"""

class Server(object):
    def __init__(self):
        self.q = Queue.Queue(50)
    
    def _rpc_get_queue(self):
        return self.q
    
    def _rpc_run(self):
        self.loop = True
        while self.loop:
            self.__rpc_dispatch(self.q.get())
            
    def __rpc_dispatch(self, obj):
        # Messages are like this
        # (False, client_queue, (method, list(arg), dict(args))])
        # Message to dispatcher are like this
        # (True, client_queue,
        # (isMsg, client_queue, data):
        # isMsg True if it's a message to RPC server
        #       False => dispatch
        # client_queue is the answer channel 
        if not isinstance(obj, tuple) or len(obj) != 3:
            return
        (isMsg, client_queue, data) = obj
        if isMsg:
            return self.__rpc_handle_msg(client_queue, data)
        (attr, args, aargs) = data
        res = getattr(self, attr)(*args, **aargs)
        client_queue.put((False, res))
    
    def __rpc_handle_msg(self, client_queue, data):
        if data == '_quit':
            self.loop = False
        client_queue.put((False, True))


class Client(object):
    def __init__(self, server_queue, timeout = 30):
        # q = queue to send message to
        self.server_queue = server_queue
        self.timeout = timeout
        
    def __getattr__(self, name):
        # for now this module only handle "method" (not attr)
        q = Queue.Queue(1)
        if name[0] == '_': #This is a RPC message
            self.server_queue.put((True, q, name))
            return self.__rpc_dispatch(q.get(True, self.timeout))
        
        def fx(*args, **aargs):
            self.server_queue.put((False, q, (name, args, aargs)))
            return self.__rpc_dispatch(q.get(True, self.timeout))
        return fx
    
    def __rpc_dispatch(self, obj):
        if not isinstance(obj, tuple) or len(obj) != 2:
            return
        (isMsg, data) = obj
        if isMsg:
            return self.__rpc_handle_msg(data)
        return data
    
    def __rpc_handle_msg(self, data):
        # handle msg
        return data