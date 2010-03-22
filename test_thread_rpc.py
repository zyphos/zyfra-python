#! /usr/bin/python
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