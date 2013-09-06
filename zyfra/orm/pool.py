#!/usr/bin/env python
# -*- coding: utf-8 -*-

from zyfra import pool

class Pool(pool.Pool):
    auto_create = False;
    
    def __init__(self, db, module_path):
        self.db = db
        super(Pool, self).__init__(module_path)

    def add_object(self, name, obj):
        super(Pool, self).add_object(name, obj)
        obj.set_instance(self)

    def set_auto_create(self, flag):
        self.auto_create = flag

    def get_auto_create(self):
        return self.auto_create
