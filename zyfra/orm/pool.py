#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .. import pool

class Pool(pool.Pool):
    _language_object_name = 'language'
    _default_user_id = 1
    _context = None
    _model_class = 'Model'
    
    
    def __init__(self, db, module_path='', lazy_load=True, db_encoding=None, table_prefix=''):
        self._db = db
        self._db_encoding = db_encoding
        self._table_prefix = table_prefix
        super(Pool, self).__init__(module_path, lazy_load)

    def __setitem__(self, key, obj):
        super(Pool, self).__setitem__(key, obj)
        obj.set_instance(self)
    
    def set_auto_create(self, flag):
        raise Exception('set_auto_create is not more used in pool use pool->update_sql_structure() instead')
        self.auto_create = flag

    def get_auto_create(self):
        raise Exception('set_auto_create is not more used in pool use pool->update_sql_structure() instead')
        return self.auto_create

    def update_sql_structure(self):
        for model_name in self.__pool:
            self.__pool[model_name].update_sql_structure()

    def get_language_object_name(self):
        return self._language_object_name
