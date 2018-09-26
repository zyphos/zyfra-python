#!/usr/bin/env python
# -*- coding: utf-8 -*-

from field import Field
from zyfra.tools import is_numeric
import decimal

class Int(Field):
    unsigned = False
    auto_increment = False
    size = 11
    default_value = None
    widget = 'integer'

    def sql_format(self, value):
        return str(int(value))
    
    def python_format(self, value):
        return int(value)

    def get_sql_def(self, db_type):
        if db_type == 'sqlite3':
            return 'INTEGER'
        return 'INT(%s)%s' % (self.size, (self.unsigned and ' UNSIGNED ' or ''))

    def get_sql_def_flags(self, db_type):
        return (db_type != 'sqlite3' and self.auto_increment and ' AUTO_INCREMENT' or '') + super(Int, self).get_sql_def_flags(db_type)

    def get_sql_extra(self, db_type):
        return db_type != 'sqlite3' and self.auto_increment and 'auto_increment' or ''

class Float(Field):
    default_value = 0
    widget = 'float'

    def sql_format(self, value):
        return str(float(value))

    def get_sql_def(self, db_type):
        return 'FLOAT'

class Double(Field):
    default_value = 0
    widget = 'double'

    def sql_format(self, value):
        return str(float(value))

    def get_sql_def(self, db_type):
        return 'DOUBLE'

class Decimal(Field):
    default_value = 0
    widget = 'double'

    def sql_format(self, value):
        return str(decimal.Decimal(str(value)))

    def get_sql_def(self, db_type):
        if db_type == 'sqlite3':
            return 'NUMERIC'
        return 'DOUBLE'
    
    def sql_create(self, sql_create, value, fields, context):
        return str(decimal.Decimal(str(value)))

class Boolean(Field):
    default_value = 0
    widget = 'boolean'

    def sql_format(self, value):
        if self.object._pool._db.type == 'postgresql':
            return 'true' if value else 'false'
        return str(value and 1 or 0)

    def get_sql_def(self, db_type):
        if db.type == 'postgresql':
            return 'BOOLEAN'
        return 'INT(1)'
    
    def python_format(self, value):
        if self.object._pool._db.type == 'postgresql':
            return value
        return value == 1

class IntSelect(Field):
    select_values = None
    widget = 'intselect'

    def __init__(self, label, select_values=None, **args):
        if isinstance(select_values, (list, tuple)):
            self.select_values = select_values
        else:
            self.select_values = [select_values]
        super(IntSelect, self).__init__(label, **args)

    def sql_format(self, value):
        if isinstance(value, basestring):
            key = array_search(value, self.select_values)
            if key is not False:
                return str(key)
        if is_numeric(value):
            return str(int(value))
        return None
    
    def python_format(self, value):
        try:
            return self.select_values[int(value)]
        except:
            return value
