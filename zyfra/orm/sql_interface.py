#!/usr/bin/env python
# -*- coding: utf-8 -*-

class SQLInterface(object):
    callbacks = None
    object = None

    def __init__(self, cr, obj):
        self.object = obj
        self.cr = cr
        self.callbacks = []

    def add_callback(self, field_object, callback_name):
        self.callbacks.append(field_object, callback_name)
