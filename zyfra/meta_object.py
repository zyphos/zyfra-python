#!/usr/bin/env python
# -*- coding: utf-8 -*-

class MetaObject(object):
    def __new__(cls, value):
        dct = dict((name, value) for name, value in cls.__dict__.items() if name not in ['__new__']) #if not name.startswith('__')
        return type(cls.__name__ + '.' + value.__class__.__name__, (value.__class__, ), dct)(value)