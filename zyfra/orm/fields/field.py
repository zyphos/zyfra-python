#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Field(object):
    name = None
    object = None
    unique = False
    primary_key = False
    index = False
    not_null = False
    key = False
    stored = True
    relational = False
    needed_columns = None
    default_value = None
    widget = 'text'
    required = False
    read_only = False
    instanciated = False
    sql_escape_fx = None
    help = ''
    handle_operator = False
    not_null = False
    select_all = True
    model_class = None
    hidden = False
    sql_name = ''

    def __init__(self, label, **args):
        self.label = label
        for key in args:
            if hasattr(self, key):
                setattr(self, key, args[key])
            else:
                raise Exception('Field (%s) do not have attribute [%s]' % (label, key))
        self.needed_columns = {}
        if self.not_null and self.default_value is None:
            raise Exception('Field do not accept null values, but default value is null.')
    
    def is_stored(self, context):
        return self.stored

    def sql_create(self, sql_create, value, fields, context):
        return self.sql_format(value)

    def sql_write(self, sql_write, value, fields, context):
        if self.read_only: return
        sql_write.add_assign('%s=%s' % (self.sql_name, self.sql_format(value)))

    def _sql_format_null(self):
        if self.not_null:
            raise Exception('Null value not accepted for this field [%s.%s]' % (self.object._name, self.name))
        return 'null'
    
    def sql_format(self, value):
        if value is None:
            return self._sql_format_null()
        if self.sql_escape_fx is None:
            if not isinstance(value, unicode):
                value = str(value)
            return "'%s'" % (value.replace("'","\\'")) # !! SQL injection !!!
        if self.sql_escape_fx is None:
            self.sql_escape_fx = self.object._pool.db.safe_var
        
        return self.sql_escape_fx(value)
    
    def python_format(self, value):
        return value
    
    def set_instance(self, object, name):
        if self.instanciated: return
        self.instanciated = True
        if self.label is None or self.label == '': self.label = name
        self.name = name
        if not self.sql_name:
            self.sql_name = (object._field_prefix + name).lower()
        self.object = object

    def get_sql(self, parent_alias, fields, sql_query, context=None):
        if context is None: context = {}
        if 'field_alias' in context:
            field_alias = context['field_alias']
        else:
            field_alias = ''
        if self.sql_name == field_alias: sql_query.no_alias(field_alias)
        parent_alias.set_used()
        return self.add_operator('%s.%s' % (parent_alias.alias, self.sql_name), context)
    
    def add_operator(self, field_sql, context):
        if 'operator' in context:
            operator = str(context['operator'])
            if operator in ['in','is']: operator = ' %s ' % operator
            op_data = context['op_data'].strip()
            return '%s%s%s' % (field_sql, operator, op_data)
        return field_sql
    
    def get_sql_column_definition(self, db):
        return db.make_sql_def(self.get_sql_def(db.type), self.not_null, self.default_value, self.primary_key)
    
    def get_sql_def(self, db_type):
        return ''

    def get_sql_def_flags(self, db_type, update=False):
        if self.primary_key: return ' PRIMARY KEY'
        return '%s NULL DEFAULT %s' % (' NOT' if self.not_null else '', self.sql_format(self.default_value))

    def get_sql_extra(self, db_type):
        return ''
    
    def get(self, ids, context, datas):
        return [] # list or dict ?
    
    def set(self, ids, value, context):
        pass
    
    def get_default(self):
        return self.default_value

    def validate(self, cr, data):
        return False
    
    def get_model_class(self):
        if self.model_class is None:
            return self.object._pool._model_class
        return self.model_class
