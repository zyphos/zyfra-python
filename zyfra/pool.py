#!/usr/bin/env python
# -*- coding: utf-8 -*-

import imp
import sys
import os

from singleton import Singleton

class Pool(object):
    __metaclass__ = Singleton
    __pool = None;

    def __init__(self, module_path, lazy_load=True):
        self.__pool = {}
        self.module_path = module_path
        sys.path.insert(1, os.path.abspath(module_path))
        if not lazy_load:
            self.__load_all_modules()

    def __getattr__(self, key):
        if key in self.__pool:
            return self.__pool[key]
        obj = self.__load_module(key)
        self[key] = obj
        return obj

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __iter__(self):
        return iter(self.__pool)

    def __len__(self):
        return len(self.__pool)

    def __contains__(self, name):
        return name in self.__pool

    def __setitem__(self, key, value):
        if key in self.__pool:
            raise Exception("This object " + key + " is already in pool")
        self.__pool[key] = value
    
    def keys(self):
        return self.__pool.keys()

    def __load_module(self, name):
        try:
            f, path, descr = imp.find_module(name, [self.module_path])
            try:
                mod = imp.load_module(name, f, path, descr)
            finally:
                if f:
                    f.close()
            return getattr(mod, name.capitalize())()  # Istanciate class
        except:
            raise
            # raise Exception("Object class [" + key + "] doesn't exists")

    def __load_all_modules(self):
        fnames = os.listdir(self.module_path)
        for fname in fnames:
            f = fname.rsplit('.', 1)
            if len(f) == 2:
                name, ext = f
            else:
                ext = ''
            if ext == 'py' and name not in self.__pool:
                obj = self.__load_module(name)
                self[name] = obj
