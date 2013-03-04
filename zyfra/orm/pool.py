#!/usr/bin/env python
# -*- coding: utf-8 -*-

from zyfra.singleton import Singleton

class Pool(object):
    __metaclass__ = Singleton
    __pool = None;
    auto_create = False;

    def __init__(self, db, module_path):
        self.__pool = {}
        self.db = db;
        self.module_path = module_path

    def __getattr__(self, key):
        if key in self.__pool:
            return self.pool[key];
        try:
            f, path, descr = imp.find_module(module_part, ad_paths)
            mod = imp.load_module(key, f, path, descr)
            obj = getattr(key, key)()  # Istanciate class
        except:
            raise Exception("Object class [" + key + "] doesn't exists")
        self.add_object(key, obj)
        return obj

    def add_object(self, name, obj):
        self.__pool[name] = obj
        obj.set_instance()

    def object_in_pool(self, name):
        return name in self.__pool

    def set_auto_create(self, flag):
        self.auto_create = flag

    def get_auto_create(self):
        return self.auto_create