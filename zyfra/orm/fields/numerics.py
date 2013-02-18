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
        return int(value)

    def get_sql_def(self):
        return 'INT(' + self.size + ')' + (self.unsigned and ' UNSIGNED ' or '')

    def get_sql_def_flags(self):
        return (self.auto_increment and ' AUTO_INCREMENT' or '') + super(Int, self).get_sql_def_flags()

    def get_sql_extra(self):
        return self.auto_increment and 'auto_increment' or ''

class Float(Field):
    default_value = 0
    widget = 'float'

    def sql_format(self, value):
        return float(value)

    def get_sql_def(self):
        return 'FLOAT'

class Double(Field):
    default_value = 0
    widget = 'double'

    def sql_format(self, value):
        return float(value)

    def get_sql_def(self):
        return 'DOUBLE'

class Decimal(Field):
    default_value = 0
    widget = 'double'

    def sql_format(self, value):
        return decimal.Decimal(value)

    def get_sql_def(self):
        return 'DOUBLE'

class Boolean(Field):
    default_value = 0
    widget = 'boolean'

    def sql_format(self, value):
        return value and 1 or 0

    def get_sql_def(self):
        return 'INT(1)'

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
                return key
        if is_numeric(value):
            return int(value)
        return None
