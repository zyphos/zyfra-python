#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Field(object):
    name = None
    unique = False
    primary_key = False
    key = False
    stored = True
    relational = False
    needed_columns = None
    default_value = None
    widget = 'text'
    required = False
    read_only = False
    instanciated = False
    sql_name = ''

    def __init__(self, label, **args):
        self.label = label
        for key in args:
            if hasattr(self, key): setattr(self, key, args[key])
        self.needed_columns = []

    def sql_create(self, sql_create, value, fields, context):
        return self.sql_format(value)

    def sql_write(self, sql_write, value, fields, context):
        if self.read_only or self.stored: return
        sql_write.add_assign(self.name+'='+self.sql_format(value))

    def sql_format(self, value):
        return "'" + value + "'" # !! SQL injection !!!
    
    def set_instance(self, object, name):
        if self.instanciated: return
        self.instanciated = True
        if self.label is None or self.label == '': self.label = name
        self.name = name
        self.sql_name = object._field_prefix + name
        self.object = object

    def get_sql(self, parent_alias, fields, sql_query, context=None):
        if context is None: context = {}
        if 'field_alias' in context:
            field_alias = context['field_alias']
        else:
            field_alias = ''
        if self.sql_name == field_alias: sql_query.no_alias(field_alias)
        parent_alias.set_used()
        return parent_alias.alias + '.' + self.sql_name

    def get_sql_def(self):
        return ''

    def get_sql_def_flags(self):
        return self.primary_key and ' PRIMARY KEY' or ''

    def get_sql_extra(self):
        return ''
    
    def get(self, ids, context, datas):
        return [] # list or dict ?
    
    def set(ids, value, context):
        pass
    
    def get_default():
        return self.default_value
