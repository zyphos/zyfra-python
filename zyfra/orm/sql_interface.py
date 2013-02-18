#!/usr/bin/env python
# -*- coding: utf-8 -*-

class SQLInterface(object):
    callbacks = None
    object = None

    def __init__(obj, context):
        self.object = obj
        self.callbacks = []
        self.context = context

    def add_callback(field_object, callback_name):
        self.callbacks.append(field_object, callback_name)
