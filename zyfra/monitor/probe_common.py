#!/usr/bin/env python
# -*- coding: utf-8 -*-

OK=0
UNKNOWN=1
WARNING=2
CRITICAL=3

class State(dict):
    def __init__(self, state, message=''):
        self['state'] = state
        self['message'] = message
    
    def __cmp__(self, other):
        if isinstance(other, State):
            return cmp(self.state, other.state)
        return cmp(self.state, other)
        # Not equal
        #if self['state'] != other['state']:
        #    return True
        #if self['message'] != other['message']:
        #    return True
        #return False
    
    def __getattribute__(self, name):
        return self[name]
        
    def __setattr__(self, name, value):
        if name not in self:
            raise Exception('State parameter not found: %s' % name)
        self[name] = value
    
    def __delattr__(self, name):
        raise Exception('Can not delete state parameter')
    
    def __delitem__(self, key):
        raise Exception('Can not delete state parameter')

class Service(object):
    def __init__(self):
        self.name = self.__class__.__name__
    
    def get_state(self):
        # To be overide
        return State(UNKNOWN)

class ProbeException(Exception):
    pass
