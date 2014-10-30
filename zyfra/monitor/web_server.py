#!/usr/bin/env python
# -*- coding: utf-8 -*

import signal
import os
from multiprocessing import Process, Queue 
import tornado.ioloop
import tornado.web

SCRIPT_PATH=os.path.dirname(os.path.realpath(__file__))

class MainHandler(tornado.web.RequestHandler):
    def initialize(self, queue2middle, queue2web):
        self.queue2middle = queue2middle
        self.queue2web = queue2web
    
    def _render_status(self, status):
        self.render
        
    def get(self):
        print '[HTTP] Received http get'
        #print '[HTTP] Sending put'
        self.queue2middle.put(('get_status',''))
        #print '[HTTP] receiving get'
        status = self.queue2web.get()
        self.render('service_status.html', status=status)
        
is_alive = True
def middleware(queue2middle, queue2web):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    _status = {}
    queue2middle = queue2middle
    queue2web = queue2web
    while True:
        #print '[MIDDLE] Waiting get'
        cmd, data = queue2middle.get()
        #print '[MIDDLE] received get'
        if cmd == 'exit':
            print '[MIDDLE] Quitting'
            return
        elif cmd == 'set_status':
            #print '[MIDDLE] set status'
            _status = data
        elif cmd == 'get_status':
            #print '[MIDDLE] sending status to web'
            queue2web.put(_status)
        else:
            print '[MIDDLE] Command [%s] not found' % cmd

def start_server(port=8888):
    queue2middle = Queue()
    queue2web = Queue()
    favicon_path = os.path.join(SCRIPT_PATH, 'favicon.ico')
    static_path = os.path.join(SCRIPT_PATH, 'static')
    application = tornado.web.Application([
                                           (r'/favicon.ico', tornado.web.StaticFileHandler, {'path': favicon_path}),
                                           (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': static_path}),
                                           (r"/", MainHandler, {'queue2middle': queue2middle, 'queue2web': queue2web}),
                                           ], compiled_template_cache=False)
    application.listen(port)
    ioloop = tornado.ioloop.IOLoop.instance()
    def dummy_callback(iol):
        print 'test'
        iol.add_callback(dummy_callback, iol) 
        
    def start_ioloop():
        try:
            ioloop.start()
        except KeyboardInterrupt:
            print '[WEB] Stopped'
    ioloop_process = Process(target=start_ioloop)
    middleware_process = Process(target=middleware, args=(queue2middle, queue2web))
    middleware_process.start()
    ioloop_process.start()
    print 'Webserver listening on port %s' % port
    return queue2middle
