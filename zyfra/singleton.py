#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Singleton(type):
    def __init__(cls, name, bases, dict):
        super(Singleton, cls).__init__(name, bases, dict)
        cls.instance = None

    def __call__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.instance


# Source: https://wiki.python.org/moin/PythonDecoratorLibrary#The_Sublime_Singleton
# @singleton
# class Highlander:
#     x = 100"""
def singleton(cls):
    instance = cls()
    instance.__call__ = lambda: instance
    return instance
