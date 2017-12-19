#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Callback:
    def __init__(self, function, return_value):
        self.function = function
        self.return_value = return_value

class SQLInterface(object):
    callbacks = None
    object = None
    debug = False

    def __init__(self, cr, obj):
        self.object = obj
        self.cr = cr
        self.callbacks = []
        self.debug = cr.context.get('debug')
        self.dry_run = cr.context.get('dry_run')

    def add_callback(self, callback_function, parameters=None):
        if parameters == None:
            parameters = []
        self.callbacks.append((callback_function, parameters))
