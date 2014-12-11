#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .. import pool

class Pool(pool.Pool):
    auto_create = False;
    
    def __init__(self, db, module_path='', lazy_load=True, db_encoding=None, table_prefix=''):
        self._db = db
        self._db_encoding = db_encoding
        self._table_prefix = table_prefix
        super(Pool, self).__init__(module_path, lazy_load)

    def __setitem__(self, key, obj):
        super(Pool, self).__setitem__(key, obj)
        obj.set_instance(self)
    
    def set_auto_create(self, flag):
        self.auto_create = flag

    def get_auto_create(self):
        return self.auto_create
