#!/usr/bin/env python
# -*- coding: utf-8 -*-

import imp
import sys
import os

from singleton import Singleton

class Pool(object):
    __metaclass__ = Singleton
    __pool = None;

    def __init__(self, db, module_path):
        self.__pool = {}
        self.db = db;
        self.module_path = module_path
        sys.path.insert(1, os.path.abspath(module_path))

    def __getattr__(self, key):
        if key in self.__pool:
            return self.__pool[key]
        try:
            f, path, descr = imp.find_module(key, [self.module_path])
            try:
                mod = imp.load_module(key, f, path, descr)
            finally:
                if f:
                    f.close()
            obj = getattr(mod, key.capitalize())()  # Istanciate class
        except:
            raise
            #raise Exception("Object class [" + key + "] doesn't exists")
        self.add_object(key, obj)
        return obj

    def add_object(self, name, obj):
        self.__pool[name] = obj

    def object_in_pool(self, name):
        return name in self.__pool
