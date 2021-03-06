#!/usr/bin/env python
# -*- coding: utf-8 -*

import signal
import os
import time
from multiprocessing import Process, Queue 
import tornado.ioloop
import tornado.web
import simplejson

SCRIPT_PATH=os.path.dirname(os.path.realpath(__file__))

intervals = (
    ('w', 604800),  # 60 * 60 * 24 * 7
    ('d', 86400),    # 60 * 60 * 24
    ('h', 3600),    # 60 * 60
    ('m', 60),
    ('s', 1),
    )

def display_time(seconds, granularity=2):
    result = []

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            result.append('%s%s' % (value, name))
    return ' '.join(result[:granularity])

class MainHandler(tornado.web.RequestHandler):
    def initialize(self, queue2middle, queue2web, queue2probe, debug):
        self.queue2middle = queue2middle
        self.queue2web = queue2web
        self.queue2probe = queue2probe
        self.debug = debug
    
    def get(self, path):
        if self.debug:
            print '[HTTP] Received http get [%s]' % path 
        if path == '':
            self.render('templates/base.html')
            return
        elif path == 'json':
            self.queue2middle.put(('get_status',''))
            status = self.queue2web.get()
            return self.write(simplejson.dumps(status))
        elif path == 'force_refresh':
            hostname = self.get_argument('hostname', None)
            service_name = self.get_argument('service', None)
            if hostname is not None and service_name is not None:
                self.queue2probe.put(('force_refresh',(hostname, service_name)))
            return
        #print '[HTTP] Sending put'
        self.queue2middle.put(('get_status',''))
        #print '[HTTP] receiving get'
        status = self.queue2web.get()
        if len(status) == 0:
            self.write('Probing hosts... Please wait')
        else:
            self.render('templates/service_status.html', status=status)
        
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
            now_ts = time.time()
            for node in _status:
                for service in node['services']:
                    service['age'] = 'Age: %s' % display_time(int(round(now_ts-service['last_update_ts'])))
                    
            queue2web.put(_status)
        else:
            print '[MIDDLE] Command [%s] not found' % cmd

def start_server(port=8888, ssl=False, certfile=None, keyfile=None, queue2probe=None, debug=False):
    queue2middle = Queue()
    queue2web = Queue()
    favicon_path = os.path.join(SCRIPT_PATH, 'favicon.ico')
    static_path = os.path.join(SCRIPT_PATH, 'static')
    application = tornado.web.Application([
                                           (r'/(favicon\.ico)', tornado.web.StaticFileHandler, {'path': SCRIPT_PATH}),
                                           (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': static_path}),
                                           (r"/(.*)", MainHandler, {'queue2middle': queue2middle, 'queue2web': queue2web, 'queue2probe': queue2probe, 'debug': debug}),
                                           ], compiled_template_cache=False)
    if ssl and certfile and keyfile:
        ssl_options={
                        'certfile': certfile,
                        'keyfile': keyfile,
                    }
    else:
        ssl_options = None
    application.listen(port, ssl_options=ssl_options)
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
