#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import time
import pyinotify as pi

#mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE  # watched events
mask = pi.ALL_EVENTS
#mask = pi.IN_CLOSE_WRITE | pi.IN_MOVED_TO | pi.IN_DELETE | pi.IN_MOVED_FROM

class PathWatcher(object):
    def __init__(self, path, timeout=5, queue=None, debug=False):
        self.__timeout = timeout
        self.__path = path
        self._queue = queue
        self.__running_event = threading.Event()
        self.__starting_event = threading.Event()
        self.__running_event.clear()
        self.__thread = None
        self.__debug = debug
    
    def start(self, threaded=False):
        print 'Inotify start'
        if self.__running_event.is_set(): # Only run the thread once
            return
        if threaded:
            self.__starting_event.clear()
            self.__thread = threading.Thread(target=self.__start)
            self.__thread.start()
            while not self.__starting_event.is_set():
                pass
            
        else:
            self.__start()
        return self

    def __start(self):
        self.__running_event.set()
        self.__events = []
        self.__timer = 0
        self.__wm = pi.WatchManager()
        handler = pi.ProcessEvent(self._on_event)
        self.__notifier = pi.Notifier(self.__wm, handler)
        while self.__running_event.is_set():
            self.__wdd = self.__wm.add_watch(self.__path, mask, rec=True, auto_add=True)
            self.__starting_event.set()
            if len(self.__wdd) > 0:
                try:
                    while self.__running_event.is_set():
                        #print 'Process events'
                        self.__notifier.process_events()
                        #print 'Check events'
                        if self.__notifier.check_events(10):
                            #print 'Read events'
                            self.__notifier.read_events()
                        #print time.time()
                        if self.__timer != 0 and time.time() > self.__timer:
                            self._on_events(self.__events)
                            self.__events = []
                            self.__timer = 0
                    
                    pass
                    #print 'Sleep 1'
                    time.sleep(0.1)
                except KeyboardInterrupt:
                        break
            time.sleep(0.1)
        print 'Inotify stopping'
        self.__events = []
        self.__notifier.stop()
        #self.__wm.stop()
        self.__running_event.clear()
        print 'Inotify stopped'
    
    def stop(self):
        self.__running_event.clear()
    
    def join(self):
        print 'Inotify joining'
        if self.__thread is None:
            self.stop()
            return
        self.stop()
        self.__thread.join()
        print 'Inotify joined'
    
    def get_queue(self):
        return self.__queue
    
    def is_running(self):
        return self.__running_event.is_set()
    
    def _on_event(self, event):
        maskname = event.maskname
        src = ''
        the_event = None
        if maskname == 'IN_MOVED_TO':
            if hasattr(event, 'src_pathname'):
                previous_event = self.__events[-1]
                if previous_event[0] == 'delete' and previous_event[1] == event.src_pathname:
                    self.__events.pop()
                the_event = ('move', (event.src_pathname, event.pathname))
            else:
                the_event = ('add', event.pathname)
        elif maskname == 'IN_MOVED_TO|IN_ISDIR':
            if hasattr(event, 'src_pathname'):
                previous_event = self.__events[-1]
                if previous_event[0] == 'delete_dir' and previous_event[1] == event.src_pathname:
                    self.__events.pop()
                the_event = ('move_dir', (event.src_pathname, event.pathname))
            else:
                the_event = ('add_dir', event.pathname)
        elif maskname == 'IN_MOVED_FROM' or maskname == 'IN_DELETE':    
            the_event = ('delete', event.pathname)
        elif maskname == 'IN_CLOSE_WRITE':
            the_event = ('add', event.pathname)
        elif maskname == 'IN_CREATE|IN_ISDIR':
            the_event = ('add_dir', event.pathname)
        elif maskname == 'IN_MOVED_FROM|IN_ISDIR' or maskname == 'IN_DELETE|IN_ISDIR':
            the_event = ('delete_dir', event.pathname)
        if hasattr(event, 'src_pathname'):
            src = ' from %s' % event.src_pathname
        if self.__debug:
            print 'Event %s on %s%s' % (event.maskname, event.pathname,src)
        if the_event is not None:
            path = the_event[1]
            if the_event[0] == 'delete_dir' and path in self.__wdd:
                wd = self.__wdd[path]
                # w = wm.get_watch(wm.get_wd(path))
                #wm.del_watch(wd)
                self.__wm.rm_watch(wd)
            self.__events.append(the_event)
            self.__timer = time.time() + self.__timeout
        #if maskname == 'IN_DELETE' or maskname == '':
            
        #event.maskname
        #event.pathname
        
        #if hasattr(event, 'src_pathname'):
        #    pass
        #pass
    
    def _on_events(self, events):
        if self.__debug:
            print 'Events:'
            print events
        if self._queue is not None:
            self._queue.put(events)
        

"""class EventHandler(pi.ProcessEvent):
    #def process_IN_CREATE(self, event):
    #    print "Creating:", event.pathname

    #def process_IN_DELETE(self, event):
    #    print "Removing:", event.pathname
    
    
    #IN_CLOSE_WRITE
    #IN_MOVED_TO event.src_pathname
    #IN_DELETE
    #IN_MOVED_FROM  (move to external)
    
    def __init__(self):
        
        
    def process_default(self, event):
        src = ''
        if hasattr(event, 'src_pathname'):
            src = ' from %s' % event.src_pathname
        print 'Event %s on %s%s' % (event.maskname, event.pathname,src)

    handler = EventHandler()
    notifier = pi.Notifier(wm, handler)
    
    wdd = wm.add_watch('/tmp/inotify', mask, rec=True)
    
    notifier.loop()"""
if __name__ == "__main__":
    pw = PathWatcher('/tmp/inotify', debug=True).start(threaded=True)
    try:
        while pw.is_running():
            print 'Running'
            time.sleep(1)
    except:
        pw.join()
        raise
    pw.join()
