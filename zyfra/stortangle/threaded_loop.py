#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Threaded loop that can be interrupted externaly
"""
import threading
import time

class ThreadedLoop(object):
    
    def __init__(self, loop_sleep_delay=0.1, log_level=0):
        self.__running_event = threading.Event()
        self.__starting_event = threading.Event()
        self.__running_event.clear()
        self.__thread = None
        self.__loop_sleep_delay = loop_sleep_delay
        self.__log_level = log_level
    
    def _log(self, msg, level=1):
        if level <= self.__log_level:
            print 'ThreadedLoop', msg
    
    def _init(self): # Setup all data before looping
        pass
    
    def _loop(self): # This is called at each loop iteration
        pass
    
    def _clear(self): # Called when the loop ended
        pass
    
    def start(self, wait_started=False):
        self._log('start', 2)
        if self.__running_event.is_set(): # Only run the thread once
            return
        self.__starting_event.clear()
        self.__thread = threading.Thread(target=self.__the_loop)
        self.__thread.start()
        while wait_started and not self.__starting_event.is_set():
            pass
    
    def stop(self):
        self._log('stop', 1)
        self.__running_event.clear()
    
    def join(self):
        self._log('join', 1)
        self.stop()
        self.__thread.join()
    
    def is_running(self):
        return self.__running_event.is_set()
    
    def __the_loop(self):
        self._log('the_loop', 2)
        self.__running_event.set()
        self._init()
        while self.__running_event.is_set():
            self._log('_loop', 2)
            self._loop()
            time.sleep(self.__loop_sleep_delay)
        self._log('clear', 1)
        self._clear()
        self.__running_event.clear()
